QNT30619 — INVESTOR NOTIFICATION CAMPAIGN ENGINE + SCHEDULED NOTICE BATCHES

ADDS
- backend/app/qnt30619_notification_campaign_router.py
- frontend/mission_qnt30619_notification_campaigns.html
- backend/artifacts/investor_notification_campaigns/

UPGRADES
- notification campaign summary
- create campaign workflow
- generate scheduled batch workflow
- send batch workflow
- investor portal navigation into notification campaigns
- command center entry for QNT30619 Notification Campaigns

API
- GET /api/notification-campaigns
- POST /api/notification-campaigns/create
- POST /api/notification-campaigns/batch
- POST /api/notification-campaigns/batch/send
- GET /api/notification-campaigns/summary

PURPOSE
- create investor notification campaigns and scheduled delivery batches
- apply routing preferences to batch generation
- prepare Quantora for scaled outbound investor communication workflows
