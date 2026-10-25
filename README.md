# Appliance Clock Sync

Resets the Samsung range and microwave clocks after power outages, with no taps.

A GitHub Actions job runs every 30 minutes (at :13 and :43) and sends the current
St. Thomas time to both appliances through SmartThings. It skips an appliance that is
offline or cooking. After an outage the clocks are right again within about half an hour
of the power coming back.

The time is set with an undocumented SmartThings command (the one behind the app's
"Sync time"), so a Samsung firmware update could break it.

## Pieces

- `sync.py` – renews SmartThings access when needed, then sets each clock.
- `.github/workflows/sync.yml` – the schedule; commits `tokens.enc` when access is renewed.
- `tokens.enc` – current SmartThings tokens, encrypted with the `TOKEN_KEY` secret.
- `authorize.py` – sign-in helper, only needed again if access is ever lost.

Repo secrets: `ST_CLIENT_ID`, `ST_CLIENT_SECRET`, `TOKEN_KEY`, `ST_INITIAL_REFRESH_TOKEN`.
Repo variable: `DEVICE_IDS` (comma-separated SmartThings device IDs).
App credentials are also kept on the Mac in `~/.appliance-clock-sync/client.json`.

## If it stops working

GitHub emails you when a run fails. If the log says the token was rejected (HTTP 400/401
on renewal), sign in again: open the approval link below, approve, copy the address of the
"page not found" tab, then run

    python3 authorize.py "<that address>"

Approval link (client ID is in `~/.appliance-clock-sync/client.json`):
`https://api.smartthings.com/oauth/authorize?client_id=<CLIENT_ID>&response_type=code&redirect_uri=https%3A%2F%2Ftmckague-antilles.github.io%2Fclock-sync-callback&scope=r%3Adevices%3A%2A+x%3Adevices%3A%2A+l%3Adevices`

To run a sync right now: GitHub → Actions → Sync appliance clocks → Run workflow.
