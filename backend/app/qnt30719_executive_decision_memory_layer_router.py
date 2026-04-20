from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=['executive-decision-memory-layer'])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / 'backend' / 'artifacts'
ENGINE_DIR = ARTIFACTS_DIR / 'executive_decision_memory_layer'
DEFAULT_POLICY = {
    'retain_memories': 240,
    'minimum_memory_confidence_score': 84.0,
    'minimum_outcome_quality_score': 70.0,
    'require_executive_context': True,
    'require_forensic_clear': True,
    'require_recovery_clear': True,
    'require_reporting_clear': True,
    'require_growth_context': True,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _executive():
    from backend.app import qnt30718_executive_ai_command_layer_router as executive
    return executive

def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic

def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery

def _strategy():
    from backend.app import qnt30708_strategy_evolution_engine_router as strategy
    return strategy

def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting

def _growth():
    from backend.app import qnt30717_self_growing_capital_engine_router as growth
    return growth

def _safe(v: str) -> str:
    return hashlib.sha256((v or '').strip().lower().encode('utf-8')).hexdigest()[:24]

def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f'{_safe(email)}.json'

def _require_user():
    return _mu()._require_session()

def _now_ts() -> int:
    return int(time.time())

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append(store: dict, key: str, row: dict, retain: int):
    arr = list(store.get(key) or [])
    arr.insert(0, row)
    store[key] = arr[: max(int(retain or 1), 1)]

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            'email': email,
            'policy': dict(DEFAULT_POLICY),
            'memories': [],
            'recalls': [],
            'exceptions': [],
            'memory_book': [],
            'last_context': {},
            'latest_memory': None,
            'latest_recall': None,
        }
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return data
    return json.loads(path.read_text(encoding='utf-8'))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding='utf-8')

def _cross_system_context(email: str) -> dict:
    executive = _executive()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    reporting = _reporting()._summary_for_email(email)
    growth = _growth()._summary_for_email(email)
    return {
        'captured_at': _now_iso(),
        'executive': {
            'posture': (executive.get('executive_ai_command_layer_status') or {}).get('posture'),
            'recommended_band': (executive.get('executive_ai_command_layer_status') or {}).get('recommended_band'),
            'latest_score': (executive.get('executive_ai_command_layer_status') or {}).get('latest_score'),
        },
        'forensic': {
            'posture': (forensic.get('forensic_status') or {}).get('posture'),
            'critical_open_count': (forensic.get('forensic_status') or {}).get('critical_open_count'),
        },
        'recovery': {
            'posture': (recovery.get('recovery_status') or {}).get('posture'),
            'safe_mode': (recovery.get('recovery_status') or {}).get('safe_mode'),
            'valid_state': (recovery.get('current_validation') or {}).get('valid_state'),
        },
        'strategy': {
            'posture': (strategy.get('strategy_evolution_status') or {}).get('posture'),
            'latest_score': (strategy.get('strategy_evolution_status') or {}).get('latest_score'),
        },
        'reporting': {
            'posture': (reporting.get('reporting_disclosure_automation_status') or {}).get('posture'),
            'latest_score': (reporting.get('reporting_disclosure_automation_status') or {}).get('latest_score'),
        },
        'growth': {
            'posture': (growth.get('self_growing_capital_status') or {}).get('posture'),
            'latest_score': (growth.get('self_growing_capital_status') or {}).get('latest_score'),
            'band': (growth.get('self_growing_capital_status') or {}).get('compounding_band'),
        },
    }

def _tokenize(text: str) -> set:
    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in (text or ''))
    return {tok for tok in cleaned.split() if len(tok) > 2}

def _similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return round(100.0 * len(ta & tb) / max(len(ta | tb), 1), 2)

