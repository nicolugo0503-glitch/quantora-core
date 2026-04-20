from pathlib import Path
import json, re
root = Path('.')

# Create package dirs
pkg = root/'backend/app/institutional_breach_exception_resolution'
pkg.mkdir(parents=True, exist_ok=True)
(pkg/'__init__.py').write_text('', encoding='utf-8')

(pkg/'state_store.py').write_text('''from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'institutional_breach_exception_resolution_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50026',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'require_risk_sync': True,
            'require_settlement_sync': True,
            'require_charter_directive_context': True,
            'require_supervisory_escalation_for_severe': True,
            'severe_alignment_threshold': 60.0,
            'default_resolution_sla_hours': 24,
            'max_cases_to_keep': 500,
            'max_resolutions_to_keep': 500,
            'max_escalations_to_keep': 500,
        },
        'last_sync': None,
        'sync_history': [],
        'breach_cases': [],
        'exception_resolutions': [],
        'escalation_log': [],
        'audit_log': [],
    }


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    return json.loads(STATE_PATH.read_text(encoding='utf-8'))


def save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    return state


def append_audit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state.setdefault('audit_log', []).insert(0, {
        'event_id': f'institutional_breach_exception_resolution_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
''', encoding='utf-8')

(pkg/'engine.py').write_text('''from __future__ import annotations

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
''', encoding='utf-8')

(root/'backend/app/models/institutional_breach_exception_resolution_models.py').write_text('''from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class InstitutionalBreachExceptionConfigurationRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_sync_sources: Optional[bool] = None
    require_risk_sync: Optional[bool] = None
    require_settlement_sync: Optional[bool] = None
    require_charter_directive_context: Optional[bool] = None
    require_supervisory_escalation_for_severe: Optional[bool] = None
    severe_alignment_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    default_resolution_sla_hours: Optional[int] = Field(default=None, ge=1, le=720)
    max_cases_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_resolutions_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    max_escalations_to_keep: Optional[int] = Field(default=None, ge=25, le=5000)
    sync_after_configure: bool = True


class InstitutionalBreachExceptionSyncRequest(BaseModel):
    source: str = Field(default='manual')


class InstitutionalBreachCaseRegistrationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    breach_type: str = Field(default='MANDATE_EXCEPTION')
    severity: str = Field(default='medium')
    source_system: str = Field(default='institutional-charter')
    directive_id: str = Field(default='')
    target_strategy: str = Field(default='')
    requested_action: str = Field(default='')
    alignment_score: float = Field(default=0.0, ge=0, le=100)
    root_cause: str = Field(default='')
    summary: str = Field(default='')
    required_resolution_sla_hours: int = Field(default=24, ge=1, le=720)
    needs_supervisory_review: bool = False
    tags: List[str] = Field(default_factory=list)


class InstitutionalBreachEscalationRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    escalation_level: str = Field(default='operations')
    reason: str = Field(default='')


class InstitutionalExceptionResolutionRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    resolution_type: str = Field(default='override')
    approved: bool = False
    exception_scope: str = Field(default='')
    control_actions: List[str] = Field(default_factory=list)
    expiry_hours: int = Field(default=0, ge=0, le=720)
    notes: str = Field(default='')


class InstitutionalBreachExceptionResetRequest(BaseModel):
    operator: str = Field(..., min_length=1)
    reason: str = Field(default='manual reset')
''', encoding='utf-8')

