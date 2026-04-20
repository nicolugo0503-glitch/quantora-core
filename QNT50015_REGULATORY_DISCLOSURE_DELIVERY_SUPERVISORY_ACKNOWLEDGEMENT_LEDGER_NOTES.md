# QNT50015 Notes

Added the regulatory disclosure delivery control layer on top of the QNT50014 governance binder publication flow.

## Integrated lineage
- QNT50012 period close
- QNT50013 official books release
- QNT50014 governance binder publication and regulator retrieval packet
- QNT50015 disclosure delivery receipt and supervisory acknowledgement ledger

## Endpoints
- `GET /regulatory-disclosures/health`
- `GET /regulatory-disclosures/summary`
- `GET /regulatory-disclosures/deliveries`
- `GET /regulatory-disclosures/acknowledgements`
- `POST /regulatory-disclosures/configure`
- `POST /regulatory-disclosures/sync-context`
- `POST /regulatory-disclosures/register-delivery`
- `POST /regulatory-disclosures/record-receipt`
- `POST /regulatory-disclosures/acknowledge`
- `POST /regulatory-disclosures/reset`
