# QNT30322 Railway Login/Input Reset Audit + Hotfix

## What was actually broken

The frontend was running a 5-second auto-refresh loop that called the full boot/render pipeline. On Railway, that meant the login/register card was being rebuilt repeatedly while the user typed. Every rebuild recreated the `<input>` elements, so the browser dropped the in-progress values.

## Root causes found in the shipped build

1. **Full DOM re-render on interval**
   - `setInterval(... boot/render ...)` refreshed the whole active module.
   - This destroyed login, register, strategy, capital, governance, approval, and control forms.

2. **Action handlers re-triggered full boot cycle**
   - After any POST action, the UI immediately re-booted and re-rendered the active module.
   - Response panels and in-progress draft values were wiped.

3. **Fragile global ID variable usage**
   - Functions referenced `login_email`, `login_password`, `reg_name`, etc. as implicit globals.
   - This is browser-dependent and can break in deployed environments.

4. **No draft preservation**
   - The UI had no cache of user-entered values.
   - Even harmless re-renders caused data loss.

5. **Background polling while logged out**
   - The app kept polling and refreshing even on the auth screen, where preserving user typing is more important than live data.

## What this hotfix changes

1. **Stable refresh engine**
   - Auto-refresh still runs, but it no longer re-renders the active form-heavy view while the user is typing or while logged out.

2. **Draft cache**
   - All input/select/textarea values are cached and restored across renders.

3. **Explicit DOM access**
   - Replaced implicit global element references with `document.getElementById(...)`.

4. **Persistent action feedback**
   - Auth/strategy/capital/policy/approval/admin responses are kept in state and restored after renders.

5. **Railway-safe fetches**
   - Frontend requests now use `cache: 'no-store'` to reduce stale UI fetch behavior.

## What was preserved

- Existing FastAPI backend structure
- Alpaca endpoints and env-based broker integration
- Unified command center layout
- Admin gating for governance/control/ledger areas

## Remaining architectural note

The current app still uses file-backed session state (`backend/artifacts/session.json`), which is fine for single-operator testing but is not multi-user safe for production. This hotfix fixes the login typing/reset problem without changing the current backend auth/session architecture.
