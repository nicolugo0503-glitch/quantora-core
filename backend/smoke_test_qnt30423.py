from pathlib import Path

root = Path(__file__).resolve().parent
main = (root / 'app' / 'main.py').read_text()
assert '/workspace/broker/configure' in main
assert '/workspace/capital/allocate' in main
assert '/workspace/execution/submit' in main
assert '/workspace/performance/summary' in main
panel = (root.parent / 'frontend' / 'org_execution_capital_engine.html').read_text()
assert 'QNT30423' in panel
assert 'Submit Org Execution' in panel
print('QNT30423 smoke test passed')
