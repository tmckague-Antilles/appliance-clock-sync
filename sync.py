"""Set the Samsung range and microwave clocks to the current local time via SmartThings.

Runs on a schedule in GitHub Actions. SmartThings access tokens last 24 hours and
each refresh token works only once, so the current pair is kept encrypted in
tokens.enc and committed back by the workflow whenever it changes.
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://api.smartthings.com/v1"
TOKEN_URL = "https://auth-global.api.smartthings.com/oauth/token"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.enc")
REFRESH_MARGIN = 2 * 3600  # renew when less than 2 hours of access remain

CLIENT_ID = os.environ["ST_CLIENT_ID"]
CLIENT_SECRET = os.environ["ST_CLIENT_SECRET"]
TOKEN_KEY = os.environ["TOKEN_KEY"]
DEVICE_IDS = [d.strip() for d in os.environ["DEVICE_IDS"].split(",") if d.strip()]
TIMEZONE = os.environ.get("CLOCK_TZ", "America/St_Thomas")


def openssl(args, data):
    return subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-md", "sha256",
         "-pass", "env:TOKEN_KEY", *args],
        input=data, capture_output=True, check=True,
    ).stdout


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "rb") as f:
            return json.loads(openssl(["-d", "-a"], f.read()))
    # First run (or after re-authorizing): start from the refresh token stored as a secret.
    return {"refresh_token": os.environ["ST_INITIAL_REFRESH_TOKEN"], "expires_at": 0}


def save_state(state):
    with open(STATE_FILE, "wb") as f:
        f.write(openssl(["-e", "-a"], json.dumps(state).encode()))


def request(url, method="GET", body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"{}")


def refresh(state):
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": state["refresh_token"],
    }).encode()
    tok = request(TOKEN_URL, "POST", body, {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    new_state = {
        "access_token": tok["access_token"],
        "refresh_token": tok["refresh_token"],
        "expires_at": int(time.time()) + int(tok.get("expires_in", 86399)),
    }
    # Save before anything else: the old refresh token is now spent.
    save_state(new_state)
    print("Renewed SmartThings access")
    return new_state


def api(token, path, method="GET", payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    return request(f"{API}{path}", method, body, {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })


def sync_device(token, device_id, now):
    name = api(token, f"/devices/{device_id}").get("label") or device_id
    if api(token, f"/devices/{device_id}/health").get("state") != "ONLINE":
        print(f"{name}: offline, skipping")
        return
    status = api(token, f"/devices/{device_id}/components/main/status")
    machine = status.get("ovenOperatingState", {}).get("machineState", {}).get("value")
    if machine in ("running", "paused"):
        print(f"{name}: in use ({machine}), skipping")
        return
    result = api(token, f"/devices/{device_id}/commands", "POST", {"commands": [{
        "component": "main",
        "capability": "execute",
        "command": "execute",
        "arguments": ["/configuration/vs/0", {"x.com.samsung.da.currentTime": now}],
    }]})
    print(f"{name}: set to {now} ({result['results'][0]['status']})")


def main():
    state = load_state()
    if state.get("expires_at", 0) - time.time() < REFRESH_MARGIN:
        state = refresh(state)

    now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%dT%H:%M:%S")
    failed = False
    for device_id in DEVICE_IDS:
        try:
            sync_device(state["access_token"], device_id, now)
        except urllib.error.HTTPError as e:
            print(f"{device_id}: HTTP {e.code} {e.read()[:200]!r}")
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
