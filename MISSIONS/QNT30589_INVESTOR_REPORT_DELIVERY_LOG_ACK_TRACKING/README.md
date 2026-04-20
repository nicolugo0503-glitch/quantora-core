QNT30589 — INVESTOR REPORT DELIVERY LOG + ACKNOWLEDGEMENT TRACKING

ADDS
- backend/app/qnt30589_report_delivery_log_router.py
- frontend/mission_qnt30589_report_delivery_log.html
- backend/artifacts/investor_report_delivery_log/

UPGRADES
- report delivery log summary
- log latest pack workflow
- acknowledgement workflow
- investor portal navigation into delivery log
- command center entry for QNT30589 Delivery Log

API
- GET /api/report-delivery-log
- POST /api/report-delivery-log/log
- POST /api/report-delivery-log/ack
- POST /api/report-delivery-log/log-latest-pack
- GET /api/report-delivery-log/summary

PURPOSE
- create an auditable delivery trail for investor report packs
- track acknowledgement status after report delivery
- prepare Quantora for institutional communication controls
