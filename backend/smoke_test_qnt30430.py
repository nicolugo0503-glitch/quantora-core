import importlib.util, pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
p = root / "backend" / "app" / "main.py"
spec = importlib.util.spec_from_file_location("quantora_main", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert hasattr(mod, "workspace_governance_pending")
assert hasattr(mod, "workspace_governance_submit")
assert hasattr(mod, "workspace_governance_approve")
assert hasattr(mod, "workspace_governance_reject")
print("QNT30430 smoke test passed")
