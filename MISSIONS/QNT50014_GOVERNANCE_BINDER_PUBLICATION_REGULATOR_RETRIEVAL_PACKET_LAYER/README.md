# QNT50014 — Governance Binder Publication + Regulator Retrieval Packet Layer

This mission extends Quantora's post-close control chain by converting QNT50013 official books release evidence into a governance binder publication case, regulator retrieval packet, and final published governance binder record.

## Core controls
- registration of publication cases from released official books
- regulator retrieval packet assembly with manifest and channel metadata
- final governance binder publication with retention lock
- audit trail for registration, packet assembly, and publication

## Primary endpoints
- `GET /governance-binder/health`
- `GET /governance-binder/summary`
- `GET /governance-binder/publications`
- `GET /governance-binder/retrieval-packets`
- `POST /governance-binder/register-publication`
- `POST /governance-binder/assemble-retrieval-packet`
- `POST /governance-binder/publish`