(root/'backend/app/qnt50026_institutional_breach_escalation_exception_resolution_layer_router.py').write_text('''from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
from backend.app.institutional_breach_exception_resolution.state_store import load_state
from backend.app.models.institutional_breach_exception_resolution_models import (
    InstitutionalBreachCaseRegistrationRequest,
    InstitutionalBreachEscalationRequest,
    InstitutionalBreachExceptionConfigurationRequest,
    InstitutionalBreachExceptionResetRequest,
    InstitutionalBreachExceptionSyncRequest,
    InstitutionalExceptionResolutionRequest,
)

router = APIRouter(tags=['qnt50026-institutional-breach-escalation-exception-resolution'])
engine = InstitutionalBreachExceptionResolutionEngine()


@router.get('/institutional-breach/health')
def qnt50026_health():
    summary = engine.summary()
    return {
        'status': 'ok',
        'mission': 'QNT50026',
        'posture': summary.get('posture'),
        'case_count': summary.get('case_count'),
        'resolution_count': summary.get('resolution_count'),
        'escalation_count': summary.get('escalation_count'),
    }


@router.get('/institutional-breach/state')
def qnt50026_state():
    return load_state()


@router.get('/institutional-breach/summary')
def qnt50026_summary():
    return engine.summary()


@router.get('/institutional-breach/cases')
def qnt50026_cases(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'breach_cases': state.get('breach_cases', [])[:use_limit]}


@router.get('/institutional-breach/resolutions')
def qnt50026_resolutions(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'exception_resolutions': state.get('exception_resolutions', [])[:use_limit]}


@router.get('/institutional-breach/escalations')
def qnt50026_escalations(limit: int = 50):
    state = load_state()
    use_limit = max(1, min(int(limit), 250))
    return {'mission': 'QNT50026', 'escalation_log': state.get('escalation_log', [])[:use_limit]}


@router.post('/institutional-breach/configure')
def qnt50026_configure(payload: InstitutionalBreachExceptionConfigurationRequest = Body(default=InstitutionalBreachExceptionConfigurationRequest())):
    return engine.configure(payload.model_dump(exclude_none=True))


@router.post('/institutional-breach/sync-context')
def qnt50026_sync(payload: InstitutionalBreachExceptionSyncRequest = Body(default=InstitutionalBreachExceptionSyncRequest())):
    return engine.sync_context(payload.model_dump(exclude_none=True))


@router.post('/institutional-breach/register-case')
def qnt50026_register_case(payload: InstitutionalBreachCaseRegistrationRequest = Body(...)):
    try:
        return engine.register_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/escalate')
def qnt50026_escalate(payload: InstitutionalBreachEscalationRequest = Body(...)):
    try:
        return engine.escalate_case(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/resolve')
def qnt50026_resolve(payload: InstitutionalExceptionResolutionRequest = Body(...)):
    try:
        return engine.resolve_exception(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/institutional-breach/reset')
def qnt50026_reset(payload: InstitutionalBreachExceptionResetRequest = Body(...)):
    try:
        return engine.reset(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
''', encoding='utf-8')

(root/'backend/app/state/institutional_breach_exception_resolution_state.json').write_text(json.dumps({
    'generated_by': 'QNT50026',
    'status': 'degraded',
    'policy': {
        'enabled': True,
        'auto_sync_sources': True,
        'require_risk_sync': True,
        'require_settlement_sync': True,
        'require_charter_directive_context': True,
        'require_supervisory_escalation_for_severe': True,
        'severe_alignment_threshold': 60.0,
        'default_resolution_sla_hours': 24,
        'max_cases_to_keep': 500,
        'max_resolutions_to_keep': 500,
        'max_escalations_to_keep': 500,
    },
    'last_sync': None,
    'sync_history': [],
    'breach_cases': [],
    'exception_resolutions': [],
    'escalation_log': [],
    'audit_log': [],
}, indent=2), encoding='utf-8')

(root/'frontend/mission_qnt50026_institutional_breach_escalation_exception_resolution_layer.html').write_text('''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>QNT50026 - Institutional Breach Escalation + Exception Resolution Layer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background:#0f172a; color:#e2e8f0; }
    .card { background:#111827; border:1px solid #334155; border-radius:12px; padding:20px; max-width:1000px; }
    h1,h2 { margin-top:0; }
    code { background:#1e293b; padding:2px 6px; border-radius:6px; }
    ul { line-height:1.6; }
  </style>
</head>
<body>
  <div class="card">
    <h1>QNT50026 — Institutional Breach Escalation + Exception Resolution Layer</h1>
    <p>Governance control layer for breach registration, supervisory escalation, controlled exceptions, and audit-grade resolution of governed execution failures.</p>
    <h2>Capabilities</h2>
    <ul>
      <li>Synchronizes risk, settlement, autonomous control, and institutional charter directive posture.</li>
      <li>Registers institutional breach cases with directive lineage, severity, SLA, and causal evidence.</li>
      <li>Escalates severe or operational breaches into governed review tracks.</li>
      <li>Approves or rejects exceptions only after policy validation and supervisory handling when required.</li>
    </ul>
    <h2>Primary endpoints</h2>
    <ul>
      <li><code>GET /institutional-breach/health</code></li>
      <li><code>GET /institutional-breach/summary</code></li>
      <li><code>POST /institutional-breach/register-case</code></li>
      <li><code>POST /institutional-breach/escalate</code></li>
      <li><code>POST /institutional-breach/resolve</code></li>
      <li><code>POST /institutional-breach/reset</code></li>
    </ul>
  </div>
</body>
</html>
''', encoding='utf-8')