def _evaluate_memory(payload: dict, ctx: dict, policy: dict) -> dict:
    confidence = float(payload.get('memory_confidence_score') or 0.0)
    outcome_quality = float(payload.get('outcome_quality_score') or 0.0)
    blockers = []
    if confidence < float(policy.get('minimum_memory_confidence_score') or 0.0):
        blockers.append('memory-confidence-below-threshold')
    if outcome_quality < float(policy.get('minimum_outcome_quality_score') or 0.0):
        blockers.append('outcome-quality-below-threshold')
    if policy.get('require_executive_context') and ctx.get('executive', {}).get('posture') not in ('APPROVED', 'WATCH', 'OPERATOR_REVIEW'):
        blockers.append('executive-context-missing')
    if policy.get('require_forensic_clear') and ctx.get('forensic', {}).get('posture') not in ('READY', 'CLEAR', 'STABLE'):
        blockers.append('forensic-not-clear')
    if policy.get('require_recovery_clear') and (ctx.get('recovery', {}).get('safe_mode') or not ctx.get('recovery', {}).get('valid_state')):
        blockers.append('recovery-not-clear')
    if policy.get('require_reporting_clear') and ctx.get('reporting', {}).get('posture') not in ('READY', 'CLEAR', 'AUTOMATED'):
        blockers.append('reporting-not-clear')
    if policy.get('require_growth_context') and ctx.get('growth', {}).get('posture') not in ('READY', 'CLEAR', 'ACCELERATING', 'STABLE'):
        blockers.append('growth-context-not-clear')
    score = round(max(0.0, min(100.0, confidence * 0.55 + outcome_quality * 0.45)), 2)
    posture = 'TRUSTED'
    if blockers:
        posture = 'BLOCKED'
    elif score < float(policy.get('minimum_memory_confidence_score') or 0.0):
        posture = 'WATCH'
    memory_band = 'CORE'
    if posture == 'BLOCKED':
        memory_band = 'QUARANTINE'
    elif score < 88:
        memory_band = 'SUPERVISED'
    return {'score': score, 'posture': posture, 'memory_band': memory_band, 'blockers': blockers}

def _recall(query: str, memories: list, limit: int = 5) -> list:
    scored = []
    for item in memories or []:
        text = ' '.join([
            str(item.get('decision_scope') or ''),
            str(item.get('decision_title') or ''),
            str(item.get('decision_summary') or ''),
            str(item.get('outcome_summary') or ''),
            str(item.get('tags') or ''),
        ])
        score = _similarity(query, text)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{
        'match_score': score,
        'memory_id': item.get('memory_id'),
        'decision_title': item.get('decision_title'),
        'decision_scope': item.get('decision_scope'),
        'memory_band': (item.get('evaluation') or {}).get('memory_band'),
        'outcome_quality_score': item.get('inputs', {}).get('outcome_quality_score'),
        'created_at': item.get('created_at'),
    } for score, item in scored[:limit]]

def _summary_for_email(email: str) -> dict:
    store = _load(email)
    latest = store.get('latest_memory') or {}
    latest_recall = store.get('latest_recall') or {}
    return {
        'executive_decision_memory_layer_status': {
            'posture': (latest.get('evaluation') or {}).get('posture', 'IDLE'),
            'latest_score': (latest.get('evaluation') or {}).get('score'),
            'memory_band': (latest.get('evaluation') or {}).get('memory_band'),
            'memory_count': len(store.get('memories') or []),
            'recall_count': len(store.get('recalls') or []),
            'exception_count': len(store.get('exceptions') or []),
        },
        'latest_memory': latest,
        'latest_recall': latest_recall,
        'policy': store.get('policy') or dict(DEFAULT_POLICY),
        'memory_book': store.get('memory_book') or [],
        'exceptions': store.get('exceptions') or [],
        'last_context': store.get('last_context') or {},
    }

@router.get('/api/executive-decision-memory-layer/summary')
def summary(session=Depends(_require_user)):
    return _summary_for_email(session['email'])

