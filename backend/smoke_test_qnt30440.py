from investor_portal import investor_portal_summary, capital_statement

def run():
    portal = investor_portal_summary()
    stmt = capital_statement("Founding LP", 250000, 50000, "active")
    assert portal["portal_status"] == "ready"
    assert stmt["estimated_nav"] > stmt["committed_capital"]
    print("QNT30440 smoke test passed")

if __name__ == "__main__":
    run()
