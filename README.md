# Appliance Clock Sync

Resets the Samsung range and microwave clocks after power outages, with no taps.

A GitHub Actions job sends the current St. Thomas time to both appliances through
SmartThings. It skips an appliance that is offline or cooking.

GitHub's own schedule (:13 and :43) is best-effort and often runs only every few hours,
so a cron-job.org job starts the workflow every 15 minutes through the GitHub API
(`POST /repos/tmckague-Antilles/appliance-clock-sync/actions/workflows/sync.yml/dispatches`
with body `{"ref":"main"}`), using a fine-grained GitHub token limited to this repo with
Actions read/write. The GitHub schedule stays as a backup. After an outage the clocks
are right again within about 15 minutes of the power coming back. The repo is public
for unlimited free Actions minutes; nothing secret is in it.

If the cron-job.org job starts failing with HTTP 401, the GitHub token expired: make a
new one and paste it into the job's Authorization header.

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
`https://api.smartthings.com/oauth/authorize?client_id=<CLIENT_ID>&response_type=code&redirect_uri=https%3A%2F%2Ftmckague-antilles.github.io%2Fclock-sync-callback&scope=r%3Adevices%3A%2A+x%3Adevices%3A%2A`

When the approval page asks for a location, pick your home, then click Authorize.

To run a sync right now: GitHub → Actions → Sync appliance clocks → Run workflow.
