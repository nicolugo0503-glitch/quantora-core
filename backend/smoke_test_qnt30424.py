
from pathlib import Path
root = Path(__file__).resolve().parent / 'app' / 'main.py'
main = root.read_text()
assert '/workspace/execution/fills' in main
assert '/workspace/positions' in main
assert '/workspace/execution/lifecycle' in main
assert 'organization_execution_fills' in main
assert 'organization_positions' in main
panel = (root.parent.parent.parent / 'frontend' / 'org_execution_capital_engine.html').read_text()
assert 'Lifecycle Events' in panel
assert 'positions' in panel.lower()
print('QNT30424 smoke test passed')
