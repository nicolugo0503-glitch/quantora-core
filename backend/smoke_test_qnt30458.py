from backend.qnt30458_institutional_data_room_allocator_access_layer import build_data_room_package

pkg = build_data_room_package(
    folders=[{"id":"f1","folder_name":"Allocator DDQ","folder_type":"diligence","status":"active"}],
    documents=[{"id":"d1","document_name":"Quarterly Fund Tearsheet","folder_name":"Allocator DDQ","document_type":"pdf","status":"published"}],
    access_grants=[{"id":"a1","allocator_name":"Northstar Capital","access_scope":"ddq_plus_reporting","status":"active","expires_at":"2026-12-31"}],
    allocator_sessions=[{"id":"s1","allocator_name":"Northstar Capital","last_document":"Quarterly Fund Tearsheet","status":"active"}],
)
assert pkg["summary"]["folders_total"] == 1
assert pkg["summary"]["documents_published"] == 1
assert pkg["summary"]["room_score"] >= 55
print("QNT30458 smoke test passed")
