# QNT50011 — Investor Distribution Waterfall + Payable Release Authority

Institutional additions:
- batch-level investor distribution waterfall registration
- performance + treasury + settlement context sync
- finance and operations attestation before release
- transfer-specific payable release authority
- treasury execution gate for investor distribution transfers

Core endpoints:
- `GET /investor-distributions/health`
- `GET /investor-distributions/summary`
- `POST /investor-distributions/register-batch`
- `POST /investor-distributions/authorize-batch`
- `POST /investor-distributions/bind-transfer`
- `POST /investor-distributions/authorize-payable`
- `POST /investor-distributions/record-execution`
