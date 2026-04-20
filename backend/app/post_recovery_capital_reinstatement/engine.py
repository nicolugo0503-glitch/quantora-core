from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.autonomous_remediation_recovery.state_store import load_state as load_remediation_state
from backend.app.institutional_breach_exception_resolution.state_store import load_state as load_breach_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state

from backend.app.post_recovery_capital_reinstatement.state_store import append_audit, default_state, load_state, save_state


class PostRecoveryCapitalReinstatementEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['reauthorization_cases'] = (state.get('reauthorization_cases') or [])[: int(policy.get('max_reauthorization_cases', 250))]
        state['reinstatement_events'] = (state.get('reinstatement_events') or [])[: int(policy.get('max_reinstatement_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        remediation = load_remediation_state()
        breach = load_breach_state()
        risk = load_risk_state()
        treasury = load_treasury_state()

        actions = remediation.get('remediation_actions') or []
        cycles = remediation.get('recovery_cycles') or []
        latest_action = actions[0] if actions else {}
        latest_cycle = cycles[0] if cycles else {}
        resolutions = breach.get('exception_resolutions') or []
        latest_resolution = resolutions[0] if resolutions else {}
        open_cases = [x for x in (breach.get('breach_cases') or []) if str(x.get('case_status') or '').lower() not in {'resolved', 'closed', 'rejected'}]
        accounts = treasury.get('accounts') or {}
        total_treasury_balance = round(sum(float((v or {}).get('balance') or 0.0) for v in accounts.values()), 4)
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'latest_action_id': str(latest_action.get('action_id') or ''),
            'latest_action_status': str(latest_action.get('status') or ''),
            'latest_cycle_id': str(latest_cycle.get('cycle_id') or ''),
            'latest_recovered_capital': round(float(latest_cycle.get('recovered_capital') or 0.0), 4),
            'latest_resolution_id': str(latest_resolution.get('resolution_id') or ''),
            'latest_resolution_status': str(latest_resolution.get('resolution_status') or ''),
            'open_breach_count': len(open_cases),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'treasury_total_balance': total_treasury_balance,
            'operating_balance': round(float((accounts.get('operating') or {}).get('balance') or 0.0), 4),
            'broker_buffer_balance': round(float((accounts.get('broker_buffer') or {}).get('balance') or 0.0), 4),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('post_recovery_capital_context_synced', snapshot)
        return {'mission': 'QNT50028', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        cases = state.get('reauthorization_cases') or []
        open_cases = [x for x in cases if str(x.get('status') or '').lower() not in {'closed', 'rejected'}]
        posture = 'ready'
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif open_cases:
            posture = 'guarded'
        elif not (cases or state.get('reinstatement_events')):
            posture = 'degraded'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50028',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'reauthorization_count': len(cases),
            'open_reauthorization_count': len(open_cases),
            'reinstatement_event_count': len(state.get('reinstatement_events') or []),
            'latest_reauthorization': (cases or [{}])[0],
            'latest_reinstatement': (state.get('reinstatement_events') or [{}])[0],
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key, value in payload.items():
            if key == 'sync_after_configure':
                continue
            if value is not None:
                policy[key] = value
        state['policy'] = policy
        self._trim(state)
        save_state(state)
        append_audit('post_recovery_capital_configuration_updated', {'policy': policy})
        result = {'mission': 'QNT50028', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def register_reauthorization(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        action_id = str(payload.get('action_id') or '').strip()
        cycle_id = str(payload.get('cycle_id') or snapshot.get('latest_cycle_id') or '').strip()
        if not action_id:
            raise ValueError('action_id is required')
        if policy.get('require_recovery_execution_for_approval', True) and not cycle_id:
            raise ValueError('recovery cycle evidence is required')
        if policy.get('require_positive_capital_recovered', True) and float(snapshot.get('latest_recovered_capital') or 0.0) <= 0:
            raise ValueError('positive recovered capital required before reauthorization registration')
        existing = next((x for x in (state.get('reauthorization_cases') or []) if x.get('action_id') == action_id and str(x.get('status') or '').lower() not in {'closed', 'rejected'}), None)
        if existing:
            raise ValueError('open reauthorization case already exists for this action_id')
        requested_capital = round(float(payload.get('requested_capital') or snapshot.get('latest_recovered_capital') or 0.0), 4)
        if requested_capital <= 0:
            raise ValueError('requested_capital must be greater than zero')
        case = {
            'reauthorization_id': f'reauthorization_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'action_id': action_id,
            'cycle_id': cycle_id,
            'case_id': str(payload.get('case_id') or '').strip(),
            'resolution_id': str(payload.get('resolution_id') or snapshot.get('latest_resolution_id') or '').strip(),
            'target_strategy': str(payload.get('target_strategy') or '').strip(),
            'target_broker': str(payload.get('target_broker') or '').strip(),
            'requested_capital': requested_capital,
            'reinstatement_pct': round(float(payload.get('reinstatement_pct') or 0.0), 4),
            'status': 'registered',
            'rationale': str(payload.get('rationale') or '').strip(),
            'notes': str(payload.get('notes') or '').strip(),
        }
        if not case['operator'] or not case['title']:
            raise ValueError('operator and title are required')
        state.setdefault('reauthorization_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('post_recovery_reauthorization_registered', case)
        return {'mission': 'QNT50028', 'status': 'registered', 'reauthorization': case}

    def approve_reinstatement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        reauthorization_id = str(payload.get('reauthorization_id') or '').strip()
        case = next((x for x in (state.get('reauthorization_cases') or []) if x.get('reauthorization_id') == reauthorization_id), None)
        if not case:
            raise ValueError('reauthorization_id not found')
        if snapshot.get('risk_triggered'):
            raise ValueError('cannot approve reinstatement while risk kill-switch is active')
        if self._policy(state).get('require_recovery_execution_for_approval', True) and not case.get('cycle_id'):
            raise ValueError('executed recovery cycle required before approval')
        approved_capital = round(float(payload.get('approved_capital') or case.get('requested_capital') or 0.0), 4)
        if approved_capital <= 0:
            raise ValueError('approved_capital must be greater than zero')
        if self._policy(state).get('require_treasury_capacity', True) and approved_capital > float(snapshot.get('treasury_total_balance') or 0.0):
            raise ValueError('approved capital exceeds treasury capacity')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_capital'] = approved_capital
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('post_recovery_reinstatement_approved', {'reauthorization_id': reauthorization_id, 'approved_capital': approved_capital})
        return {'mission': 'QNT50028', 'status': 'approved', 'reauthorization': case}

    def execute_reinstatement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        reauthorization_id = str(payload.get('reauthorization_id') or '').strip()
        case = next((x for x in (state.get('reauthorization_cases') or []) if x.get('reauthorization_id') == reauthorization_id), None)
        if not case:
            raise ValueError('reauthorization_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('reauthorization must be approved before execution')
        if self._policy(state).get('require_risk_clearance_for_execution', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot execute reinstatement while risk kill-switch is active')
        capital_reinstated = round(float(payload.get('capital_reinstated') or case.get('approved_capital') or 0.0), 4)
        if capital_reinstated <= 0:
            raise ValueError('capital_reinstated must be greater than zero')
        event = {
            'event_id': f'reinstatement_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'reauthorization_id': reauthorization_id,
            'action_id': case.get('action_id'),
            'cycle_id': case.get('cycle_id'),
            'execution_mode': str(payload.get('execution_mode') or 'controlled').strip(),
            'destination_account': str(payload.get('destination_account') or 'broker_buffer').strip(),
            'capital_reinstated': capital_reinstated,
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_event_id'] = event['event_id']
        state.setdefault('reinstatement_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('post_recovery_reinstatement_executed', event)
        return {'mission': 'QNT50028', 'status': 'executed', 'reauthorization': case, 'event': event}

    def close_reauthorization(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        reauthorization_id = str(payload.get('reauthorization_id') or '').strip()
        case = next((x for x in (state.get('reauthorization_cases') or []) if x.get('reauthorization_id') == reauthorization_id), None)
        if not case:
            raise ValueError('reauthorization_id not found')
        if self._policy(state).get('require_closed_action_for_close', True):
            remediation_actions = load_remediation_state().get('remediation_actions') or []
            action = next((x for x in remediation_actions if x.get('action_id') == case.get('action_id')), None)
            if action and str(action.get('status') or '').lower() != 'closed':
                raise ValueError('linked remediation action must be closed before reauthorization closure')
        if str(case.get('status') or '').lower() not in {'executed', 'approved', 'registered'}:
            raise ValueError('reauthorization is not eligible for closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('post_recovery_reauthorization_closed', {'reauthorization_id': reauthorization_id, 'closed_by': case['closed_by']})
        return {'mission': 'QNT50028', 'status': 'closed', 'reauthorization': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self._refresh()
        defaults = default_state()
        defaults = {
            'generated_by': 'QNT50028',
            'status': 'ready',
            'policy': current.get('policy') or defaults.get('policy'),
            'last_sync': None,
            'sync_history': [],
            'reauthorization_cases': [],
            'reinstatement_events': [],
            'audit_log': [],
        }
        save_state(defaults)
        append_audit('post_recovery_capital_reset', {
            'operator': str(payload.get('operator') or '').strip(),
            'reason': str(payload.get('reason') or 'manual reset').strip(),
            'prior_reauthorization_count': len(current.get('reauthorization_cases') or []),
            'prior_reinstatement_event_count': len(current.get('reinstatement_events') or []),
        })
        return {'mission': 'QNT50028', 'status': 'reset'}
