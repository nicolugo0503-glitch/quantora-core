from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.live_capital_reactivation.state_store import append_audit, default_state, load_state, save_state
from backend.app.post_recovery_capital_reinstatement.state_store import load_state as load_reauthorization_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_strategy_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class LiveCapitalReactivationEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self):
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(default_state().get('policy', {}), **(state.get('policy') or {}))

    def _trim(self, state: Dict[str, Any]):
        policy = self._policy(state)
        state['reactivation_cases'] = (state.get('reactivation_cases') or [])[: int(policy.get('max_reactivation_cases', 250))]
        state['reentry_events'] = (state.get('reentry_events') or [])[: int(policy.get('max_reentry_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        reauth = load_reauthorization_state()
        risk = load_risk_state()
        strategy = load_strategy_state()
        treasury = load_treasury_state()
        reauth_cases = reauth.get('reauthorization_cases') or []
        reentry_profiles = strategy.get('deployment_profiles') or []
        accounts = treasury.get('accounts') or {}
        total_treasury_balance = round(sum(float((v or {}).get('balance') or 0.0) for v in accounts.values()), 4)
        return {
            'synced_at': int(time.time()),
            'source': 'manual',
            'latest_reauthorization_id': (reauth_cases[0] or {}).get('reauthorization_id') if reauth_cases else '',
            'latest_reauthorization_status': (reauth_cases[0] or {}).get('status') if reauth_cases else '',
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': risk.get('kill_switch_level', 'normal'),
            'safe_mode': bool(strategy.get('safe_mode', True)),
            'execution_mode': str(strategy.get('execution_mode') or 'paper'),
            'current_regime': str(strategy.get('current_regime') or 'neutral'),
            'deployment_profiles': reentry_profiles,
            'treasury_total_balance': total_treasury_balance,
            'operating_balance': float((accounts.get('operating') or {}).get('balance') or 0.0),
            'broker_buffer_balance': float((accounts.get('broker_buffer') or {}).get('balance') or 0.0),
        }

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot()
        snapshot['source'] = str(payload.get('source') or 'manual')
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('live_capital_reactivation_context_synced', snapshot)
        return {'mission': 'QNT50029', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if not state.get('last_sync') and self._policy(state).get('auto_sync_sources', True):
            self.sync_context({'source': source})
            return self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key, value in payload.items():
            if key in policy and value is not None:
                policy[key] = value
        state['policy'] = policy
        self._trim(state)
        save_state(state)
        append_audit('live_capital_reactivation_configured', {'policy': policy})
        result = {'mission': 'QNT50029', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        active = [x for x in (state.get('reactivation_cases') or []) if str(x.get('status') or '').lower() not in {'closed', 'rejected'}]
        return {
            'mission': 'QNT50029',
            'posture': 'guarded' if snapshot.get('safe_mode') else 'controlled',
            'risk_triggered': bool(snapshot.get('risk_triggered')),
            'safe_mode': bool(snapshot.get('safe_mode')),
            'reactivation_case_count': len(state.get('reactivation_cases') or []),
            'open_reactivation_case_count': len(active),
            'reentry_event_count': len(state.get('reentry_events') or []),
            'current_regime': snapshot.get('current_regime'),
            'execution_mode': snapshot.get('execution_mode'),
            'treasury_total_balance': snapshot.get('treasury_total_balance'),
        }

    def register_reactivation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        reauthorization_id = str(payload.get('reauthorization_id') or '').strip()
        strategy_id = str(payload.get('strategy_id') or '').strip()
        if not reauthorization_id or not strategy_id:
            raise ValueError('reauthorization_id and strategy_id are required')
        reauth_state = load_reauthorization_state()
        reauth_case = next((x for x in (reauth_state.get('reauthorization_cases') or []) if x.get('reauthorization_id') == reauthorization_id), None)
        if not reauth_case:
            raise ValueError('reauthorization_id not found')
        if policy.get('require_reauthorization_execution', True) and str(reauth_case.get('status') or '').lower() != 'executed':
            raise ValueError('reauthorization must be executed before live capital reactivation registration')
        profile = next((x for x in (snapshot.get('deployment_profiles') or []) if x.get('strategy_id') == strategy_id), None)
        if policy.get('require_strategy_profile_match', True) and not profile:
            raise ValueError('strategy deployment profile required for strategy re-entry')
        requested_capital = round(float(payload.get('requested_capital') or reauth_case.get('approved_capital') or reauth_case.get('requested_capital') or 0.0), 4)
        if requested_capital <= 0:
            raise ValueError('requested_capital must be greater than zero')
        if policy.get('require_treasury_capacity', True) and requested_capital > float(snapshot.get('treasury_total_balance') or 0.0):
            raise ValueError('requested capital exceeds treasury capacity')
        case = {
            'reactivation_id': f'reactivation_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'reauthorization_id': reauthorization_id,
            'strategy_id': strategy_id,
            'symbol': str(payload.get('symbol') or (profile or {}).get('symbol') or '').strip(),
            'broker': str(payload.get('broker') or ((profile or {}).get('allowed_brokers') or ['paper'])[0]).strip(),
            'requested_capital': requested_capital,
            'requested_weight': round(float(payload.get('requested_weight') or 0.0), 4),
            'reentry_reason': str(payload.get('reentry_reason') or '').strip(),
            'notes': str(payload.get('notes') or '').strip(),
            'regime': snapshot.get('current_regime', 'neutral'),
            'status': 'registered',
        }
        if not case['operator'] or not case['title']:
            raise ValueError('operator and title are required')
        state.setdefault('reactivation_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('live_capital_reactivation_registered', case)
        return {'mission': 'QNT50029', 'status': 'registered', 'reactivation': case}

    def approve_reentry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        reactivation_id = str(payload.get('reactivation_id') or '').strip()
        case = next((x for x in (state.get('reactivation_cases') or []) if x.get('reactivation_id') == reactivation_id), None)
        if not case:
            raise ValueError('reactivation_id not found')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot approve re-entry while risk kill-switch is active')
        approved_capital = round(float(payload.get('approved_capital') or case.get('requested_capital') or 0.0), 4)
        approved_weight = round(float(payload.get('approved_weight') or case.get('requested_weight') or 0.0), 4)
        if approved_capital <= 0:
            raise ValueError('approved_capital must be greater than zero')
        mode = str(payload.get('mode') or 'paper').strip().lower()
        if mode == 'live' and (snapshot.get('safe_mode') or not policy.get('allow_live_mode', False)):
            raise ValueError('live mode approval is blocked while safe mode is enabled or live mode policy is disabled')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_capital'] = approved_capital
        case['approved_weight'] = approved_weight
        case['approved_mode'] = mode
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('live_capital_reentry_approved', {'reactivation_id': reactivation_id, 'approved_capital': approved_capital, 'mode': mode})
        return {'mission': 'QNT50029', 'status': 'approved', 'reactivation': case}

    def execute_reentry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        reactivation_id = str(payload.get('reactivation_id') or '').strip()
        case = next((x for x in (state.get('reactivation_cases') or []) if x.get('reactivation_id') == reactivation_id), None)
        if not case:
            raise ValueError('reactivation_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('reactivation must be approved before execution')
        mode = str(payload.get('execution_mode') or case.get('approved_mode') or 'paper').strip().lower()
        if mode == 'live' and (snapshot.get('risk_triggered') or snapshot.get('safe_mode')):
            raise ValueError('live execution blocked by risk or safe mode posture')
        capital_activated = round(float(payload.get('capital_activated') or case.get('approved_capital') or 0.0), 4)
        if capital_activated <= 0:
            raise ValueError('capital_activated must be greater than zero')
        event = {
            'event_id': f'reentry_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'reactivation_id': reactivation_id,
            'reauthorization_id': case.get('reauthorization_id'),
            'strategy_id': case.get('strategy_id'),
            'symbol': case.get('symbol'),
            'broker': case.get('broker'),
            'execution_mode': mode,
            'capital_activated': capital_activated,
            'release_to': str(payload.get('release_to') or 'execution_queue').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_event_id'] = event['event_id']
        state.setdefault('reentry_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('live_capital_reentry_executed', event)
        return {'mission': 'QNT50029', 'status': 'executed', 'reactivation': case, 'event': event}

    def close_reactivation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        reactivation_id = str(payload.get('reactivation_id') or '').strip()
        case = next((x for x in (state.get('reactivation_cases') or []) if x.get('reactivation_id') == reactivation_id), None)
        if not case:
            raise ValueError('reactivation_id not found')
        if str(case.get('status') or '').lower() not in {'executed', 'approved', 'registered'}:
            raise ValueError('reactivation is not eligible for closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('live_capital_reactivation_closed', {'reactivation_id': reactivation_id, 'closed_by': case['closed_by']})
        return {'mission': 'QNT50029', 'status': 'closed', 'reactivation': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        state = default_state()
        save_state(state)
        append_audit('live_capital_reactivation_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50029', 'status': 'reset', 'state': state}
