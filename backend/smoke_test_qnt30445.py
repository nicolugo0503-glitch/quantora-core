from backend.qnt30445_monetization_engine import build_monetization_package

pkg = build_monetization_package(
    subscriptions=[{"client_name":"Client A","plan_name":"pro","monthly_amount":499,"status":"active"}],
    invoices=[{"client_name":"Client A","invoice_type":"management_fee","amount":1250,"status":"open"}],
    fee_ledger=[{"fee_type":"performance_fee","amount":900,"status":"recognized"}],
    licenses=[{"id":"lic_1","client_name":"Institutional Desk","plan_name":"institutional","monthly_amount":5000,"seat_count":10,"term_months":12,"status":"active"}],
)
assert pkg["summary"]["mrr"] == 499.0
assert pkg["summary"]["open_invoices"] == 1
assert pkg["summary"]["realized_revenue"] == 900.0
print("QNT30445 smoke test passed")