missions_dir = root/'MISSIONS/QNT50026_INSTITUTIONAL_BREACH_ESCALATION_EXCEPTION_RESOLUTION_LAYER'
missions_dir.mkdir(parents=True, exist_ok=True)
(missions_dir/'README.md').write_text('# QNT50026\n\nInstitutional Breach Escalation + Exception Resolution Layer.\n', encoding='utf-8')
(root/'QNT50026_INSTITUTIONAL_BREACH_ESCALATION_EXCEPTION_RESOLUTION_LAYER_NOTES.md').write_text('''# QNT50026 — Institutional Breach Escalation + Exception Resolution Layer

This mission adds an institutional control surface for breach registration, escalation, and exception resolution.

## Added
- Breach case registry with directive lineage
- Escalation log for supervisory and operations review
- Exception resolution ledger with approval gating
- Context sync against risk, settlement, control loop, and charter layers

## Primary backend endpoints
- `GET /institutional-breach/health`
- `GET /institutional-breach/summary`
- `GET /institutional-breach/cases`
- `GET /institutional-breach/resolutions`
- `GET /institutional-breach/escalations`
- `POST /institutional-breach/configure`
- `POST /institutional-breach/sync-context`
- `POST /institutional-breach/register-case`
- `POST /institutional-breach/escalate`
- `POST /institutional-breach/resolve`
- `POST /institutional-breach/reset`
''', encoding='utf-8')

