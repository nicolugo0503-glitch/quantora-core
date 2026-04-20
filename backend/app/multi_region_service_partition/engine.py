from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.multi_region_service_partition.state_store import append_audit, default_state, load_state, save_state


class MultiRegionServicePartitionEngine:
    def __init__(self) -> None:
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict((state or {}).get('policy') or {})

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['expansion_cases'] = (state.get('expansion_cases') or [])[: int(policy.get('max_expansion_cases', 250))]
        state['partition_events'] = (state.get('partition_events') or [])[: int(policy.get('max_partition_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            'synced_at': int(time.time()),
            'safe_mode': True,
            'risk_triggered': False,
            'execution_mode': 'paper',
            'latest_service_model_id': '',
            'latest_service_event_id': '',
            'latest_service_status': '',
            'treasury_total_balance': 0.0,
            'compliance_clear': True,
            'active_directive_id': '',
        }
        try:
            from backend.app.multi_vehicle_shared_services.state_store import load_state as load_shared_state
            shared = load_shared_state()
            models = shared.get('service_models') or []
            events = shared.get('service_events') or []
            latest_model = models[0] if models else {}
            latest_event = events[0] if events else {}
            snapshot['latest_service_model_id'] = str(latest_model.get('service_model_id') or '')
            snapshot['latest_service_status'] = str(latest_model.get('status') or '')
            snapshot['latest_service_event_id'] = str(latest_event.get('service_event_id') or '')
        except Exception:
            pass
        try:
            from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
            treasury = load_treasury_state()
            balances = treasury.get('balances') or treasury.get('cash_balances') or {}
            if isinstance(balances, dict):
                snapshot['treasury_total_balance'] = round(sum(v for v in balances.values() if isinstance(v, (int, float))), 2)
            summary = treasury.get('summary') or {}
            snapshot['safe_mode'] = bool(summary.get('safe_mode', snapshot['safe_mode']))
            snapshot['execution_mode'] = str(summary.get('execution_mode') or snapshot['execution_mode'])
        except Exception:
            pass
        try:
            from backend.app.risk_control.state_store import load_state as load_risk_state
            risk = load_risk_state()
            summary = risk.get('summary') or risk.get('last_summary') or {}
            snapshot['risk_triggered'] = bool(summary.get('kill_switch_triggered') or summary.get('triggered') or risk.get('kill_switch_triggered') or False)
        except Exception:
            pass
        try:
            from backend.app.institutional_allocation_execution_charter.state_store import load_state as load_charter_state
            charter = load_charter_state()
            directives = charter.get('directives') or []
            active = next((d for d in directives if str(d.get('status') or '').lower() in {'active', 'approved', 'executed'}), {})
            snapshot['active_directive_id'] = str(active.get('directive_id') or '')
        except Exception:
            pass
        try:
            from backend.app.compliance_matrix_rule_engine.state_store import load_state as load_compliance_state
            compliance = load_compliance_state()
            decisions = compliance.get('decisions') or []
            latest = decisions[0] if decisions else {}
            status = str(latest.get('status') or latest.get('decision') or 'clear').lower()
            snapshot['compliance_clear'] = status not in {'blocked', 'violation', 'breach', 'denied'}
        except Exception:
            pass
        return snapshot

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snap = self._source_snapshot()
        state['last_sync'] = {
            'mission': 'QNT50035',
            'timestamp': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'snapshot': snap,
        }
        state.setdefault('sync_history', []).insert(0, state['last_sync'])
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('multi_region_service_partition_context_synced', {'source': state['last_sync']['source'], 'snapshot': snap})
        return {'mission': 'QNT50035', 'status': 'synced', 'snapshot': snap}

    def _ensure_sync(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        policy = self._policy(state)
        if not state.get('last_sync') and policy.get('auto_sync_sources', True):
            self.sync_context({'source': action})
            return self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = state.setdefault('policy', {})
        for k, v in payload.items():
            if k in {'sync_after_configure'}:
                continue
            if v is not None:
                policy[k] = v
        save_state(state)
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        append_audit('multi_region_service_partition_configured', {'policy': policy})
        return {'mission': 'QNT50035', 'status': 'configured', 'policy': policy}

    def register_expansion_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'register')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        policy = self._policy(state)
        if policy.get('require_shared_services_execution', True) and not (payload.get('service_event_id') or snap.get('latest_service_event_id')):
            raise ValueError('executed QNT50034 shared-services evidence is required before regional expansion registration')
        if policy.get('require_compliance_clearance', False) and not snap.get('compliance_clear', True):
            raise ValueError('compliance clearance is required before regional expansion registration')
        if snap.get('risk_triggered'):
            raise ValueError('cannot register regional expansion while risk kill-switch is active')
        operator = str(payload.get('operator') or '').strip()
        region_name = str(payload.get('region_name') or '').strip()
        if not operator or not region_name:
            raise ValueError('operator and region_name are required')
        jurisdictions = list(payload.get('jurisdictions') or [])
        service_partitions = list(payload.get('service_partitions') or [])
        budget = round(float(payload.get('regional_budget') or 0.0), 2)
        case = {
            'expansion_case_id': f'expansion_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'region_name': region_name,
            'operating_model': str(payload.get('operating_model') or 'regional-hub').strip(),
            'jurisdictions': jurisdictions,
            'service_partitions': service_partitions,
            'regional_budget': budget,
            'budget_limit': round(float(payload.get('budget_limit') or policy.get('default_region_budget_limit', 1000000.0)), 2),
            'service_event_id': str(payload.get('service_event_id') or snap.get('latest_service_event_id') or '').strip(),
            'directive_id': str(payload.get('directive_id') or snap.get('active_directive_id') or '').strip(),
            'operating_mode': str(payload.get('operating_mode') or 'paper').strip().lower(),
            'notes': str(payload.get('notes') or '').strip(),
            'status': 'registered',
        }
        state.setdefault('expansion_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('multi_region_service_partition_registered', case)
        return {'mission': 'QNT50035', 'status': 'registered', 'expansion_case': case}

    def approve_partition(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'approve')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        case_id = str(payload.get('expansion_case_id') or '').strip()
        case = next((x for x in (state.get('expansion_cases') or []) if x.get('expansion_case_id') == case_id), None)
        if not case:
            raise ValueError('expansion_case_id not found')
        mode = str(payload.get('approval_mode') or case.get('operating_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('live regional partition approval is blocked while safe mode is enabled')
        if snap.get('risk_triggered'):
            raise ValueError('cannot approve regional partition while risk kill-switch is active')
        approved_budget = round(float(payload.get('approved_budget') or case.get('regional_budget') or 0.0), 2)
        if approved_budget > round(float(case.get('budget_limit') or 0.0), 2):
            raise ValueError('approved budget exceeds regional budget limit')
        if self._policy(state).get('require_treasury_capacity', True) and approved_budget > round(float(snap.get('treasury_total_balance') or 0.0), 2):
            raise ValueError('insufficient treasury capacity for regional partition approval')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approval_mode'] = mode
        case['approved_budget'] = approved_budget
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('multi_region_service_partition_approved', {'expansion_case_id': case_id, 'approval_mode': mode})
        return {'mission': 'QNT50035', 'status': 'approved', 'expansion_case': case}

    def execute_partition(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'execute')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        case_id = str(payload.get('expansion_case_id') or '').strip()
        case = next((x for x in (state.get('expansion_cases') or []) if x.get('expansion_case_id') == case_id), None)
        if not case:
            raise ValueError('expansion_case_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('regional expansion case must be approved before execution')
        mode = str(payload.get('execution_mode') or case.get('approval_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('cannot execute live regional partition while safe mode is enabled')
        partition_event = {
            'partition_event_id': f'partition_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'expansion_case_id': case_id,
            'region_name': case.get('region_name'),
            'execution_mode': mode,
            'jurisdiction_count': int(payload.get('jurisdiction_count') or len(case.get('jurisdictions') or [])),
            'partition_registry': str(payload.get('partition_registry') or 'regional_service_registry').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = partition_event['executed_at']
        case['last_partition_event_id'] = partition_event['partition_event_id']
        state.setdefault('partition_events', []).insert(0, partition_event)
        self._trim(state)
        save_state(state)
        append_audit('multi_region_service_partition_executed', partition_event)
        return {'mission': 'QNT50035', 'status': 'executed', 'partition_event': partition_event, 'expansion_case': case}

    def close_expansion_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'close')
        case_id = str(payload.get('expansion_case_id') or '').strip()
        case = next((x for x in (state.get('expansion_cases') or []) if x.get('expansion_case_id') == case_id), None)
        if not case:
            raise ValueError('expansion_case_id not found')
        if str(case.get('status') or '').lower() not in {'approved', 'executed'}:
            raise ValueError('regional expansion case must be approved or executed before closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('multi_region_service_partition_closed', {'expansion_case_id': case_id, 'closed_by': case.get('closed_by')})
        return {'mission': 'QNT50035', 'status': 'closed', 'expansion_case': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        save_state(default_state())
        append_audit('multi_region_service_partition_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50035', 'status': 'reset'}

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        return {
            'mission': 'QNT50035',
            'posture': state.get('status', 'degraded'),
            'safe_mode': bool(snap.get('safe_mode', True)),
            'risk_triggered': bool(snap.get('risk_triggered', False)),
            'latest_service_event_id': snap.get('latest_service_event_id'),
            'compliance_clear': bool(snap.get('compliance_clear', True)),
            'expansion_case_count': len(state.get('expansion_cases') or []),
            'partition_event_count': len(state.get('partition_events') or []),
        }
