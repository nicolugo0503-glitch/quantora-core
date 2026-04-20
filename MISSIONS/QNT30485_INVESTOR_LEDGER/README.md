# QNT30485 — INVESTOR LEDGER

Adds an isolated investor ledger mission module without modifying core files.

## Included
- `investor_ledger.py`
- `sample_investors.json`
- `README.md`

## Purpose
Tracks:
- investor accounts
- deposits
- withdrawals
- ownership calculations per fund

## Integration Path
Current system remains untouched.

Recommended future hook sequence:
1. Fund selected
2. Investor cash movement recorded
3. Net contributions calculated
4. Ownership table produced
5. NAV engine consumes ledger outputs in next mission

## Notes
- This is intentionally isolated for stability.
- No existing structure was changed.
