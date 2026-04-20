from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.cross_border_service_routing.state_store import append_audit, default_state, load_state, save_state


class CrossBorderServiceRoutingEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self):
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict((state.get('policy') or {}).get('policy', state.get('policy') or {}))

    def _trim(self, state: Dict[str, Any]):
        policy = self._policy(state)
        state['route_cases'] = (state.get('route_cases') or [])[: int(policy.get('max_route_cases', 250))]
        state['routing_events'] = (state.get('routing_events') or [])[: int(policy.get('max_routing_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            'synced_at': int(time.time()),
            'safe_mode': True,
            'risk_triggered': False,
            'execution_mode': 'paper',
            'latest_partition_event_id': '',
            'latest_partition_status': '',
            'compliance_clear': True,
            'active_boundary_policy_id': '',
            'latest_compliance_decision_id': '',
            'treasury_total_balance': 0.0,
        }
        try:
            from backend.app.multi_region_service_partition.state_store import load_state as load_region_state
            region = load_region_state()
            events = region.get('partition_events') or []
            latest = events[0] if events else {}
            snap['latest_partition_event_id'] = latest.get('partition_event_id', '')
            snap['latest_partition_status'] = latest.get('status', '')
        except Exception:
            pass
        try:
            from backend.app.risk_control.state_store import load_state as load_risk_state
            risk = load_risk_state()
            summary = risk.get('last_summary') or {}
            snap['safe_mode'] = bool(summary.get('safe_mode', True))
            snap['risk_triggered'] = bool(summary.get('kill_switch_triggered', summary.get('triggered', False)))
        except Exception:
            pass
        try:
            from backend.app.compliance_matrix_rule_engine.state_store import load_state as load_compliance_state
            compliance = load_compliance_state()
            decisions = compliance.get('decisions') or []
            latest = decisions[0] if decisions else {}
            snap['latest_compliance_decision_id'] = latest.get('decision_id', '')
            snap['compliance_clear'] = str(latest.get('decision', 'clear')).lower() not in {'breach', 'denied', 'blocked', 'violation'}
        except Exception:
            pass
        try:
            from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
            treasury = load_treasury_state()
            balances = treasury.get('cash_balances') or treasury.get('balances') or {}
            if isinstance(balances, dict):
                snap['treasury_total_balance'] = round(sum(v for v in balances.values() if isinstance(v, (int, float))), 2)
        except Exception:
            pass
        return snap

    def _ensure_sync(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        if not (state.get('last_sync') or {}):
            raise ValueError(f'cross-border routing context must be synced before {action}')
        return state

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snap = self._source_snapshot()
        state['last_sync'] = {
            'mission': 'QNT50036',
            'timestamp': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'snapshot': snap,
        }
        state.setdefault('sync_history', []).insert(0, state['last_sync'])
        state['sync_history'] = state['sync_history'][:100]
        state['status'] = 'synced'
        save_state(state)
        append_audit('cross_border_service_routing_context_synced', {'source': state['last_sync']['source']})
        return {'mission': 'QNT50036', 'status': 'synced', 'snapshot': snap}

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = state.setdefault('policy', {})
        for key, value in payload.items():
            if key in {'sync_after_configure'} or value is None:
                continue
            policy[key] = value
        save_state(state)
        append_audit('cross_border_service_routing_configured', {'operator': 'system'})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
            state = self._refresh()
        return {'mission': 'QNT50036', 'status': 'configured', 'policy': state.get('policy', {})}

    def register_route_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'register')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        policy = self._policy(state)
        if snap.get('risk_triggered'):
            raise ValueError('cannot register cross-border route while risk kill-switch is active')
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        src = str(payload.get('source_region') or '').strip()
        dst = str(payload.get('destination_region') or '').strip()
        srcj = str(payload.get('source_jurisdiction') or '').strip()
        dstj = str(payload.get('destination_jurisdiction') or '').strip()
        if not all([src, dst, srcj, dstj]):
            raise ValueError('source_region, destination_region, source_jurisdiction, and destination_jurisdiction are required')
        if policy.get('require_region_partition_execution', True) and not str(payload.get('partition_event_id') or snap.get('latest_partition_event_id') or '').strip():
            raise ValueError('executed regional partition evidence is required before cross-border route registration')
        if policy.get('require_compliance_clearance', False) and not bool(snap.get('compliance_clear', True)):
            raise ValueError('compliance clearance is required before cross-border route registration')
        case = {
            'route_case_id': f'route_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'source_region': src,
            'destination_region': dst,
            'source_jurisdiction': srcj,
            'destination_jurisdiction': dstj,
            'service_channels': list(payload.get('service_channels') or []),
            'route_notional': round(float(payload.get('route_notional') or 0.0), 2),
            'route_limit': round(float(payload.get('route_limit') or policy.get('default_route_notional_limit', 1000000.0)), 2),
            'partition_event_id': str(payload.get('partition_event_id') or snap.get('latest_partition_event_id') or '').strip(),
            'compliance_decision_id': str(payload.get('compliance_decision_id') or snap.get('latest_compliance_decision_id') or '').strip(),
            'boundary_policy_id': str(payload.get('boundary_policy_id') or snap.get('active_boundary_policy_id') or '').strip(),
            'execution_mode': str(payload.get('execution_mode') or 'paper').strip().lower(),
            'notes': str(payload.get('notes') or '').strip(),
            'status': 'registered',
        }
        state.setdefault('route_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('cross_border_service_routing_registered', case)
        return {'mission': 'QNT50036', 'status': 'registered', 'route_case': case}

    def approve_route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'approve')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        policy = self._policy(state)
        case_id = str(payload.get('route_case_id') or '').strip()
        case = next((x for x in (state.get('route_cases') or []) if x.get('route_case_id') == case_id), None)
        if not case:
            raise ValueError('route_case_id not found')
        mode = str(payload.get('approval_mode') or case.get('execution_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('live cross-border routing approval is blocked while safe mode is enabled')
        if snap.get('risk_triggered'):
            raise ValueError('cannot approve cross-border route while risk kill-switch is active')
        if policy.get('require_boundary_clearance', True) and not bool(payload.get('boundary_clearance', False)):
            raise ValueError('regulatory boundary clearance is required before approval')
        approved_notional = round(float(payload.get('approved_notional') or case.get('route_notional') or 0.0), 2)
        if approved_notional > round(float(case.get('route_limit') or 0.0), 2):
            raise ValueError('approved notional exceeds route limit')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_notional'] = approved_notional
        case['approval_mode'] = mode
        case['boundary_clearance'] = bool(payload.get('boundary_clearance', True))
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('cross_border_service_routing_approved', {'route_case_id': case_id, 'approval_mode': mode})
        return {'mission': 'QNT50036', 'status': 'approved', 'route_case': case}

    def execute_route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'execute')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        case_id = str(payload.get('route_case_id') or '').strip()
        case = next((x for x in (state.get('route_cases') or []) if x.get('route_case_id') == case_id), None)
        if not case:
            raise ValueError('route_case_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('cross-border route case must be approved before execution')
        mode = str(payload.get('execution_mode') or case.get('approval_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('cannot execute live cross-border routing while safe mode is enabled')
        event = {
            'routing_event_id': f'routing_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'route_case_id': case_id,
            'source_region': case.get('source_region'),
            'destination_region': case.get('destination_region'),
            'execution_mode': mode,
            'routed_channel_count': int(payload.get('routed_channel_count') or len(case.get('service_channels') or [])),
            'route_registry': str(payload.get('route_registry') or 'cross_border_service_registry').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_routing_event_id'] = event['routing_event_id']
        state.setdefault('routing_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('cross_border_service_routing_executed', event)
        return {'mission': 'QNT50036', 'status': 'executed', 'routing_event': event, 'route_case': case}

    def close_route_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'close')
        case_id = str(payload.get('route_case_id') or '').strip()
        case = next((x for x in (state.get('route_cases') or []) if x.get('route_case_id') == case_id), None)
        if not case:
            raise ValueError('route_case_id not found')
        if str(case.get('status') or '').lower() not in {'approved', 'executed'}:
            raise ValueError('cross-border route case must be approved or executed before closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('cross_border_service_routing_closed', {'route_case_id': case_id, 'closed_by': case.get('closed_by')})
        return {'mission': 'QNT50036', 'status': 'closed', 'route_case': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        save_state(default_state())
        append_audit('cross_border_service_routing_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50036', 'status': 'reset'}

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        return {
            'mission': 'QNT50036',
            'posture': state.get('status', 'degraded'),
            'safe_mode': bool(snap.get('safe_mode', True)),
            'risk_triggered': bool(snap.get('risk_triggered', False)),
            'latest_partition_event_id': snap.get('latest_partition_event_id'),
            'compliance_clear': bool(snap.get('compliance_clear', True)),
            'route_case_count': len(state.get('route_cases') or []),
            'routing_event_count': len(state.get('routing_events') or []),
        }
