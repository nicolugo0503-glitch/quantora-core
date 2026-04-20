from __future__ import annotations

import math
import time
from datetime import date
from statistics import mean, stdev
from typing import Any, Dict, List

from backend.app.allocation.state_store import load_state as load_allocation_state
from backend.app.execution.fill_handler import append_audit as append_execution_audit
from backend.app.execution.fill_handler import load_state as load_execution_state
from backend.app.performance_engine.state_store import append_audit, load_state, save_state
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state


class PerformanceEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _parse_date(value: str) -> date:
        return date.fromisoformat(value)

    @staticmethod
    def _round(value: float, digits: int = 6) -> float:
        return round(float(value or 0.0), digits)

    def _sorted_series(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        series = list(state.get('nav_series') or [])
        series.sort(key=lambda item: item.get('as_of_date', ''))
        return series

    def _ensure_nav_per_unit(self, series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        prev = None
        for item in series:
            current = dict(item)
            equity = float(current.get('equity') or 0.0)
            if current.get('nav_per_unit') is None:
                if prev is None:
                    current['nav_per_unit'] = 100.0
                else:
                    prev_equity = float(prev.get('equity') or 0.0)
                    prev_nav = float(prev.get('nav_per_unit') or 100.0)
                    net_flow = float(current.get('net_flow') or 0.0)
                    ret = 0.0 if prev_equity <= 0 else ((equity - net_flow) / prev_equity) - 1.0
                    current['nav_per_unit'] = prev_nav * (1.0 + ret)
            current['nav_per_unit'] = float(current.get('nav_per_unit') or 100.0)
            if current.get('cash_pct') is None:
                current['cash_pct'] = max(0.0, 1.0 - float(current.get('gross_exposure_pct') or 0.0))
            out.append(current)
            prev = current
        return out

    def _returns(self, series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        prev = None
        for item in series:
            entry = dict(item)
            if prev is None:
                entry['daily_return'] = 0.0
            else:
                prev_nav = float(prev.get('nav_per_unit') or 0.0)
                current_nav = float(entry.get('nav_per_unit') or 0.0)
                entry['daily_return'] = 0.0 if prev_nav <= 0 else (current_nav / prev_nav) - 1.0
            out.append(entry)
            prev = entry
        return out

    def _drawdown(self, series: List[Dict[str, Any]]) -> Dict[str, float]:
        peak = 0.0
        max_dd = 0.0
        current_dd = 0.0
        for item in series:
            nav = float(item.get('nav_per_unit') or 0.0)
            peak = max(peak, nav)
            if peak > 0:
                current_dd = max(0.0, (peak - nav) / peak)
                max_dd = max(max_dd, current_dd)
        return {
            'max_drawdown_pct': self._round(max_dd, 6),
            'current_drawdown_pct': self._round(current_dd, 6),
        }

    def _aggregate_attribution(self, series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        latest = series[-1] if series else {}
        latest_exposure = {str(r.get('strategy_id')): float(r.get('gross_exposure_pct') or 0.0) for r in latest.get('strategy_attribution', [])}
        aggregate: Dict[str, Dict[str, Any]] = {}
        for item in series:
            for row in item.get('strategy_attribution', []) or []:
                strategy_id = str(row.get('strategy_id') or 'unassigned')
                bucket = aggregate.setdefault(strategy_id, {
                    'strategy_id': strategy_id,
                    'pnl': 0.0,
                    'return_contribution_pct': 0.0,
                    'gross_exposure_pct': 0.0,
                    'observations': 0,
                })
                bucket['pnl'] += float(row.get('pnl') or 0.0)
                bucket['return_contribution_pct'] += float(row.get('return_contribution_pct') or 0.0)
                bucket['observations'] += 1
        for bucket in aggregate.values():
            bucket['pnl'] = round(bucket['pnl'], 2)
            bucket['return_contribution_pct'] = self._round(bucket['return_contribution_pct'], 6)
            bucket['gross_exposure_pct'] = self._round(latest_exposure.get(bucket['strategy_id'], 0.0), 6)
        rows = list(aggregate.values())

        # Backfill exposure-only strategies from allocation and deployment states.
        allocation = load_allocation_state()
        for strategy in allocation.get('strategies', []) or []:
            strategy_id = strategy.get('strategy_id')
            if strategy_id and strategy_id not in aggregate:
                rows.append({
                    'strategy_id': strategy_id,
                    'pnl': 0.0,
                    'return_contribution_pct': 0.0,
                    'gross_exposure_pct': self._round(float(strategy.get('risk_budget') or 0.0), 6),
                    'observations': 0,
                })
        rows.sort(key=lambda row: (row.get('pnl') or 0.0), reverse=True)
        return rows[:50]

    def _investor_metrics(self, series: List[Dict[str, Any]], returns: List[float], state: Dict[str, Any]) -> Dict[str, Any]:
        if not series:
            return {}
        latest = series[-1]
        latest_date = self._parse_date(latest['as_of_date'])
        first = series[0]
        current_nav = float(latest.get('nav_per_unit') or 0.0)
        first_nav = float(first.get('nav_per_unit') or current_nav or 100.0)

        def period_return(start_filter):
            subset = [item for item in series if start_filter(self._parse_date(item['as_of_date']))]
            if not subset:
                return 0.0
            start_nav = float(subset[0].get('nav_per_unit') or current_nav)
            return 0.0 if start_nav <= 0 else (current_nav / start_nav) - 1.0

        mtd = period_return(lambda d: d.year == latest_date.year and d.month == latest_date.month)
        qtd = period_return(lambda d: d.year == latest_date.year and ((d.month - 1) // 3) == ((latest_date.month - 1) // 3))
        ytd = period_return(lambda d: d.year == latest_date.year)
        inception = 0.0 if first_nav <= 0 else (current_nav / first_nav) - 1.0
        return {
            'as_of_date': latest['as_of_date'],
            'latest_equity': round(float(latest.get('equity') or 0.0), 2),
            'nav_per_unit': self._round(current_nav, 6),
            'mtd_return_pct': self._round(mtd, 6),
            'qtd_return_pct': self._round(qtd, 6),
            'ytd_return_pct': self._round(ytd, 6),
            'inception_return_pct': self._round(inception, 6),
            'gross_exposure_pct': self._round(float(latest.get('gross_exposure_pct') or 0.0), 6),
            'net_exposure_pct': self._round(float(latest.get('net_exposure_pct') or 0.0), 6),
            'cash_pct': self._round(float(latest.get('cash_pct') or 0.0), 6),
            'return_observations': max(len(returns), 0),
        }

    def _sync_risk_metrics(self, state: Dict[str, Any], metrics: Dict[str, Any], investor_metrics: Dict[str, Any], attribution: List[Dict[str, Any]]) -> None:
        risk = load_risk_state()
        latest_equity = float(investor_metrics.get('latest_equity') or 0.0)
        gross_exposure = float(investor_metrics.get('gross_exposure_pct') or 0.0)
        largest_position = max([float(row.get('gross_exposure_pct') or 0.0) for row in attribution] + [0.0])
        risk.setdefault('metrics', {})
        risk['metrics']['equity'] = latest_equity
        risk['metrics']['peak_equity'] = max(float(risk['metrics'].get('peak_equity') or 0.0), latest_equity)
        risk['metrics']['portfolio_drawdown_pct'] = float(metrics.get('current_drawdown_pct') or 0.0)
        risk['metrics']['daily_loss_pct'] = max(0.0, -float(metrics.get('latest_daily_return_pct') or 0.0))
        risk['metrics']['open_notional'] = latest_equity * gross_exposure
        risk['metrics']['largest_position_pct'] = largest_position
        save_risk_state(risk)
        append_execution_audit('performance_metrics_synced_to_risk', {
            'latest_equity': latest_equity,
            'portfolio_drawdown_pct': risk['metrics']['portfolio_drawdown_pct'],
            'daily_loss_pct': risk['metrics']['daily_loss_pct'],
        })

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        series = self._ensure_nav_per_unit(self._sorted_series(state))
        attribution = state.get('strategy_attribution', []) or self._aggregate_attribution(series)
        execution_state = load_execution_state()
        allocation_state = load_allocation_state()
        deployment_state = load_deployment_state()
        return {
            'mission': 'QNT50005',
            'status': 'ok',
            'snapshot_count': len(series),
            'metrics': state.get('metrics', {}),
            'investor_metrics': state.get('investor_metrics', {}),
            'strategy_attribution': attribution,
            'operating_context': {
                'active_strategy_count': len(deployment_state.get('active_deployments', []) or []),
                'registered_strategy_count': len(allocation_state.get('strategies', []) or []),
                'fill_count': len(execution_state.get('fills', []) or []),
                'order_count': len(execution_state.get('orders', []) or []),
                'latest_recompute_at': state.get('latest_recompute_at'),
            },
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        config = dict(state.get('config') or {})
        for key in ['benchmark_rate_annual', 'minimum_acceptable_return_annual', 'target_volatility_annual', 'trading_days_annual']:
            if payload.get(key) is not None:
                config[key] = payload[key]
        state['config'] = config
        save_state(state)
        append_audit('performance_config_updated', config)
        return self.recompute({'sync_risk': False})

    def register_nav_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        series = self._sorted_series(state)
        as_of_date = payload['as_of_date']
        row = {
            'as_of_date': as_of_date,
            'equity': round(float(payload['equity']), 2),
            'nav_per_unit': payload.get('nav_per_unit'),
            'net_flow': round(float(payload.get('net_flow') or 0.0), 2),
            'gross_exposure_pct': self._round(float(payload.get('gross_exposure_pct') or 0.0), 6),
            'net_exposure_pct': self._round(float(payload.get('net_exposure_pct') or 0.0), 6),
            'cash_pct': self._round(float(payload.get('cash_pct') if payload.get('cash_pct') is not None else max(0.0, 1.0 - float(payload.get('gross_exposure_pct') or 0.0))), 6),
            'strategy_attribution': payload.get('strategy_attribution', []),
        }
        replaced = False
        for idx, existing in enumerate(series):
            if existing.get('as_of_date') == as_of_date:
                series[idx] = row
                replaced = True
                break
        if not replaced:
            series.append(row)
        state['nav_series'] = self._ensure_nav_per_unit(sorted(series, key=lambda item: item.get('as_of_date', '')))
        save_state(state)
        append_audit('nav_snapshot_registered', {'as_of_date': as_of_date, 'replaced': replaced, 'equity': row['equity']})
        return self.recompute({'sync_risk': True})

    def recompute(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        if payload.get('benchmark_rate_annual') is not None:
            state.setdefault('config', {})['benchmark_rate_annual'] = payload['benchmark_rate_annual']
        if payload.get('minimum_acceptable_return_annual') is not None:
            state.setdefault('config', {})['minimum_acceptable_return_annual'] = payload['minimum_acceptable_return_annual']
        series = self._returns(self._ensure_nav_per_unit(self._sorted_series(state)))
        trading_days = int(state.get('config', {}).get('trading_days_annual', 252) or 252)
        benchmark_rate = float(state.get('config', {}).get('benchmark_rate_annual', 0.02) or 0.0)
        mar_rate = float(state.get('config', {}).get('minimum_acceptable_return_annual', 0.0) or 0.0)
        return_values = [float(item.get('daily_return') or 0.0) for item in series[1:]]
        avg_daily = mean(return_values) if return_values else 0.0
        vol_daily = stdev(return_values) if len(return_values) > 1 else 0.0
        annualized_vol = vol_daily * math.sqrt(trading_days) if vol_daily > 0 else 0.0
        if series:
            first_nav = float(series[0].get('nav_per_unit') or 100.0)
            last_nav = float(series[-1].get('nav_per_unit') or first_nav)
            cumulative_return = 0.0 if first_nav <= 0 else (last_nav / first_nav) - 1.0
        else:
            cumulative_return = 0.0
        annualized_return = ((1.0 + cumulative_return) ** (trading_days / max(len(return_values), 1))) - 1.0 if return_values else cumulative_return
        excess_daily = avg_daily - (benchmark_rate / trading_days)
        sharpe = (excess_daily / vol_daily) * math.sqrt(trading_days) if vol_daily > 0 else 0.0
        downside = [min(0.0, r - (mar_rate / trading_days)) for r in return_values]
        downside_dev = math.sqrt(sum(d * d for d in downside) / len(downside)) if downside else 0.0
        sortino = ((avg_daily - (mar_rate / trading_days)) / downside_dev) * math.sqrt(trading_days) if downside_dev > 0 else 0.0
        drawdowns = self._drawdown(series)
        max_dd = float(drawdowns.get('max_drawdown_pct') or 0.0)
        calmar = annualized_return / max_dd if max_dd > 0 else 0.0
        best_day = max(return_values) if return_values else 0.0
        worst_day = min(return_values) if return_values else 0.0
        win_rate = (sum(1 for r in return_values if r > 0) / len(return_values)) if return_values else 0.0
        latest_daily = return_values[-1] if return_values else 0.0
        attribution = self._aggregate_attribution(series)
        investor_metrics = self._investor_metrics(series, return_values, state)
        metrics = {
            'cumulative_return_pct': self._round(cumulative_return, 6),
            'annualized_return_pct': self._round(annualized_return, 6),
            'annualized_volatility_pct': self._round(annualized_vol, 6),
            'sharpe_ratio': self._round(sharpe, 6),
            'sortino_ratio': self._round(sortino, 6),
            'calmar_ratio': self._round(calmar, 6),
            'average_daily_return_pct': self._round(avg_daily, 6),
            'latest_daily_return_pct': self._round(latest_daily, 6),
            'best_day_return_pct': self._round(best_day, 6),
            'worst_day_return_pct': self._round(worst_day, 6),
            'win_rate_pct': self._round(win_rate, 6),
            **drawdowns,
        }
        state['nav_series'] = series
        state['metrics'] = metrics
        state['investor_metrics'] = investor_metrics
        state['strategy_attribution'] = attribution
        state['latest_recompute_at'] = int(time.time())
        state.setdefault('recompute_log', []).insert(0, {
            'timestamp': state['latest_recompute_at'],
            'snapshot_count': len(series),
            'cumulative_return_pct': metrics['cumulative_return_pct'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'max_drawdown_pct': metrics['max_drawdown_pct'],
        })
        state['recompute_log'] = state['recompute_log'][:200]
        save_state(state)
        append_audit('performance_recomputed', {
            'snapshot_count': len(series),
            'sharpe_ratio': metrics['sharpe_ratio'],
            'max_drawdown_pct': metrics['max_drawdown_pct'],
        })
        if payload.get('sync_risk', True):
            self._sync_risk_metrics(state, metrics, investor_metrics, attribution)
        return self.summary()

    def returns_series(self, limit: int = 250) -> Dict[str, Any]:
        state = self._refresh()
        series = self._returns(self._ensure_nav_per_unit(self._sorted_series(state)))
        use_limit = max(1, min(int(limit), 1000))
        return {
            'mission': 'QNT50005',
            'returns': [
                {
                    'as_of_date': item['as_of_date'],
                    'equity': round(float(item.get('equity') or 0.0), 2),
                    'nav_per_unit': self._round(float(item.get('nav_per_unit') or 0.0), 6),
                    'daily_return_pct': self._round(float(item.get('daily_return') or 0.0), 6),
                }
                for item in series[-use_limit:]
            ]
        }

    def attribution(self, limit: int = 25) -> Dict[str, Any]:
        state = self._refresh()
        use_limit = max(1, min(int(limit), 100))
        rows = state.get('strategy_attribution', []) or self._aggregate_attribution(self._ensure_nav_per_unit(self._sorted_series(state)))
        return {
            'mission': 'QNT50005',
            'rows': rows[:use_limit],
        }
