from pathlib import Path

text = Path(__file__).with_name("app").joinpath("main.py").read_text()
required = [
    "/workspace/isolation/status",
    "/workspace/isolation/enforce",
    "/workspace/isolation/audit",
    "workspace_isolation_audit",
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f"Missing QNT30422.1 markers: {missing}")
print("QNT30422.1 smoke test passed")
