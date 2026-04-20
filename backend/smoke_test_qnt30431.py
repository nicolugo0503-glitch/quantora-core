from app.main import app

if __name__ == "__main__":
    routes = {getattr(r, 'path', None) for r in app.routes}
    required = {'/workspace/brief/daily','/workspace/brief/risk','/workspace/brief/strategies','/workspace/brief/governance'}
    missing = sorted(required - routes)
    if missing:
        raise SystemExit(f"missing routes: {missing}")
    print('QNT30431 smoke test passed')
