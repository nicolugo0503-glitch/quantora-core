from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.autonomous_control_loop.state_store import load_state as load_control_loop_state
from backend.app.executive_capital_committee.state_store import load_state as load_committee_state
from backend.app.executive_scenario_arbitration.state_store import append_audit, load_state, save_state
from backend.app.intercompany_ledger.state_store import load_state as load_intercompany_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class ExecutiveScenarioArbitrationEngine:
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

    def _source_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        committee = load_committee_state()
        risk = load_risk_state()
        perf = load_performance_state()
        treasury = load_treasury_state()
        deployment = load_deployment_state()
        control = load_control_loop_state()
        intercompany = load_intercompany_state()
        metrics = perf.get('metrics') or {}
        investor_metrics = perf.get('investor_metrics') or {}
        treasury_sync = treasury.get('last_sync') or {}
        latest_decision = (committee.get('committee_decisions') or [{}])[0]
        latest_plan = (control.get('control_plans') or [{}])[0]
        open_flows = [x for x in intercompany.get('flow_cases') or [] if x.get('status') not in {'settled', 'rejected'}]
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'committee_posture': str(committee.get('status') or 'degraded'),
            'committee_decision_count': len(committee.get('committee_decisions') or []),
            'latest_committee_decision_id': str(latest_decision.get('decision_id') or ''),
            'latest_committee_outcome': str(latest_decision.get('decision_status') or latest_decision.get('outcome') or ''),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'safe_mode': bool(deployment.get('safe_mode', True)),
            'execution_mode': str(deployment.get('execution_mode') or 'paper'),
            'current_regime': str((deployment.get('current_plan') or {}).get('regime') or deployment.get('current_regime') or 'neutral'),
            'cumulative_return_pct': self._round(metrics.get('cumulative_return_pct'), 6),
            'sharpe_ratio': self._round(metrics.get('sharpe_ratio'), 4),
            'max_drawdown_pct': self._round(metrics.get('max_drawdown_pct'), 6),
            'latest_equity': self._round(investor_metrics.get('latest_equity') or 0.0, 2),
            'available_to_move': self._round(treasury_sync.get('available_to_move') or 0.0, 2),
            'cash_balance': self._round(treasury_sync.get('cash_balance') or 0.0, 2),
            'settlement_status': str(treasury_sync.get('settlement_status') or ''),
            'control_loop_posture': str(control.get('status') or 'degraded'),
            'latest_control_plan_id': str(latest_plan.get('plan_id') or ''),
            'open_intercompany_flow_count': len(open_flows),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('executive_scenario_context_synced', snapshot)
        return {'mission': 'QNT50024', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['allocation_policies'] = (state.get('allocation_policies') or [])[: int(policy.get('max_scenarios_to_keep', 300))]
        state['scenario_cases'] = (state.get('scenario_cases') or [])[: int(policy.get('max_scenarios_to_keep', 300))]
        state['arbitration_decisions'] = (state.get('arbitration_decisions') or [])[: int(policy.get('max_decisions_to_keep', 300))]

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        posture = 'ready'
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif not (state.get('allocation_policies') or state.get('scenario_cases') or state.get('arbitration_decisions')):
            posture = 'degraded'
        elif any(x.get('decision_status') in {'blocked', 'rejected', 'deferred'} for x in (state.get('arbitration_decisions') or [])):
            posture = 'guarded'
        state['status'] = posture
        save_state(state)
        latest_decision = (state.get('arbitration_decisions') or [{}])[0]
        return {
            'mission': 'QNT50024',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'policy_count': len(state.get('allocation_policies') or []),
            'scenario_count': len(state.get('scenario_cases') or []),
            'decision_count': len(state.get('arbitration_decisions') or []),
            'latest_decision': latest_decision,
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
        append_audit('executive_scenario_configuration_updated', {'policy': policy})
        result = {'mission': 'QNT50024', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def register_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        policy_record = {
            'policy_id': f'policy_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'policy_scope': str(payload.get('policy_scope') or 'CAPITAL_ALLOCATION_POLICY').strip(),
            'summary': str(payload.get('summary') or '').strip(),
            'target_strategy': str(payload.get('target_strategy') or '').strip(),
            'allowed_actions': list(payload.get('allowed_actions') or []),
            'blocked_actions': list(payload.get('blocked_actions') or []),
            'max_capital_delta_pct': self._round(payload.get('max_capital_delta_pct'), 6),
            'max_notional': self._round(payload.get('max_notional'), 2),
            'minimum_policy_alignment_score': self._round(payload.get('minimum_policy_alignment_score') or state['policy'].get('minimum_policy_alignment_score'), 2),
            'minimum_scenario_resilience_score': self._round(payload.get('minimum_scenario_resilience_score') or state['policy'].get('minimum_scenario_resilience_score'), 2),
            'jurisdiction': str(payload.get('jurisdiction') or '').strip(),
            'entity_scope': str(payload.get('entity_scope') or '').strip(),
            'active': bool(payload.get('active', True)),
            'tags': list(payload.get('tags') or []),
        }
        if not policy_record['operator']:
            raise ValueError('operator is required')
        if not policy_record['title']:
            raise ValueError('title is required')
        state.setdefault('allocation_policies', []).insert(0, policy_record)
        self._trim(state)
        save_state(state)
        append_audit('allocation_policy_registered', policy_record)
        return {'mission': 'QNT50024', 'status': 'registered', 'policy': policy_record}

    def _active_policies(self, state: Dict[str, Any], target_strategy: str = '') -> List[Dict[str, Any]]:
        policies = [x for x in (state.get('allocation_policies') or []) if x.get('active', True)]
        if target_strategy:
            scoped = [x for x in policies if not x.get('target_strategy') or x.get('target_strategy') == target_strategy]
            if scoped:
                return scoped
        return policies

    def arbitrate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        title = str(payload.get('title') or '').strip()
        requested_action = str(payload.get('requested_action') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not title:
            raise ValueError('title is required')
        if not requested_action:
            raise ValueError('requested_action is required')

        proposed_notional = self._round(payload.get('proposed_notional'), 2)
        capital_delta_pct = self._round(payload.get('capital_delta_pct'), 6)
        policy_alignment_score = self._round(payload.get('policy_alignment_score'), 2)
        scenario_resilience_score = self._round(payload.get('scenario_resilience_score'), 2)
        downside_risk_score = self._round(payload.get('downside_risk_score'), 2)
        liquidity_coverage_score = self._round(payload.get('liquidity_coverage_score'), 2)
        safe_mode_override_requested = bool(payload.get('safe_mode_override_requested', False))
        target_strategy = str(payload.get('target_strategy') or '').strip()

        active_policies = self._active_policies(state, target_strategy)
        applicable = active_policies[0] if active_policies else None
        if applicable:
            min_policy_alignment = max(policy.get('minimum_policy_alignment_score', 85.0), applicable.get('minimum_policy_alignment_score', 85.0))
            min_scenario_resilience = max(policy.get('minimum_scenario_resilience_score', 78.0), applicable.get('minimum_scenario_resilience_score', 78.0))
            max_capital_delta_pct = min(abs(float(policy.get('max_capital_delta_pct', 0.12))), abs(float(applicable.get('max_capital_delta_pct', 0.12))))
            max_notional = min(float(policy.get('max_live_notional_without_override', 250000.0)), float(applicable.get('max_notional') or policy.get('max_live_notional_without_override', 250000.0)))
        else:
            min_policy_alignment = float(policy.get('minimum_policy_alignment_score', 85.0))
            min_scenario_resilience = float(policy.get('minimum_scenario_resilience_score', 78.0))
            max_capital_delta_pct = abs(float(policy.get('max_capital_delta_pct', 0.12)))
            max_notional = float(policy.get('max_live_notional_without_override', 250000.0))

        reasons: List[str] = []
        decision_status = 'approved'
        requires_override = False

        if snapshot.get('risk_triggered') and policy.get('require_risk_clearance', True):
            decision_status = 'blocked'
            reasons.append('risk kill-switch is active')
        if snapshot.get('committee_posture') not in {'ready', 'guarded'} and policy.get('require_committee_context', True):
            decision_status = 'blocked'
            reasons.append('committee context is not ready')
        if proposed_notional > float(snapshot.get('available_to_move') or 0.0) and policy.get('minimum_available_liquidity', 0.0) > 0:
            decision_status = 'blocked'
            reasons.append('insufficient available liquidity for proposed notional')
        if float(snapshot.get('available_to_move') or 0.0) < float(policy.get('minimum_available_liquidity', 0.0)):
            decision_status = 'blocked'
            reasons.append('available liquidity below governance floor')
        if policy_alignment_score < min_policy_alignment and policy.get('require_policy_alignment', True):
            decision_status = 'rejected'
            reasons.append('policy alignment score below minimum threshold')
        if scenario_resilience_score < min_scenario_resilience:
            decision_status = 'rejected'
            reasons.append('scenario resilience score below minimum threshold')
        if abs(capital_delta_pct) > max_capital_delta_pct:
            decision_status = 'deferred'
            reasons.append('capital delta exceeds allowed policy range')
            requires_override = True
        if proposed_notional > max_notional:
            decision_status = 'deferred'
            reasons.append('notional exceeds live threshold without override')
            requires_override = True
        if requested_action in set(applicable.get('blocked_actions') or []) if applicable else set():
            decision_status = 'blocked'
            reasons.append('requested action is blocked by active policy')
        if applicable and applicable.get('allowed_actions') and requested_action not in set(applicable.get('allowed_actions') or []):
            decision_status = 'rejected'
            reasons.append('requested action is outside allowed policy actions')
        if snapshot.get('safe_mode') and snapshot.get('execution_mode') == 'live' and safe_mode_override_requested and policy.get('require_safe_mode_for_live_override', True):
            decision_status = 'blocked'
            reasons.append('safe mode prevents live override request')
        if downside_risk_score > 70.0 and decision_status == 'approved':
            decision_status = 'guarded'
            reasons.append('downside risk requires guarded approval')
        if liquidity_coverage_score < 70.0 and decision_status == 'approved':
            decision_status = 'guarded'
            reasons.append('liquidity coverage requires guarded approval')
        if not reasons and decision_status == 'approved':
            reasons.append('scenario arbitration passed all thresholds')

        scenario_case = {
            'scenario_id': f'scenario_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'title': title,
            'scenario_scope': str(payload.get('scenario_scope') or 'EXECUTIVE_SCENARIO_ARBITRATION'),
            'summary': str(payload.get('summary') or ''),
            'requested_action': requested_action,
            'target_strategy': target_strategy,
            'proposed_notional': proposed_notional,
            'capital_delta_pct': capital_delta_pct,
            'policy_alignment_score': policy_alignment_score,
            'scenario_resilience_score': scenario_resilience_score,
            'downside_risk_score': downside_risk_score,
            'liquidity_coverage_score': liquidity_coverage_score,
            'safe_mode_override_requested': safe_mode_override_requested,
            'tags': list(payload.get('tags') or []),
            'committee_decision_id': str(payload.get('committee_decision_id') or snapshot.get('latest_committee_decision_id') or ''),
            'policy_id': str((applicable or {}).get('policy_id') or ''),
        }
        decision = {
            'decision_id': f'arbitration_{uuid.uuid4().hex[:12]}',
            'timestamp': int(time.time()),
            'operator': operator,
            'scenario_id': scenario_case['scenario_id'],
            'decision_status': decision_status,
            'requires_override': requires_override,
            'rationale': str(payload.get('rationale') or ''),
            'reasons': reasons,
            'policy_id': scenario_case['policy_id'],
            'committee_decision_id': scenario_case['committee_decision_id'],
            'posture_snapshot': snapshot,
        }
        state.setdefault('scenario_cases', []).insert(0, scenario_case)
        state.setdefault('arbitration_decisions', []).insert(0, decision)
        self._trim(state)
        save_state(state)
        append_audit('executive_scenario_arbitrated', {
            'scenario_id': scenario_case['scenario_id'],
            'decision_id': decision['decision_id'],
            'decision_status': decision_status,
            'policy_id': scenario_case['policy_id'],
        })
        return {
            'mission': 'QNT50024',
            'status': decision_status,
            'scenario': scenario_case,
            'decision': decision,
        }

    def enforce_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        decision_id = str(payload.get('decision_id') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not decision_id:
            raise ValueError('decision_id is required')
        decision = next((x for x in (state.get('arbitration_decisions') or []) if x.get('decision_id') == decision_id), None)
        if not decision:
            raise ValueError('decision_id not found')
        action = str(payload.get('enforcement_action') or 'issue_directive').strip()
        directive = {
            'directive_id': f'directive_{uuid.uuid4().hex[:12]}',
            'issued_at': int(time.time()),
            'operator': operator,
            'decision_id': decision_id,
            'enforcement_action': action,
            'directive_status': 'issued' if decision.get('decision_status') in {'approved', 'guarded'} else 'blocked',
            'instruction': str(payload.get('instruction') or ''),
        }
        decision['enforcement'] = directive
        save_state(state)
        append_audit('allocation_policy_enforced', directive)
        return {
            'mission': 'QNT50024',
            'status': directive['directive_status'],
            'directive': directive,
            'decision': decision,
        }

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = self._refresh()
        state = default = load_state()
        from backend.app.executive_scenario_arbitration.state_store import default_state
        state = default_state()
        state['audit_log'] = [
            {
                'event_id': f'executive_scenario_arbitration_audit_{time.time_ns()}',
                'event_type': 'executive_scenario_reset',
                'timestamp': int(time.time()),
                'operator': operator,
                'reason': str(payload.get('reason') or 'manual reset'),
                'prior_policy_count': len(current.get('allocation_policies') or []),
                'prior_scenario_count': len(current.get('scenario_cases') or []),
                'prior_decision_count': len(current.get('arbitration_decisions') or []),
            }
        ]
        save_state(state)
        return {'mission': 'QNT50024', 'status': 'reset', 'state': self.summary()}
