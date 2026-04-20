# QNT30332 Second Fix Notes

- Fixed false-positive Alpaca connected state when broker returns 401 or other soft errors.
- Cleared stale broker snapshots on soft broker failures so capital guard does not silently rely on stale data.
- Updated workspace to show effective capital source instead of stale raw state.
- Improved UI labels so execution route and capital source are clearly separated.
- Auto-selects broker capital source after successful Alpaca connect.
- Reloads broker status after capital source updates for clearer operator feedback.

Important: if Alpaca still shows HTTP 401 Unauthorized after this fix, the remaining issue is credentials, not the ZIP.
