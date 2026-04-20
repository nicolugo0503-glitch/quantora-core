from strategy_marketplace import publish_strategy, create_mandate, allocate, summary

def run():
    s = publish_strategy("Alpha Core","test","balanced")
    m = create_mandate(s["strategy_id"], 1000000, 25000)
    a = allocate(m["mandate_id"], "LP One", 50000)
    summ = summary()
    assert summ["allocations"] == 1
    assert summ["allocated_capital"] == 50000.0
    print("QNT30441 smoke test passed")

if __name__ == "__main__":
    run()
