from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.autonomous_control_loop.state_store import load_state as load_control_state
from backend.app.executive_capital_committee.state_store import load_state as load_committee_state
from backend.app.executive_scenario_arbitration.state_store import load_state as load_arbitration_state
from backend.app.intercompany_ledger.state_store import load_state as load_intercompany_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state

from backend.app.institutional_allocation_execution_charter.state_store import append_audit, default_state, load_state, save_state


class InstitutionalAllocationExecutionCharterEngine:
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
        state['execution_charters'] = (state.get('execution_charters') or [])[: int(policy.get('max_charters_to_keep', 300))]
        state['mandates'] = (state.get('mandates') or [])[: int(policy.get('max_mandates_to_keep', 300))]
        state['enforcement_directives'] = (state.get('enforcement_directives') or [])[: int(policy.get('max_directives_to_keep', 500))]

    def _source_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        arbitration = load_arbitration_state()
        committee = load_committee_state()
        risk = load_risk_state()
        treasury = load_treasury_state()
        control = load_control_state()
        intercompany = load_intercompany_state()
        latest_decision = (arbitration.get('arbitration_decisions') or [{}])[0]
        latest_committee_decision = (committee.get('committee_decisions') or [{}])[0]
        treasury_sync = treasury.get('last_sync') or {}
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'arbitration_posture': str(arbitration.get('status') or 'degraded'),
            'arbitration_decision_count': len(arbitration.get('arbitration_decisions') or []),
            'latest_arbitration_decision_id': str(latest_decision.get('decision_id') or ''),
            'latest_arbitration_status': str(latest_decision.get('decision_status') or ''),
            'committee_posture': str(committee.get('status') or 'degraded'),
            'committee_decision_count': len(committee.get('committee_decisions') or []),
            'latest_committee_decision_id': str(latest_committee_decision.get('decision_id') or ''),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'available_to_move': self._round(treasury_sync.get('available_to_move') or 0.0, 2),
            'cash_balance': self._round(treasury_sync.get('cash_balance') or 0.0, 2),
            'settlement_status': str(treasury_sync.get('settlement_status') or ''),
            'control_loop_posture': str(control.get('status') or 'degraded'),
            'open_intercompany_flow_count': len([x for x in intercompany.get('flow_cases') or [] if x.get('status') not in {'settled', 'rejected'}]),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('institutional_charter_context_synced', snapshot)
        return {'mission': 'QNT50025', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        posture = 'ready'
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif not (state.get('execution_charters') or state.get('mandates') or state.get('enforcement_directives')):
            posture = 'degraded'
        elif any(x.get('directive_status') in {'blocked', 'rejected'} for x in (state.get('enforcement_directives') or [])):
            posture = 'guarded'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50025',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'charter_count': len(state.get('execution_charters') or []),
            'mandate_count': len(state.get('mandates') or []),
            'directive_count': len(state.get('enforcement_directives') or []),
            'latest_directive': (state.get('enforcement_directives') or [{}])[0],
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
        append_audit('institutional_charter_configuration_updated', {'policy': policy})
        result = {'mission': 'QNT50025', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def register_charter(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        charter = {
            'charter_id': f'charter_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'charter_scope': str(payload.get('charter_scope') or 'INSTITUTIONAL_EXECUTION_CHARTER').strip(),
            'summary': str(payload.get('summary') or '').strip(),
            'target_strategy': str(payload.get('target_strategy') or '').strip(),
            'allowed_actions': list(payload.get('allowed_actions') or []),
            'blocked_actions': list(payload.get('blocked_actions') or []),
            'max_notional': self._round(payload.get('max_notional'), 2),
            'max_capital_delta_pct': self._round(payload.get('max_capital_delta_pct'), 6),
            'jurisdiction': str(payload.get('jurisdiction') or '').strip(),
            'entity_scope': str(payload.get('entity_scope') or '').strip(),
            'active': bool(payload.get('active', True)),
            'tags': list(payload.get('tags') or []),
        }
        if not charter['operator'] or not charter['title']:
            raise ValueError('operator and title are required')
        state.setdefault('execution_charters', []).insert(0, charter)
        self._trim(state)
        save_state(state)
        append_audit('institutional_execution_charter_registered', charter)
        return {'mission': 'QNT50025', 'status': 'registered', 'charter': charter}

    def register_mandate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        charter_id = str(payload.get('charter_id') or '').strip()
        if not charter_id:
            raise ValueError('charter_id is required')
        charter = next((x for x in (state.get('execution_charters') or []) if x.get('charter_id') == charter_id), None)
        if not charter:
            raise ValueError('charter_id not found')
        mandate = {
            'mandate_id': f'mandate_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'charter_id': charter_id,
            'title': str(payload.get('title') or '').strip(),
            'summary': str(payload.get('summary') or '').strip(),
            'target_strategy': str(payload.get('target_strategy') or charter.get('target_strategy') or '').strip(),
            'allowed_actions': list(payload.get('allowed_actions') or charter.get('allowed_actions') or []),
            'blocked_actions': list(payload.get('blocked_actions') or charter.get('blocked_actions') or []),
            'minimum_mandate_alignment_score': self._round(payload.get('minimum_mandate_alignment_score') or state.get('policy', {}).get('minimum_mandate_alignment_score') or 82.0, 4),
            'max_notional': self._round(payload.get('max_notional') if payload.get('max_notional') is not None else charter.get('max_notional'), 2),
            'max_capital_delta_pct': self._round(payload.get('max_capital_delta_pct') if payload.get('max_capital_delta_pct') is not None else charter.get('max_capital_delta_pct'), 6),
            'require_explicit_committee_memory': bool(payload.get('require_explicit_committee_memory', False)),
            'active': bool(payload.get('active', True)),
            'tags': list(payload.get('tags') or []),
        }
        if not mandate['operator'] or not mandate['title']:
            raise ValueError('operator and title are required')
        state.setdefault('mandates', []).insert(0, mandate)
        self._trim(state)
        save_state(state)
        append_audit('institutional_mandate_registered', mandate)
        return {'mission': 'QNT50025', 'status': 'registered', 'mandate': mandate}

    def enforce_mandate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        policy = self._policy(state)
        if not policy.get('enabled', True):
            raise ValueError('mission is disabled')
        decision_id = str(payload.get('decision_id') or '').strip()
        mandate_id = str(payload.get('mandate_id') or '').strip()
        if not decision_id:
            raise ValueError('decision_id is required')
        if not mandate_id:
            raise ValueError('mandate_id is required')
        decision = next((x for x in load_arbitration_state().get('arbitration_decisions') or [] if x.get('decision_id') == decision_id), None)
        if not decision:
            raise ValueError('decision_id not found')
        mandate = next((x for x in (state.get('mandates') or []) if x.get('mandate_id') == mandate_id), None)
        if not mandate:
            raise ValueError('mandate_id not found')
        charter = next((x for x in (state.get('execution_charters') or []) if x.get('charter_id') == mandate.get('charter_id')), None)
        action = str(payload.get('execution_action') or decision.get('requested_action') or '').strip()
        target_strategy = str(payload.get('target_strategy') or decision.get('target_strategy') or mandate.get('target_strategy') or '').strip()
        proposed_notional = self._round(payload.get('proposed_notional') if payload.get('proposed_notional') is not None else decision.get('proposed_notional'), 2)
        capital_delta_pct = self._round(payload.get('capital_delta_pct') if payload.get('capital_delta_pct') is not None else decision.get('capital_delta_pct'), 6)
        alignment_score = self._round(payload.get('mandate_alignment_score') or decision.get('policy_alignment_score') or 0.0, 4)

        status = 'issued'
        reasons = []
        snapshot = state.get('last_sync') or {}
        if policy.get('require_arbitration_context', True) and decision.get('decision_status') not in {'approved', 'guarded'}:
            status = 'blocked'
            reasons.append('arbitration decision not approved for mandate enforcement')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            status = 'blocked'
            reasons.append('risk kill-switch active')
        if policy.get('require_liquidity_support', True) and proposed_notional > float(snapshot.get('available_to_move') or 0.0):
            status = 'blocked'
            reasons.append('insufficient available liquidity')
        if policy.get('require_committee_alignment', True) and not snapshot.get('latest_committee_decision_id'):
            status = 'blocked'
            reasons.append('committee context missing')
        if target_strategy and mandate.get('target_strategy') and target_strategy != mandate.get('target_strategy'):
            status = 'blocked'
            reasons.append('target strategy outside mandate scope')
        if action in set(mandate.get('blocked_actions') or []):
            status = 'blocked'
            reasons.append('action blocked by mandate')
        allowed_actions = set(mandate.get('allowed_actions') or [])
        if allowed_actions and action not in allowed_actions:
            status = 'blocked'
            reasons.append('action not allowed by mandate')
        if proposed_notional > float(mandate.get('max_notional') or 0.0):
            status = 'blocked'
            reasons.append('proposed notional exceeds mandate limit')
        if abs(capital_delta_pct) > abs(float(mandate.get('max_capital_delta_pct') or 0.0)):
            status = 'blocked'
            reasons.append('capital delta exceeds mandate limit')
        if alignment_score < float(mandate.get('minimum_mandate_alignment_score') or policy.get('minimum_mandate_alignment_score') or 0.0):
            status = 'blocked'
            reasons.append('mandate alignment score below threshold')

        directive = {
            'directive_id': f'directive_{uuid.uuid4().hex[:12]}',
            'issued_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'decision_id': decision_id,
            'mandate_id': mandate_id,
            'charter_id': str((charter or {}).get('charter_id') or ''),
            'execution_action': action,
            'target_strategy': target_strategy,
            'proposed_notional': proposed_notional,
            'capital_delta_pct': capital_delta_pct,
            'mandate_alignment_score': alignment_score,
            'directive_status': status,
            'instruction': str(payload.get('instruction') or '').strip(),
            'reasons': reasons,
        }
        state.setdefault('enforcement_directives', []).insert(0, directive)
        self._trim(state)
        save_state(state)
        append_audit('institutional_mandate_enforced', directive)
        return {'mission': 'QNT50025', 'status': status, 'directive': directive}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        reason = str(payload.get('reason') or 'manual reset')
        current = self._refresh()
        default = default_state()
        default['audit_log'] = [{
            'event_id': f'institutional_allocation_execution_charter_audit_{time.time_ns()}',
            'event_type': 'institutional_charter_reset',
            'timestamp': int(time.time()),
            'reason': reason,
            'operator': str(payload.get('operator') or '').strip(),
            'prior_charter_count': len(current.get('execution_charters') or []),
            'prior_mandate_count': len(current.get('mandates') or []),
            'prior_directive_count': len(current.get('enforcement_directives') or []),
        }]
        save_state(default)
        return {'mission': 'QNT50025', 'status': 'reset', 'reason': reason, 'summary': self.summary()}