(root/'test_qnt50026_smoke.py').write_text('''from backend.app.institutional_allocation_execution_charter.engine import InstitutionalAllocationExecutionCharterEngine
from backend.app.institutional_breach_exception_resolution.engine import InstitutionalBreachExceptionResolutionEngine
from backend.app.executive_capital_committee.engine import ExecutiveCapitalCommitteeEngine
from backend.app.executive_scenario_arbitration.engine import ExecutiveScenarioArbitrationEngine
from backend.app.risk_control.state_store import load_state as load_risk_state, save_state as save_risk_state


def prime_context():
    risk = load_risk_state()
    risk['kill_switch_triggered'] = False
    risk['kill_switch_level'] = 'normal'
    risk.setdefault('metrics', {})['breach_count'] = 0
    save_risk_state(risk)

    committee = ExecutiveCapitalCommitteeEngine()
    committee.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    committee.record_memory({
        'operator': 'smoke',
        'title': 'Prime committee context for QNT50026',
        'memory_type': 'capital_committee',
        'summary': 'Committee memory for breach escalation test.',
        'tags': ['smoke'],
    })

    arbitration = ExecutiveScenarioArbitrationEngine()
    arbitration.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    decision = arbitration.arbitrate({
        'operator': 'smoke',
        'scenario_name': 'QNT50026 arbitration case',
        'requested_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'policy_alignment_score': 91.0,
        'summary': 'Smoke scenario.',
    })['decision']

    charter = InstitutionalAllocationExecutionCharterEngine()
    charter.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    charter.sync_context({'source': 'smoke'})
    charter_id = charter.register_charter({
        'operator': 'smoke',
        'title': 'QNT50026 charter',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'max_notional': 50000.0,
        'max_capital_delta_pct': 0.10,
    })['charter']['charter_id']
    mandate_id = charter.register_mandate({
        'operator': 'smoke',
        'charter_id': charter_id,
        'title': 'QNT50026 mandate',
        'target_strategy': 'GLOBAL_MACRO',
        'allowed_actions': ['allocate'],
        'minimum_mandate_alignment_score': 80.0,
        'max_notional': 50000.0,
        'max_capital_delta_pct': 0.10,
    })['mandate']['mandate_id']
    directive = charter.enforce_mandate({
        'operator': 'smoke',
        'decision_id': decision['decision_id'],
        'mandate_id': mandate_id,
        'execution_action': 'allocate',
        'target_strategy': 'GLOBAL_MACRO',
        'proposed_notional': 25000.0,
        'capital_delta_pct': 0.05,
        'mandate_alignment_score': 92.0,
        'instruction': 'approved for smoke test',
    })['directive']
    return directive['directive_id']


def run_smoke():
    directive_id = prime_context()
    engine = InstitutionalBreachExceptionResolutionEngine()
    engine.reset({'operator': 'smoke', 'reason': 'qnt50026_smoke'})
    engine.sync_context({'source': 'smoke'})

    case = engine.register_case({
        'operator': 'smoke',
        'title': 'Breach case',
        'directive_id': directive_id,
        'breach_type': 'MANDATE_EXCEPTION',
        'severity': 'high',
        'alignment_score': 50.0,
        'summary': 'Escalation needed before exception resolution.',
    })['case']
    assert case['severity'] == 'severe'

    escalated = engine.escalate_case({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'escalation_level': 'supervisory',
        'reason': 'severe breach',
    })
    assert escalated['status'] == 'escalated'

    resolved = engine.resolve_exception({
        'operator': 'smoke',
        'case_id': case['case_id'],
        'resolution_type': 'override',
        'approved': True,
        'exception_scope': 'single_directive',
        'control_actions': ['heightened_monitoring'],
        'notes': 'approved after supervisory escalation',
    })
    assert resolved['status'] == 'approved'

    summary = engine.summary()
    assert summary['resolution_count'] >= 1
    return summary


if __name__ == '__main__':
    print(run_smoke())
''', encoding='utf-8')

# Update main.py
main = (root/'backend/app/main.py').read_text(encoding='utf-8')
import_line = "from .qnt50026_institutional_breach_escalation_exception_resolution_layer_router import router as qnt50026_router\n"
if import_line not in main:
    target = "from .qnt50025_institutional_allocation_execution_charter_mandate_enforcement_layer_router import router as qnt50025_router\n"
    main = main.replace(target, target + import_line)
include_line = "app.include_router(qnt50026_router)\n"
if include_line not in main:
    target = "app.include_router(qnt50025_router)\n"
    main = main.replace(target, target + include_line)
(root/'backend/app/main.py').write_text(main, encoding='utf-8')

# Update frontend mission registry
reg_path = root/'frontend/mission_registry.json'
reg = json.loads(reg_path.read_text(encoding='utf-8'))
missions = reg['missions']
if not any(m.get('id') == 'QNT50026' for m in missions):
    missions.append({
        'id': 'QNT50026',
        'title': 'Institutional Breach Escalation + Exception Resolution Layer',
        'path': 'mission_qnt50026_institutional_breach_escalation_exception_resolution_layer.html',
    })
reg_path.write_text(json.dumps(reg, indent=2), encoding='utf-8')

# Update manifest
manifest_path = root/'QUANTORA_FULL_PROJECT_MANIFEST.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for key in ['newly_merged_missions', 'integrated_missions', 'missions']:
    vals = manifest.get(key, [])
    if 'QNT50026' not in vals:
        vals.append('QNT50026')
        manifest[key] = vals
manifest['latest_mission'] = 'QNT50026'
manifest['latest_mission_label'] = 'Institutional Breach Escalation + Exception Resolution Layer'
manifest['package_name'] = 'QUANTORA_QNT50026_INSTITUTIONAL_BREACH_ESCALATION_EXCEPTION_RESOLUTION_LAYER.zip'
manifest['latest_mission_path'] = 'frontend/mission_qnt50026_institutional_breach_escalation_exception_resolution_layer.html'
manifest['latest_complete_project_mission'] = 'QNT50026'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