@router.post('/api/executive-decision-memory-layer/record')
def record(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _evaluate_memory(payload, ctx, policy)
    memory = {
        'memory_id': f'exec-mem-{_now_ts()}',
        'created_at': _now_iso(),
        'decision_scope': payload.get('decision_scope') or 'EXECUTIVE_DECISION',
        'decision_title': payload.get('decision_title') or 'untitled-executive-decision',
        'decision_summary': payload.get('decision_summary') or '',
        'outcome_summary': payload.get('outcome_summary') or '',
        'tags': payload.get('tags') or [],
        'inputs': payload,
        'context': ctx,
        'evaluation': evaluation,
    }
    retain = int(policy.get('retain_memories') or 240)
    _append(store, 'memories', memory, retain)
    _append(store, 'memory_book', {'entry_id': f'exec-mem-book-{_now_ts()}', 'created_at': _now_iso(), 'memory_id': memory['memory_id'], 'decision_title': memory['decision_title'], 'score': evaluation.get('score'), 'posture': evaluation.get('posture'), 'memory_band': evaluation.get('memory_band')}, retain)
    if evaluation.get('posture') in ('BLOCKED', 'WATCH'):
        _append(store, 'exceptions', {'exception_id': f'exec-mem-ex-{_now_ts()}', 'created_at': _now_iso(), 'memory_id': memory['memory_id'], 'posture': evaluation.get('posture'), 'score': evaluation.get('score'), 'blockers': evaluation.get('blockers') or []}, retain)
    store['latest_memory'] = memory
    store['last_context'] = ctx
    _save(email, store)
    return {'ok': True, 'memory': memory, 'summary': _summary_for_email(email)}

@router.post('/api/executive-decision-memory-layer/recall')
def recall(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    query = str(payload.get('query') or '').strip()
    limit = int(payload.get('limit') or 5)
    results = _recall(query, store.get('memories') or [], limit=limit)
    recall_row = {'recall_id': f'exec-recall-{_now_ts()}', 'created_at': _now_iso(), 'query': query, 'limit': limit, 'matches': results}
    _append(store, 'recalls', recall_row, int((store.get('policy') or {}).get('retain_memories') or 240))
    store['latest_recall'] = recall_row
    _save(email, store)
    return {'ok': True, 'recall': recall_row, 'summary': _summary_for_email(email)}

@router.post('/api/executive-decision-memory-layer/policy')
def update_policy(payload: dict = Body(...), session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        if key in payload:
            policy[key] = payload[key]
    store['policy'] = policy
    _save(email, store)
    return {'ok': True, 'policy': policy}

@router.post('/api/executive-decision-memory-layer/bootstrap-demo')
def bootstrap_demo(session=Depends(_require_user)):
    email = session['email']
    store = _load(email)
    payload = {
        'decision_scope': 'EXECUTIVE_CAPITAL_MEMORY',
        'decision_title': 'tilt capital toward resilient momentum sleeve',
        'decision_summary': 'Executive layer approved a controlled tilt into resilient momentum after favorable regime, liquidity, and growth posture.',
        'outcome_summary': 'Allocation held risk inside guardrails and improved compounding efficiency without triggering defensive controls.',
        'memory_confidence_score': 92.0,
        'outcome_quality_score': 88.0,
        'tags': ['allocation', 'momentum', 'liquidity', 'regime'],
    }
    ctx = _cross_system_context(email)
    policy = store.get('policy') or dict(DEFAULT_POLICY)
    evaluation = _evaluate_memory(payload, ctx, policy)
    memory = {'memory_id': f'exec-mem-{_now_ts()}', 'created_at': _now_iso(), 'decision_scope': payload['decision_scope'], 'decision_title': payload['decision_title'], 'decision_summary': payload['decision_summary'], 'outcome_summary': payload['outcome_summary'], 'tags': payload['tags'], 'inputs': payload, 'context': ctx, 'evaluation': evaluation}
    retain = int(policy.get('retain_memories') or 240)
    _append(store, 'memories', memory, retain)
    _append(store, 'memory_book', {'entry_id': f'exec-mem-book-{_now_ts()}', 'created_at': _now_iso(), 'memory_id': memory['memory_id'], 'decision_title': memory['decision_title'], 'score': evaluation.get('score'), 'posture': evaluation.get('posture'), 'memory_band': evaluation.get('memory_band')}, retain)
    store['latest_memory'] = memory
    store['last_context'] = ctx
    store['latest_recall'] = {'recall_id': f'exec-recall-{_now_ts()}', 'created_at': _now_iso(), 'query': 'resilient momentum liquidity regime', 'limit': 5, 'matches': _recall('resilient momentum liquidity regime', [memory], limit=5)}
    _save(email, store)
    return {'ok': True, 'summary': _summary_for_email(email)}
