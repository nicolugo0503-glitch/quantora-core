from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from backend.app.allocation.state_store import append_audit, load_state, save_state
from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state


class AllocationEngine:
    REGIME_MULTIPLIER = {
        'bull': 1.10,
        'neutral': 1.0,
        'range': 0.96,
        'bear': 0.82,
        'stress': 0.70,
    }

    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _dynamic_reserve_weight(self, regime: str, liquidity_state: str, capital: float) -> float:
        reserve = float(self.state.get('reserve_target_weight', 0.10))
        if regime in {'bear', 'stress'}:
            reserve += 0.08
        if liquidity_state in {'tight', 'stressed'}:
            reserve += 0.05
        if capital < 250000:
            reserve += 0.03
        return round(min(max(reserve, 0.05), 0.35), 4)

    def _regime_fit(self, strategy: Dict[str, Any], regime: str) -> float:
        preferred = set(strategy.get('preferred_regimes') or [])
        if regime in preferred:
            return 1.08
        if 'neutral' in preferred and regime == 'range':
            return 0.98
        return 0.84

    def _risk_health(self, strategy: Dict[str, Any]) -> float:
        limit = max(float(strategy.get('max_drawdown_limit') or 0.01), 0.01)
        dd = max(float(strategy.get('drawdown_pct') or 0.0), 0.0)
        return max(0.05, min(1.15, 1 - (dd / limit) * 0.55))

    def _base_score(self, strategy: Dict[str, Any], regime: str) -> float:
        if not strategy.get('enabled', True):
            return 0.0
        signal = max(float(strategy.get('signal_strength') or 0.0), 0.0)
        conviction = max(float(strategy.get('conviction') or 0.0), 0.0)
        liquidity = max(float(strategy.get('liquidity_score') or 0.0), 0.0)
        risk_budget = max(float(strategy.get('risk_budget') or 0.0), 0.01)
        regime_mult = self.REGIME_MULTIPLIER.get(regime, 1.0) * self._regime_fit(strategy, regime)
        return signal * conviction * liquidity * risk_budget * regime_mult * self._risk_health(strategy)

    def list_strategies(self) -> Dict[str, Any]:
        state = self._refresh()
        return {
            'mission': 'QNT50002',
            'strategies': state.get('strategies', []),
            'count': len(state.get('strategies', [])),
        }

    def register_strategy(self, strategy_payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        strategy = dict(strategy_payload)
        strategy['strategy_id'] = strategy.get('strategy_id') or f"strat_{uuid.uuid4().hex[:10]}"
        strategy.setdefault('enabled', True)
        strategy.setdefault('preferred_regimes', ['neutral'])
        state.setdefault('strategies', []).insert(0, strategy)
        save_state(state)
        append_audit('strategy_registered', {
            'strategy_id': strategy['strategy_id'],
            'name': strategy.get('name'),
        })
        return strategy

    def recommend(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        capital = float(payload.get('capital') or state.get('total_capital') or 0.0)
        regime = str(payload.get('regime') or state.get('last_regime') or 'neutral').lower()
        liquidity_state = str(payload.get('liquidity_state') or 'normal').lower()
        override = payload.get('strategies') or state.get('strategies', [])
        max_strategy_weight = float(payload.get('max_strategy_weight') or state.get('max_strategy_weight') or 0.35)
        reserve_weight = self._dynamic_reserve_weight(regime, liquidity_state, capital)
        deployable_capital = max(capital * (1 - reserve_weight), 0.0)

        scored: List[Dict[str, Any]] = []
        total_score = 0.0
        for strategy in override:
            score = self._base_score(strategy, regime)
            entry = dict(strategy)
            entry['score'] = round(score, 8)
            scored.append(entry)
            total_score += score

        if total_score <= 0:
            raise ValueError('no eligible strategies available for allocation')

        weights_left = 1.0
        provisional: List[Dict[str, Any]] = []
        for idx, strategy in enumerate(sorted(scored, key=lambda x: x['score'], reverse=True)):
            raw_weight = strategy['score'] / total_score
            capped_weight = min(raw_weight, max_strategy_weight)
            if idx == len(scored) - 1:
                final_weight = max(0.0, min(capped_weight, weights_left))
            else:
                final_weight = max(0.0, min(capped_weight, weights_left))
                weights_left -= final_weight
            provisional.append({
                'strategy_id': strategy['strategy_id'],
                'name': strategy.get('name'),
                'symbol': strategy.get('symbol'),
                'asset_class': strategy.get('asset_class'),
                'score': strategy['score'],
                'weight': final_weight,
                'target_capital': round(deployable_capital * final_weight, 2),
                'risk_budget': float(strategy.get('risk_budget') or 0.0),
                'preferred_regimes': strategy.get('preferred_regimes') or [],
            })
        allocated_weight = sum(item['weight'] for item in provisional)
        if allocated_weight > 0:
            scale = min(1.0, 1.0 / allocated_weight)
            for item in provisional:
                item['weight'] = round(item['weight'] * scale, 6)
                item['target_capital'] = round(deployable_capital * item['weight'], 2)

        plan = {
            'mission': 'QNT50002',
            'plan_id': f"alloc_plan_{uuid.uuid4().hex[:10]}",
            'decision_id': f"alloc_dec_{uuid.uuid4().hex[:10]}",
            'generated_at': int(time.time()),
            'capital': round(capital, 2),
            'reserve_weight': reserve_weight,
            'reserve_capital': round(capital * reserve_weight, 2),
            'deployable_capital': round(deployable_capital, 2),
            'regime': regime,
            'liquidity_state': liquidity_state,
            'max_strategy_weight': max_strategy_weight,
            'allocations': provisional,
            'status': 'proposed',
        }
        state['rebalance_preview'] = plan
        state['last_regime'] = regime
        state['total_capital'] = round(capital, 2)
        save_state(state)
        append_audit('allocation_plan_proposed', {
            'plan_id': plan['plan_id'],
            'decision_id': plan['decision_id'],
            'regime': regime,
            'capital': plan['capital'],
        })
        return plan

    def approve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        plan = payload.get('plan') or state.get('rebalance_preview')
        if not plan:
            raise ValueError('no allocation plan available to approve')
        approver = payload.get('approver') or 'capital_committee'
        notes = payload.get('notes') or 'approved for controlled deployment'
        approved = dict(plan)
        approved['status'] = 'approved'
        approved['approved_at'] = int(time.time())
        approved['approver'] = approver
        approved['approval_notes'] = notes
        state['latest_plan'] = approved
        state.setdefault('history', []).insert(0, approved)
        state['history'] = state['history'][:200]
        state.setdefault('committee_log', []).insert(0, {
            'plan_id': approved['plan_id'],
            'decision_id': approved['decision_id'],
            'approved_at': approved['approved_at'],
            'approver': approver,
            'notes': notes,
        })
        state['committee_log'] = state['committee_log'][:200]
        state.setdefault('export_queue', []).insert(0, self._build_execution_handoff(approved))
        state['export_queue'] = state['export_queue'][:100]
        save_state(state)
        self._sync_execution_decision_memory(approved)
        append_audit('allocation_plan_approved', {
            'plan_id': approved['plan_id'],
            'decision_id': approved['decision_id'],
            'approver': approver,
        })
        return approved

    def _sync_execution_decision_memory(self, approved: Dict[str, Any]) -> None:
        execution_state = load_execution_state()
        execution_state.setdefault('decision_memory', []).insert(0, {
            'decision_id': approved.get('decision_id'),
            'allocation_id': approved.get('plan_id'),
            'strategy_id': 'portfolio_allocation_engine',
            'risk_tag': f"REGIME_{str(approved.get('regime', 'neutral')).upper()}",
            'timestamp': int(time.time()),
        })
        execution_state['decision_memory'] = execution_state['decision_memory'][:500]
        save_execution_state(execution_state)

    def _build_execution_handoff(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        tickets = []
        for allocation in plan.get('allocations', []):
            tickets.append({
                'allocation_id': plan.get('plan_id'),
                'decision_id': plan.get('decision_id'),
                'strategy_id': allocation.get('strategy_id'),
                'symbol': allocation.get('symbol'),
                'target_capital': allocation.get('target_capital'),
                'weight': allocation.get('weight'),
                'risk_tag': f"REGIME_{str(plan.get('regime', 'neutral')).upper()}",
            })
        return {
            'plan_id': plan.get('plan_id'),
            'decision_id': plan.get('decision_id'),
            'generated_at': int(time.time()),
            'tickets': tickets,
        }

    def execution_handoff(self) -> Dict[str, Any]:
        state = self._refresh()
        latest = state.get('latest_plan')
        return {
            'mission': 'QNT50002',
            'latest_plan': latest,
            'handoff': self._build_execution_handoff(latest) if latest else None,
            'queue_depth': len(state.get('export_queue', [])),
        }

    def rebalance_preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        latest = state.get('latest_plan') or state.get('rebalance_preview')
        if not latest:
            raise ValueError('no baseline allocation plan available')
        incoming_capital = float(payload.get('capital_change') or 0.0)
        new_capital = max(float(latest.get('capital') or state.get('total_capital') or 0.0) + incoming_capital, 0.0)
        return self.recommend({
            'capital': new_capital,
            'regime': payload.get('regime') or latest.get('regime') or state.get('last_regime'),
            'liquidity_state': payload.get('liquidity_state') or latest.get('liquidity_state') or 'normal',
            'max_strategy_weight': payload.get('max_strategy_weight') or latest.get('max_strategy_weight') or state.get('max_strategy_weight'),
        })

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        latest = state.get('latest_plan')
        return {
            'mission': 'QNT50002',
            'status': 'ok',
            'safe_mode': state.get('safe_mode', True),
            'execution_mode': state.get('execution_mode', 'paper'),
            'total_capital': state.get('total_capital', 0.0),
            'strategy_count': len(state.get('strategies', [])),
            'last_regime': state.get('last_regime', 'neutral'),
            'latest_plan_id': latest.get('plan_id') if latest else None,
            'latest_plan_status': latest.get('status') if latest else 'none',
            'queue_depth': len(state.get('export_queue', [])),
        }
