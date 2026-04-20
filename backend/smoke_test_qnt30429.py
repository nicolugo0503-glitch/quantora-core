import importlib.util
from pathlib import Path

def run():
    main_path = Path(__file__).resolve().parent / "app" / "main.py"
    text = main_path.read_text(encoding="utf-8")
    required = [
        "/workspace/pnl/summary",
        "/workspace/attribution/strategies",
        "/workspace/attribution/symbols",
        "QNT30429",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Missing expected markers: {missing}")
    print("QNT30429 smoke test passed")

if __name__ == "__main__":
    run()
