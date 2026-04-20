from pathlib import Path
import py_compile

main_py = Path(__file__).resolve().parent / 'app' / 'main.py'
html = Path(__file__).resolve().parent.parent / 'frontend' / 'org_execution_capital_engine.html'

text = main_py.read_text()
for needle in [
    "/workspace/positions/reduce",
    "/workspace/positions/close",
    "/workspace/positions/flatten",
    "position_reduced",
    "position_closed",
]:
    assert needle in text, f"missing {needle}"

html_text = html.read_text()
for needle in ["Reduce 25%", "Reduce 50%", "Flatten All", "/workspace/positions/reduce"]:
    assert needle in html_text, f"missing {needle} in html"

py_compile.compile(str(main_py), doraise=True)
print('QNT30428 smoke test passed')
