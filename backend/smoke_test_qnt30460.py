from backend.qnt30460_executive_kpi_mission_control import build_executive_kpi_package

pkg = build_executive_kpi_package(
    kpis=[{"id":"k1","kpi_name":"ARR Run Rate","category":"revenue","current_value":480000,"target_value":1200000,"status":"watch"}],
    scorecards=[{"id":"s1","scorecard_name":"CEO Weekly Scorecard","owner":"ceo","score":72,"status":"active"}],
    executive_alerts=[{"id":"a1","alert_name":"Growth Target Miss Risk","severity":"high","status":"open","target_ref":"ARR Run Rate"}],
    strategic_initiatives=[{"id":"i1","initiative_name":"Institutional Launch Program","owner":"founder","status":"active","progress_percent":38}],
)
assert pkg["summary"]["kpis_total"] == 1
assert pkg["summary"]["scorecards_total"] == 1
assert pkg["summary"]["mission_score"] >= 50
print("QNT30460 smoke test passed")
