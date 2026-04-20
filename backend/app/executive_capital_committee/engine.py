from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.autonomous_control_loop.state_store import load_state as load_control_loop_state
from backend.app.executive_capital_committee.state_store import append_audit, load_state, save_state
from backend.app.intercompany_ledger.state_store import load_state as load_intercompany_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class ExecutiveCapitalCommitteeEngine:
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
        risk = load_risk_state()
        perf = load_performance_state()
        treasury = load_treasury_state()
        deployment = load_deployment_state()
        control = load_control_loop_state()
        intercompany = load_intercompany_state()
        metrics = perf.get('metrics') or {}
        investor_metrics = perf.get('investor_metrics') or {}
        treasury_sync = treasury.get('last_sync') or {}
        latest_plan = (control.get('control_plans') or [{}])[0]
        latest_cycle = (control.get('control_cycles') or [{}])[0]
        latest_release = (deployment.get('release_queue') or [{}])[0]
        open_intercompany = [x for x in intercompany.get('flow_cases') or [] if x.get('status') not in {'settled', 'rejected'}]
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
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
            'control_plan_count': len(control.get('control_plans') or []),
            'control_cycle_count': len(control.get('control_cycles') or []),
            'latest_control_plan_id': str(latest_plan.get('plan_id') or ''),
            'latest_control_cycle_id': str(latest_cycle.get('cycle_id') or ''),
            'release_queue_count': len(deployment.get('release_queue') or []),
            'latest_release_id': str(latest_release.get('deployment_id') or latest_release.get('release_id') or ''),
            'open_intercompany_flow_count': len(open_intercompany),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        snapshot = self._source_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('executive_committee_context_synced', snapshot)
        return {'mission': 'QNT50023', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def _memory_similarity(self, query_tokens: set[str], memory: Dict[str, Any]) -> float:
        text = ' '.join([
            str(memory.get('title') or ''),
            str(memory.get('decision_scope') or ''),
            str(memory.get('summary') or ''),
            str(memory.get('outcome_summary') or ''),
            ' '.join(str(x) for x in (memory.get('tags') or [])),
        ]).lower()
        mem_tokens = {tok for tok in ''.join(ch if ch.isalnum() else ' ' for ch in text).split() if len(tok) > 2}
        if not query_tokens or not mem_tokens:
            return 0.0
        return round(100.0 * len(query_tokens & mem_tokens) / max(len(query_tokens | mem_tokens), 1), 2)

    def _recall_memories(self, payload: Dict[str, Any], memories: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        query = ' '.join([
            str(payload.get('title') or ''),
            str(payload.get('decision_scope') or ''),
            str(payload.get('summary') or ''),
            ' '.join(str(x) for x in (payload.get('tags') or [])),
        ]).lower()
        query_tokens = {tok for tok in ''.join(ch if ch.isalnum() else ' ' for ch in query).split() if len(tok) > 2}
        scored: List[tuple[float, Dict[str, Any]]] = []
        for item in memories or []:
            score = self._memory_similarity(query_tokens, item)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, item in scored[:limit]:
            out.append({
                'match_score': score,
                'memory_id': item.get('memory_id'),
                'title': item.get('title'),
                'decision_scope': item.get('decision_scope'),
                'memory_confidence_score': item.get('memory_confidence_score'),
                'outcome_quality_score': item.get('outcome_quality_score'),
                'created_at': item.get('created_at'),
            })
        return out

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        posture = 'ready'
        if snapshot.get('risk_triggered'):
            posture = 'blocked'
        elif not (state.get('committee_decisions') or state.get('committee_proposals') or state.get('decision_memories')):
            posture = 'degraded'
        elif any(x.get('status') == 'blocked' for x in state.get('committee_decisions') or []):
            posture = 'guarded'
        state['status'] = posture
        save_state(state)
        latest_decision = (state.get('committee_decisions') or [{}])[0]
        return {
            'mission': 'QNT50023',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': snapshot,
            'memory_count': len(state.get('decision_memories') or []),
            'proposal_count': len(state.get('committee_proposals') or []),
            'decision_count': len(state.get('committee_decisions') or []),
            'latest_decision': latest_decision,
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'enabled', 'auto_sync_sources', 'require_risk_clearance', 'require_liquidity_support',
            'require_control_loop_context', 'require_committee_approval', 'minimum_committee_score',
            'minimum_memory_confidence_score', 'minimum_available_liquidity',
            'operator_review_notional_threshold', 'max_memories_to_keep', 'max_decisions_to_keep',
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('executive_committee_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def record_memory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), source='record_memory')
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        title = str(payload.get('title') or '').strip()
        if not title:
            raise ValueError('title is required')
        summary = str(payload.get('summary') or '').strip()
        outcome_summary = str(payload.get('outcome_summary') or '').strip()
        memory_confidence_score = self._round(payload.get('memory_confidence_score'), 2)
        outcome_quality_score = self._round(payload.get('outcome_quality_score'), 2)
        status = 'trusted'
        if memory_confidence_score < float(policy.get('minimum_memory_confidence_score') or 0.0):
            status = 'watch'
        memory = {
            'memory_id': f'ecm_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'decision_scope': str(payload.get('decision_scope') or 'EXECUTIVE_CAPITAL_DECISION'),
            'title': title,
            'summary': summary,
            'outcome_summary': outcome_summary,
            'tags': payload.get('tags') or [],
            'memory_confidence_score': memory_confidence_score,
            'outcome_quality_score': outcome_quality_score,
            'status': status,
            'linked_decision_id': str(payload.get('linked_decision_id') or ''),
        }
        state.setdefault('decision_memories', []).insert(0, memory)
        keep = int(policy.get('max_memories_to_keep', 300) or 300)
        state['decision_memories'] = state['decision_memories'][:keep]
        save_state(state)
        append_audit('executive_committee_memory_recorded', {
            'memory_id': memory['memory_id'],
            'status': status,
            'memory_confidence_score': memory_confidence_score,
        })
        return {'mission': 'QNT50023', 'status': status, 'memory': memory, 'summary': self.summary()}

    def _gate(self, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        policy = self._policy(state)
        snapshot = state.get('last_sync') or self._source_snapshot({'source': 'direct'})
        issues: List[str] = []
        if not bool(policy.get('enabled', True)):
            issues.append('executive committee disabled by policy')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            issues.append('risk kill switch active')
        if policy.get('require_liquidity_support', True) and float(snapshot.get('available_to_move') or 0.0) < float(policy.get('minimum_available_liquidity') or 0.0):
            issues.append('available liquidity below executive policy minimum')
        if policy.get('require_control_loop_context', True) and str(snapshot.get('control_loop_posture') or 'degraded') not in {'ready', 'guarded'}:
            issues.append('autonomous control loop posture not ready for committee action')
        if snapshot.get('safe_mode') and str(payload.get('requested_action') or '').lower() in {'live_allocate', 'live_execute', 'increase_live_risk'}:
            issues.append('safe mode blocks requested live action')
        if int(snapshot.get('open_intercompany_flow_count') or 0) > 0 and str(payload.get('decision_scope') or '').upper() == 'GLOBAL_REALLOCATION':
            issues.append('open intercompany flows block global reallocation decision')
        return {'ready': len(issues) == 0, 'issues': issues, 'snapshot': snapshot}

    def propose(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), source='propose')
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        title = str(payload.get('title') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not title:
            raise ValueError('title is required')
        if self._policy(state).get('auto_sync_sources', True):
            self.sync_context({'source': 'propose'})
            state = self._refresh()
        gate = self._gate(state, payload)
        conviction = self._round(payload.get('conviction_score'), 2)
        scenario = self._round(payload.get('scenario_coverage_score'), 2)
        execution = self._round(payload.get('execution_feasibility_score'), 2)
        alignment = self._round(payload.get('policy_alignment_score'), 2)
        proposed_notional = self._round(payload.get('proposed_notional'), 2)
        memory_matches = self._recall_memories(payload, state.get('decision_memories') or [], limit=int(payload.get('memory_limit') or 5))
        memory_bias = 0.0
        if memory_matches:
            top = memory_matches[0]
            memory_bias = min(float(top.get('match_score') or 0.0), 100.0) * 0.10
        score = round(max(0.0, min(100.0, conviction * 0.30 + scenario * 0.25 + execution * 0.20 + alignment * 0.15 + memory_bias)), 2)
        status = 'proposed'
        committee_posture = 'approved'
        recommended_action = str(payload.get('requested_action') or 'observe').lower()
        if gate.get('issues'):
            committee_posture = 'blocked'
            status = 'blocked'
            recommended_action = 'defer'
        elif score < float(policy.get('minimum_committee_score') or 0.0):
            committee_posture = 'watch'
            status = 'watch'
            recommended_action = 'review'
        if proposed_notional >= float(policy.get('operator_review_notional_threshold') or 0.0) and committee_posture == 'approved':
            committee_posture = 'operator_review'
            status = 'review_required'
            recommended_action = 'supervise'
        proposal = {
            'proposal_id': f'ecc_prop_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'decision_scope': str(payload.get('decision_scope') or 'EXECUTIVE_CAPITAL_DECISION'),
            'title': title,
            'summary': str(payload.get('summary') or ''),
            'requested_action': str(payload.get('requested_action') or 'observe'),
            'target_strategy': str(payload.get('target_strategy') or ''),
            'proposed_notional': proposed_notional,
            'capital_delta_pct': self._round(payload.get('capital_delta_pct'), 4),
            'tags': payload.get('tags') or [],
            'scores': {
                'conviction_score': conviction,
                'scenario_coverage_score': scenario,
                'execution_feasibility_score': execution,
                'policy_alignment_score': alignment,
                'committee_score': score,
            },
            'memory_matches': memory_matches,
            'gate': gate,
            'status': status,
            'committee_posture': committee_posture,
            'recommended_action': recommended_action,
            'directive': {
                'directive_type': 'capital_committee_decision',
                'action': recommended_action,
                'target_strategy': str(payload.get('target_strategy') or ''),
                'proposed_notional': proposed_notional,
                'capital_delta_pct': self._round(payload.get('capital_delta_pct'), 4),
            },
        }
        state.setdefault('committee_proposals', []).insert(0, proposal)
        state['committee_proposals'] = state['committee_proposals'][:int(policy.get('max_decisions_to_keep', 250) or 250)]
        save_state(state)
        append_audit('executive_committee_proposal_created', {
            'proposal_id': proposal['proposal_id'],
            'status': status,
            'committee_score': score,
        })
        return {'mission': 'QNT50023', 'status': status, 'proposal': proposal, 'summary': self.summary()}

    def _find_proposal(self, state: Dict[str, Any], proposal_id: str) -> Dict[str, Any]:
        for item in state.get('committee_proposals', []):
            if item.get('proposal_id') == proposal_id:
                return item
        raise ValueError('proposal_id not found')

    def approve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), source='approve')
        operator = str(payload.get('operator') or '').strip()
        proposal_id = str(payload.get('proposal_id') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not proposal_id:
            raise ValueError('proposal_id is required')
        proposal = self._find_proposal(state, proposal_id)
        policy = self._policy(state)
        outcome = str(payload.get('outcome') or 'approve').lower()
        if proposal.get('committee_posture') == 'blocked' and outcome == 'approve':
            raise ValueError('blocked proposal cannot be approved')
        if policy.get('require_committee_approval', True) and outcome not in {'approve', 'reject', 'defer'}:
            raise ValueError('outcome must be approve, reject, or defer')
        decision_status = {'approve': 'approved', 'reject': 'rejected', 'defer': 'deferred'}[outcome]
        directive = dict(proposal.get('directive') or {})
        if decision_status != 'approved':
            directive['action'] = 'defer' if outcome == 'defer' else 'reject'
        decision = {
            'decision_id': f'ecc_dec_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'proposal_id': proposal_id,
            'title': proposal.get('title'),
            'decision_scope': proposal.get('decision_scope'),
            'status': decision_status,
            'committee_posture': proposal.get('committee_posture'),
            'committee_score': (proposal.get('scores') or {}).get('committee_score'),
            'directive': directive,
            'rationale': str(payload.get('rationale') or ''),
            'memory_matches': proposal.get('memory_matches') or [],
            'gate': proposal.get('gate') or {},
        }
        state.setdefault('committee_decisions', []).insert(0, decision)
        state['committee_decisions'] = state['committee_decisions'][:int(policy.get('max_decisions_to_keep', 250) or 250)]
        save_state(state)
        append_audit('executive_committee_decision_recorded', {
            'decision_id': decision['decision_id'],
            'proposal_id': proposal_id,
            'status': decision_status,
        })
        return {'mission': 'QNT50023', 'status': decision_status, 'decision': decision, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = self._refresh()
        state = {
            'generated_by': 'QNT50023',
            'status': 'degraded',
            'policy': current.get('policy') or load_state().get('policy'),
            'last_sync': None,
            'sync_history': [],
            'decision_memories': [],
            'committee_proposals': [],
            'committee_decisions': [],
            'audit_log': [],
        }
        save_state(state)
        append_audit('executive_committee_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
        })
        return self.summary()
