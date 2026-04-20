from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.autonomous_control_loop.state_store import load_state as load_control_state
from backend.app.institutional_allocation_execution_charter.state_store import load_state as load_charter_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state

from backend.app.institutional_breach_exception_resolution.state_store import append_audit, default_state, load_state, save_state


class InstitutionalBreachExceptionResolutionEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: Any, digits: int = 4) -> float:
        return round(float(value or 0.0), digits)

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['breach_cases'] = (state.get('breach_cases') or [])[: int(policy.get('max_cases_to_keep', 500))]
        state['exception_resolutions'] = (state.get('exception_resolutions') or [])[: int(policy.get('max_resolutions_to_keep', 500))]
        state['escalation_log'] = (state.get('escalation_log') or [])[: int(policy.get('max_escalations_to_keep', 500))]

    def _source_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        risk = load_risk_state()
        settlement = load_settlement_state()
        charter = load_charter_state()
        control = load_control_state()
        latest_directive = (charter.get('enforcement_directives') or [{}])[0]
        latest_cycle = (control.get('control_cycles') or [{}])[0]
        breaks = settlement.get('reconciliation_breaks') or []
        active_breaks = [x for x in breaks if str(x.get('status') or 'open').lower() not in {'resolved', 'cleared'}]
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'risk_breach_count': int((risk.get('metrics') or {}).get('breach_count') or 0),
            'settlement_break_count': len(active_breaks),
            'latest_break_id': str((active_breaks[0] if active_breaks else {}).get('break_id') or ''),
            'charter_directive_count': len(charter.get('enforcement_directives') or []),
            'latest_directive_id': str(latest_directive.get('directive_id') or ''),
            'latest_directive_status': str(latest_directive.get('directive_status') or ''),
            'control_loop_posture': str(control.get('status') or 'degraded'),
            'latest_cycle_id': str(latest_cycle.get('cycle_id') or ''),
            'escalation_count': len(control.get('escalations') or []),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('institutional_breach_context_synced', snapshot)
        return {'mission': 'QNT50026', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        posture = 'ready'
        open_cases = [x for x in state.get('breach_cases') or [] if x.get('case_status') not in {'resolved', 'rejected', 'closed'}]
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif open_cases:
            posture = 'guarded'
        elif not (state.get('breach_cases') or state.get('exception_resolutions') or state.get('escalation_log')):
            posture = 'degraded'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50026',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'open_case_count': len(open_cases),
            'case_count': len(state.get('breach_cases') or []),
            'resolution_count': len(state.get('exception_resolutions') or []),
            'escalation_count': len(state.get('escalation_log') or []),
            'latest_case': (state.get('breach_cases') or [{}])[0],
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
        append_audit('institutional_breach_configuration_updated', {'policy': policy})
        result = {'mission': 'QNT50026', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def register_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        policy = self._policy(state)
        snapshot = state.get('last_sync') or {}
        directive_id = str(payload.get('directive_id') or snapshot.get('latest_directive_id') or '').strip()
        severity = str(payload.get('severity') or 'medium').strip().lower()
        alignment_score = self._round(payload.get('alignment_score') or 0.0, 4)
        breach_case = {
            'case_id': f'breach_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'breach_type': str(payload.get('breach_type') or 'MANDATE_EXCEPTION').strip(),
            'severity': severity,
            'case_status': 'open',
            'source_system': str(payload.get('source_system') or 'institutional-charter').strip(),
            'directive_id': directive_id,
            'target_strategy': str(payload.get('target_strategy') or '').strip(),
            'requested_action': str(payload.get('requested_action') or '').strip(),
            'alignment_score': alignment_score,
            'root_cause': str(payload.get('root_cause') or '').strip(),
            'summary': str(payload.get('summary') or '').strip(),
            'required_resolution_sla_hours': int(payload.get('required_resolution_sla_hours') or policy.get('default_resolution_sla_hours') or 24),
            'risk_triggered_at_registration': bool(snapshot.get('risk_triggered')),
            'settlement_break_count': int(snapshot.get('settlement_break_count') or 0),
            'needs_supervisory_review': bool(payload.get('needs_supervisory_review', False)),
            'tags': list(payload.get('tags') or []),
        }
        if not breach_case['operator'] or not breach_case['title']:
            raise ValueError('operator and title are required')
        if policy.get('require_charter_directive_context', True) and not breach_case['directive_id']:
            raise ValueError('directive_id is required when charter directive context is enforced')
        if alignment_score and alignment_score < float(policy.get('severe_alignment_threshold') or 60.0):
            breach_case['severity'] = 'severe'
            breach_case['needs_supervisory_review'] = True
        state.setdefault('breach_cases', []).insert(0, breach_case)
        self._trim(state)
        save_state(state)
        append_audit('institutional_breach_case_registered', breach_case)
        return {'mission': 'QNT50026', 'status': 'registered', 'case': breach_case}

    def escalate_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        case_id = str(payload.get('case_id') or '').strip()
        if not case_id:
            raise ValueError('case_id is required')
        breach_case = next((x for x in (state.get('breach_cases') or []) if x.get('case_id') == case_id), None)
        if not breach_case:
            raise ValueError('case_id not found')
        level = str(payload.get('escalation_level') or ('supervisory' if breach_case.get('severity') == 'severe' else 'operations')).strip()
        escalation = {
            'escalation_id': f'escalation_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'case_id': case_id,
            'escalation_level': level,
            'status': 'open',
            'reason': str(payload.get('reason') or '').strip(),
            'directive_id': str(breach_case.get('directive_id') or ''),
            'requires_action': True,
        }
        if not escalation['operator']:
            raise ValueError('operator is required')
        if breach_case.get('severity') == 'severe':
            breach_case['needs_supervisory_review'] = True
        breach_case['case_status'] = 'escalated'
        state.setdefault('escalation_log', []).insert(0, escalation)
        self._trim(state)
        save_state(state)
        append_audit('institutional_breach_case_escalated', escalation)
        return {'mission': 'QNT50026', 'status': 'escalated', 'escalation': escalation, 'case': breach_case}

    def resolve_exception(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        policy = self._policy(state)
        case_id = str(payload.get('case_id') or '').strip()
        if not case_id:
            raise ValueError('case_id is required')
        breach_case = next((x for x in (state.get('breach_cases') or []) if x.get('case_id') == case_id), None)
        if not breach_case:
            raise ValueError('case_id not found')
        resolution_type = str(payload.get('resolution_type') or 'override').strip().lower()
        approved = bool(payload.get('approved', False))
        snapshot = state.get('last_sync') or {}
        if policy.get('require_risk_sync', True) and not state.get('last_sync'):
            raise ValueError('context sync required before resolution')
        if policy.get('require_supervisory_escalation_for_severe', True) and breach_case.get('severity') == 'severe':
            has_supervisory = any(x.get('case_id') == case_id and x.get('escalation_level') == 'supervisory' for x in (state.get('escalation_log') or []))
            if not has_supervisory:
                raise ValueError('supervisory escalation required before resolving severe case')
        if resolution_type == 'override' and snapshot.get('risk_triggered'):
            raise ValueError('cannot approve override while risk kill-switch is active')
        resolution = {
            'resolution_id': f'resolution_{uuid.uuid4().hex[:12]}',
            'resolved_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'case_id': case_id,
            'resolution_type': resolution_type,
            'approved': approved,
            'resolution_status': 'approved' if approved else 'rejected',
            'exception_scope': str(payload.get('exception_scope') or '').strip(),
            'control_actions': list(payload.get('control_actions') or []),
            'expiry_hours': int(payload.get('expiry_hours') or 0),
            'notes': str(payload.get('notes') or '').strip(),
            'directive_id': str(breach_case.get('directive_id') or ''),
        }
        if not resolution['operator']:
            raise ValueError('operator is required')
        breach_case['case_status'] = 'resolved' if approved else 'rejected'
        breach_case['resolved_at'] = resolution['resolved_at']
        breach_case['last_resolution_id'] = resolution['resolution_id']
        state.setdefault('exception_resolutions', []).insert(0, resolution)
        self._trim(state)
        save_state(state)
        append_audit('institutional_exception_resolved', resolution)
        return {'mission': 'QNT50026', 'status': resolution['resolution_status'], 'resolution': resolution, 'case': breach_case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        reason = str(payload.get('reason') or 'manual reset')
        current = self._refresh()
        default = default_state()
        default['audit_log'] = [{
            'event_id': f'institutional_breach_exception_resolution_audit_{time.time_ns()}',
            'event_type': 'institutional_breach_reset',
            'timestamp': int(time.time()),
            'reason': reason,
            'operator': str(payload.get('operator') or '').strip(),
            'prior_case_count': len(current.get('breach_cases') or []),
            'prior_resolution_count': len(current.get('exception_resolutions') or []),
            'prior_escalation_count': len(current.get('escalation_log') or []),
        }]
        save_state(default)
        return {'mission': 'QNT50026', 'status': 'reset', 'reason': reason, 'summary': self.summary()}
