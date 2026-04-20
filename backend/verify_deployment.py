import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.qnt30420_deployment_hardening import evaluate

artifacts_dir = ROOT / 'backend' / 'artifacts'
db_path = Path((__import__('os').getenv('QUANTORA_DB_PATH') or str(ROOT / 'state' / 'quantora.db')))
report = evaluate(artifacts_dir, db_path)
print(json.dumps(report, indent=2))
