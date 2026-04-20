from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.autonomous_control_loop.state_store import load_state as load_control_state
from backend.app.institutional_breach_exception_resolution.state_store import load_state as load_breach_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state

from backend.app.autonomous_remediation_recovery.state_store import append_audit, load_state, save_state


class AutonomousRemediationRecoveryEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['remediation_actions'] = (state.get('remediation_actions') or [])[: int(policy.get('max_open_actions', 250))]
        state['recovery_cycles'] = (state.get('recovery_cycles') or [])[: int(policy.get('max_recovery_cycles', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        breach = load_breach_state()
        risk = load_risk_state()
        treasury = load_treasury_state()
        control = load_control_state()
        cases = breach.get('breach_cases') or []
        open_cases = [x for x in cases if str(x.get('case_status') or 'open').lower() not in {'resolved', 'closed', 'rejected'}]
        severe_open = [x for x in open_cases if str(x.get('severity') or '').lower() == 'severe']
        resolutions = breach.get('exception_resolutions') or []
        latest_resolution = resolutions[0] if resolutions else {}
        latest_case = open_cases[0] if open_cases else (cases[0] if cases else {})
        transfers = treasury.get('transfers') or []
        pending_transfers = [x for x in transfers if str(x.get('status') or 'pending').lower() not in {'executed', 'completed', 'settled', 'cancelled'}]
        cycles = control.get('control_cycles') or []
        latest_cycle = cycles[0] if cycles else {}
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'open_breach_count': len(open_cases),
            'severe_open_breach_count': len(severe_open),
            'latest_case_id': str(latest_case.get('case_id') or ''),
            'latest_case_status': str(latest_case.get('case_status') or ''),
            'latest_case_severity': str(latest_case.get('severity') or ''),
            'latest_resolution_id': str(latest_resolution.get('resolution_id') or ''),
            'latest_resolution_status': str(latest_resolution.get('resolution_status') or ''),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'pending_treasury_transfer_count': len(pending_transfers),
            'control_loop_posture': str(control.get('status') or 'degraded'),
            'latest_cycle_id': str(latest_cycle.get('cycle_id') or ''),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('autonomous_remediation_context_synced', snapshot)
        return {'mission': 'QNT50027', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        actions = state.get('remediation_actions') or []
        open_actions = [x for x in actions if str(x.get('status') or '').lower() not in {'closed', 'rejected'}]
        cycles = state.get('recovery_cycles') or []
        posture = 'ready'
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif snapshot.get('open_breach_count', 0) > 0 or open_actions:
            posture = 'guarded'
        elif not actions and not cycles:
            posture = 'degraded'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50027',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'open_action_count': len(open_actions),
            'action_count': len(actions),
            'recovery_cycle_count': len(cycles),
            'latest_action': (actions or [{}])[0],
            'latest_cycle': (cycles or [{}])[0],
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
        append_audit('autonomous_remediation_configuration_updated', {'policy': policy})
        result = {'mission': 'QNT50027', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def register_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        if policy.get('require_breach_sync', True) and not snapshot:
            raise ValueError('context sync required before remediation registration')
        case_id = str(payload.get('case_id') or snapshot.get('latest_case_id') or '').strip()
        if not case_id:
            raise ValueError('case_id is required')
        actions = state.get('remediation_actions') or []
        existing = next((x for x in actions if x.get('case_id') == case_id and str(x.get('status') or '').lower() not in {'closed', 'rejected'}), None)
        if existing:
            raise ValueError('open remediation action already exists for this case_id')
        action = {
            'action_id': f'remediation_action_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'case_id': case_id,
            'resolution_id': str(payload.get('resolution_id') or snapshot.get('latest_resolution_id') or '').strip(),
            'directive_id': str(payload.get('directive_id') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'remediation_type': str(payload.get('remediation_type') or 'containment').strip(),
            'priority': str(payload.get('priority') or 'high').strip().lower(),
            'status': 'registered',
            'target_strategy': str(payload.get('target_strategy') or '').strip(),
            'target_broker': str(payload.get('target_broker') or '').strip(),
            'requested_actions': list(payload.get('requested_actions') or []),
            'capital_at_risk': round(float(payload.get('capital_at_risk') or 0.0), 4),
            'estimated_recovery_pct': round(float(payload.get('estimated_recovery_pct') or 0.0), 4),
            'requires_human_confirmation': bool(payload.get('requires_human_confirmation', False)),
            'notes': str(payload.get('notes') or '').strip(),
        }
        if not action['operator'] or not action['title']:
            raise ValueError('operator and title are required')
        state.setdefault('remediation_actions', []).insert(0, action)
        self._trim(state)
        save_state(state)
        append_audit('autonomous_remediation_action_registered', action)
        return {'mission': 'QNT50027', 'status': 'registered', 'action': action}

    def authorize_recovery(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        action_id = str(payload.get('action_id') or '').strip()
        actions = state.get('remediation_actions') or []
        action = next((x for x in actions if x.get('action_id') == action_id), None)
        if not action:
            raise ValueError('action_id not found')
        if self._policy(state).get('require_supervisory_resolution_for_severe_cases', True) and str(snapshot.get('latest_case_severity') or '').lower() == 'severe':
            if str(snapshot.get('latest_resolution_status') or '').lower() not in {'approved', 'authorized'}:
                raise ValueError('approved exception resolution required before recovery authorization')
        action['status'] = 'authorized'
        action['authorized_at'] = int(time.time())
        action['authorized_by'] = str(payload.get('operator') or '').strip()
        action['recovery_instruction'] = str(payload.get('recovery_instruction') or '').strip()
        action['required_confidence_score'] = round(float(payload.get('required_confidence_score') or 0.0), 4)
        save_state(state)
        append_audit('autonomous_recovery_authorized', {'action_id': action_id, 'authorized_by': action['authorized_by']})
        return {'mission': 'QNT50027', 'status': 'authorized', 'action': action}

    def execute_recovery(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        action_id = str(payload.get('action_id') or '').strip()
        actions = state.get('remediation_actions') or []
        action = next((x for x in actions if x.get('action_id') == action_id), None)
        if not action:
            raise ValueError('action_id not found')
        if str(action.get('status') or '').lower() != 'authorized':
            raise ValueError('action must be authorized before execution')
        if self._policy(state).get('require_risk_clearance_for_execute', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot execute recovery while risk kill-switch is active')
        cycle = {
            'cycle_id': f'recovery_cycle_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'action_id': action_id,
            'case_id': action.get('case_id'),
            'execution_mode': str(payload.get('execution_mode') or 'controlled').strip(),
            'status': 'executed',
            'steps_executed': list(payload.get('steps_executed') or action.get('requested_actions') or []),
            'recovered_capital': round(float(payload.get('recovered_capital') or 0.0), 4),
            'residual_risk_score': round(float(payload.get('residual_risk_score') or 0.0), 4),
            'result_summary': str(payload.get('result_summary') or '').strip(),
        }
        action['status'] = 'executed'
        action['last_cycle_id'] = cycle['cycle_id']
        action['executed_at'] = cycle['executed_at']
        state.setdefault('recovery_cycles', []).insert(0, cycle)
        self._trim(state)
        save_state(state)
        append_audit('autonomous_recovery_executed', cycle)
        return {'mission': 'QNT50027', 'status': 'executed', 'cycle': cycle, 'action': action}

    def close_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        action_id = str(payload.get('action_id') or '').strip()
        actions = state.get('remediation_actions') or []
        action = next((x for x in actions if x.get('action_id') == action_id), None)
        if not action:
            raise ValueError('action_id not found')
        if str(action.get('status') or '').lower() not in {'executed', 'authorized', 'registered'}:
            raise ValueError('action is not eligible for closure')
        action['status'] = 'closed'
        action['closed_at'] = int(time.time())
        action['closed_by'] = str(payload.get('operator') or '').strip()
        action['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('autonomous_remediation_closed', {'action_id': action_id, 'closed_by': action['closed_by']})
        return {'mission': 'QNT50027', 'status': 'closed', 'action': action}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self._refresh()
        defaults = load_state()
        defaults = {
            'generated_by': 'QNT50027',
            'status': 'ready',
            'policy': current.get('policy') or defaults.get('policy'),
            'last_sync': None,
            'sync_history': [],
            'remediation_actions': [],
            'recovery_cycles': [],
            'audit_log': [],
        }
        save_state(defaults)
        append_audit('autonomous_remediation_reset', {
            'operator': str(payload.get('operator') or '').strip(),
            'reason': str(payload.get('reason') or 'manual reset').strip(),
            'prior_action_count': len(current.get('remediation_actions') or []),
            'prior_cycle_count': len(current.get('recovery_cycles') or []),
        })
        return {'mission': 'QNT50027', 'status': 'reset'}
