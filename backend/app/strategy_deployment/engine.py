from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from backend.app.allocation.state_store import load_state as load_allocation_state
from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state
from backend.app.strategy_deployment.state_store import append_audit, load_state, save_state


class StrategyDeploymentEngine:
    REGIME_FIT = {
        'preferred': 1.08,
        'neutral': 0.94,
        'mismatch': 0.72,
    }

    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _profiles_by_id(self) -> Dict[str, Dict[str, Any]]:
        state = self._refresh()
        return {item['strategy_id']: item for item in state.get('deployment_profiles', []) if item.get('strategy_id')}

    def _allocation_plan(self) -> Dict[str, Any] | None:
        alloc_state = load_allocation_state()
        return alloc_state.get('latest_plan') or alloc_state.get('rebalance_preview')

    def _deployment_fit(self, profile: Dict[str, Any], regime: str) -> float:
        preferred = set(profile.get('preferred_regimes') or [])
        if regime in preferred:
            return self.REGIME_FIT['preferred']
        if 'neutral' in preferred and regime in {'range', 'neutral'}:
            return self.REGIME_FIT['neutral']
        return self.REGIME_FIT['mismatch']

    def _proposed_action(self, target_weight: float, current_weight: float, preferred: bool) -> str:
        if target_weight <= 0.0001:
            return 'retire'
        if current_weight <= 0.0001 and preferred:
            return 'activate'
        if target_weight > current_weight + 0.03:
            return 'scale_up'
        if current_weight > target_weight + 0.03:
            return 'scale_down'
        return 'hold'

    def list_profiles(self) -> Dict[str, Any]:
        state = self._refresh()
        return {
            'mission': 'QNT50003',
            'profiles': state.get('deployment_profiles', []),
            'count': len(state.get('deployment_profiles', [])),
        }

    def register_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        profile = dict(payload)
        profile['strategy_id'] = profile.get('strategy_id') or f"deploy_{uuid.uuid4().hex[:10]}"
        profile.setdefault('status', 'standby')
        profile.setdefault('enabled', True)
        profile.setdefault('preferred_regimes', ['neutral'])
        profile.setdefault('allowed_brokers', ['paper'])
        state.setdefault('deployment_profiles', []).insert(0, profile)
        save_state(state)
        append_audit('deployment_profile_registered', {
            'strategy_id': profile['strategy_id'],
            'name': profile.get('name'),
        })
        return profile

    def evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        allocation_plan = payload.get('allocation_plan') or self._allocation_plan()
        if not allocation_plan:
            raise ValueError('no allocation plan available for strategy deployment')

        regime = str(payload.get('regime') or allocation_plan.get('regime') or state.get('current_regime') or 'neutral').lower()
        liquidity_state = str(payload.get('liquidity_state') or allocation_plan.get('liquidity_state') or state.get('liquidity_state') or 'normal').lower()
        active_current = {item['strategy_id']: item for item in state.get('active_deployments', []) if item.get('strategy_id')}
        profiles = self._profiles_by_id()
        max_concurrent = int(payload.get('max_concurrent_strategies') or state.get('max_concurrent_strategies') or 3)

        evaluated: List[Dict[str, Any]] = []
        for alloc in allocation_plan.get('allocations', []):
            strategy_id = alloc.get('strategy_id')
            profile = dict(profiles.get(strategy_id) or {})
            if profile and not profile.get('enabled', True):
                continue
            preferred = regime in set(profile.get('preferred_regimes') or [])
            readiness = float(profile.get('deployment_readiness') or 0.80)
            regime_fit = self._deployment_fit(profile, regime)
            alloc_weight = float(alloc.get('weight') or 0.0)
            current_weight = float((active_current.get(strategy_id) or {}).get('target_weight') or 0.0)
            capped_weight = min(alloc_weight, float(profile.get('max_live_weight') or state.get('max_strategy_weight') or 0.40))
            priority = round((float(alloc.get('score') or 0.0) + alloc_weight) * readiness * regime_fit, 8)
            evaluated.append({
                'strategy_id': strategy_id,
                'name': alloc.get('name') or profile.get('name'),
                'symbol': alloc.get('symbol') or profile.get('symbol'),
                'asset_class': alloc.get('asset_class') or profile.get('asset_class'),
                'target_capital': round(float(alloc.get('target_capital') or 0.0), 2),
                'target_weight': round(capped_weight, 6),
                'allocation_weight': round(alloc_weight, 6),
                'current_weight': round(current_weight, 6),
                'priority_score': priority,
                'regime_fit': round(regime_fit, 4),
                'readiness': readiness,
                'preferred_regimes': profile.get('preferred_regimes') or [],
                'allowed_brokers': profile.get('allowed_brokers') or ['paper'],
                'warmup_required': bool(profile.get('warmup_required', False)),
                'routing_action': self._proposed_action(capped_weight, current_weight, preferred),
                'status': 'candidate',
            })

        if not evaluated:
            raise ValueError('no strategy candidates available for deployment')

        selected = sorted(evaluated, key=lambda item: item['priority_score'], reverse=True)[:max_concurrent]
        selected_ids = {item['strategy_id'] for item in selected}
        deployments: List[Dict[str, Any]] = []
        for item in selected:
            item['status'] = 'selected'
            deployments.append(item)

        for item in state.get('active_deployments', []):
            strategy_id = item.get('strategy_id')
            if strategy_id and strategy_id not in selected_ids:
                deployments.append({
                    'strategy_id': strategy_id,
                    'name': item.get('name'),
                    'symbol': item.get('symbol'),
                    'asset_class': item.get('asset_class'),
                    'target_capital': 0.0,
                    'target_weight': 0.0,
                    'allocation_weight': 0.0,
                    'current_weight': round(float(item.get('target_weight') or 0.0), 6),
                    'priority_score': 0.0,
                    'regime_fit': 0.0,
                    'readiness': 1.0,
                    'preferred_regimes': item.get('preferred_regimes') or [],
                    'allowed_brokers': item.get('allowed_brokers') or ['paper'],
                    'warmup_required': False,
                    'routing_action': 'retire',
                    'status': 'selected',
                })

        plan = {
            'mission': 'QNT50003',
            'deployment_id': f"deploy_plan_{uuid.uuid4().hex[:10]}",
            'decision_id': f"deploy_dec_{uuid.uuid4().hex[:10]}",
            'generated_at': int(time.time()),
            'regime': regime,
            'liquidity_state': liquidity_state,
            'source_allocation_id': allocation_plan.get('plan_id'),
            'source_decision_id': allocation_plan.get('decision_id'),
            'safe_mode': bool(state.get('safe_mode', True)),
            'execution_mode': state.get('execution_mode', 'paper'),
            'max_concurrent_strategies': max_concurrent,
            'deployments': deployments,
            'status': 'proposed',
        }
        state['current_regime'] = regime
        state['liquidity_state'] = liquidity_state
        state['current_plan'] = plan
        save_state(state)
        append_audit('deployment_plan_proposed', {
            'deployment_id': plan['deployment_id'],
            'decision_id': plan['decision_id'],
            'source_allocation_id': plan.get('source_allocation_id'),
            'regime': regime,
        })
        return plan

    def _build_release_ticket(self, plan: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        broker = (item.get('allowed_brokers') or ['paper'])[0]
        if plan.get('safe_mode', True):
            broker = 'paper'
        return {
            'deployment_id': plan.get('deployment_id'),
            'decision_id': plan.get('decision_id'),
            'source_allocation_id': plan.get('source_allocation_id'),
            'source_decision_id': plan.get('source_decision_id'),
            'strategy_id': item.get('strategy_id'),
            'symbol': item.get('symbol'),
            'target_capital': item.get('target_capital'),
            'target_weight': item.get('target_weight'),
            'routing_action': item.get('routing_action'),
            'broker': broker,
            'regime': plan.get('regime'),
            'risk_tag': f"DEPLOY_{str(plan.get('regime', 'neutral')).upper()}",
            'staged_at': int(time.time()),
        }

    def deploy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        plan = payload.get('plan') or state.get('current_plan')
        if not plan:
            raise ValueError('no strategy deployment plan available to approve')
        approver = payload.get('approver') or 'deployment_committee'
        notes = payload.get('notes') or 'approved for controlled deployment'
        approved = dict(plan)
        approved['status'] = 'approved'
        approved['approved_at'] = int(time.time())
        approved['approver'] = approver
        approved['approval_notes'] = notes
        release_queue = [self._build_release_ticket(approved, item) for item in approved.get('deployments', [])]
        active_deployments = []
        for item in approved.get('deployments', []):
            if item.get('routing_action') != 'retire' and float(item.get('target_weight') or 0.0) > 0:
                entry = dict(item)
                entry['status'] = 'active'
                active_deployments.append(entry)

        state['current_plan'] = approved
        state['active_deployments'] = active_deployments
        state.setdefault('release_queue', []).insert(0, {
            'deployment_id': approved['deployment_id'],
            'decision_id': approved['decision_id'],
            'tickets': release_queue,
            'approved_at': approved['approved_at'],
        })
        state['release_queue'] = state['release_queue'][:100]
        state.setdefault('history', []).insert(0, approved)
        state['history'] = state['history'][:200]
        save_state(state)
        self._sync_execution_memory(approved, release_queue)
        append_audit('deployment_plan_approved', {
            'deployment_id': approved['deployment_id'],
            'decision_id': approved['decision_id'],
            'approver': approver,
            'release_count': len(release_queue),
        })
        return {
            'mission': 'QNT50003',
            'status': 'approved',
            'plan': approved,
            'release_queue': release_queue,
        }

    def _sync_execution_memory(self, plan: Dict[str, Any], release_queue: List[Dict[str, Any]]) -> None:
        execution_state = load_execution_state()
        execution_state.setdefault('decision_memory', []).insert(0, {
            'decision_id': plan.get('decision_id'),
            'allocation_id': plan.get('deployment_id'),
            'strategy_id': 'strategy_deployment_engine',
            'risk_tag': f"DEPLOY_{str(plan.get('regime', 'neutral')).upper()}",
            'timestamp': int(time.time()),
        })
        execution_state.setdefault('deployment_queue', []).insert(0, {
            'deployment_id': plan.get('deployment_id'),
            'decision_id': plan.get('decision_id'),
            'tickets': release_queue,
            'generated_at': int(time.time()),
        })
        execution_state['decision_memory'] = execution_state['decision_memory'][:500]
        execution_state['deployment_queue'] = execution_state['deployment_queue'][:200]
        save_execution_state(execution_state)

    def switch_regime(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        regime = str(payload.get('regime') or state.get('current_regime') or 'neutral').lower()
        liquidity_state = str(payload.get('liquidity_state') or state.get('liquidity_state') or 'normal').lower()
        state['current_regime'] = regime
        state['liquidity_state'] = liquidity_state
        save_state(state)
        append_audit('deployment_regime_switched', {
            'regime': regime,
            'liquidity_state': liquidity_state,
        })
        if payload.get('force_redeploy', False):
            plan = self.evaluate({'regime': regime, 'liquidity_state': liquidity_state})
            return {
                'mission': 'QNT50003',
                'status': 're-evaluated',
                'plan': plan,
            }
        return {
            'mission': 'QNT50003',
            'status': 'updated',
            'regime': regime,
            'liquidity_state': liquidity_state,
        }

    def release_queue(self) -> Dict[str, Any]:
        state = self._refresh()
        latest = state.get('release_queue', [])
        return {
            'mission': 'QNT50003',
            'queue_depth': len(latest),
            'latest_release': latest[0] if latest else None,
        }

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        current_plan = state.get('current_plan') or {}
        return {
            'mission': 'QNT50003',
            'status': 'ok',
            'safe_mode': bool(state.get('safe_mode', True)),
            'execution_mode': state.get('execution_mode', 'paper'),
            'current_regime': state.get('current_regime', 'neutral'),
            'liquidity_state': state.get('liquidity_state', 'normal'),
            'profile_count': len(state.get('deployment_profiles', [])),
            'active_strategy_count': len(state.get('active_deployments', [])),
            'current_plan_id': current_plan.get('deployment_id'),
            'current_plan_status': current_plan.get('status', 'none'),
            'release_queue_depth': len(state.get('release_queue', [])),
        }
