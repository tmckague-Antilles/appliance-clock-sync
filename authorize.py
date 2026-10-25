"""One-time (or recovery) sign-in: trade a SmartThings approval code for a refresh token
and hand it to the GitHub workflow.

Usage: python3 authorize.py "<the full address of the 'page not found' tab after approving>"

Reads the app credentials from ~/.appliance-clock-sync/client.json. Stores the refresh
token as the ST_INITIAL_REFRESH_TOKEN repo secret and removes tokens.enc so the next
run starts from it. Nothing secret is printed.
"""

import base64
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

REDIRECT_URI = "https://tmckague-antilles.github.io/clock-sync-callback"
TOKEN_URL = "https://auth-global.api.smartthings.com/oauth/token"
REPO = "tmckague-Antilles/appliance-clock-sync"
HERE = os.path.dirname(os.path.abspath(__file__))

client = json.load(open(os.path.expanduser("~/.appliance-clock-sync/client.json")))
code = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[1]).query)["code"][0]

basic = base64.b64encode(f"{client['client_id']}:{client['client_secret']}".encode()).decode()
req = urllib.request.Request(TOKEN_URL, method="POST", data=urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "client_id": client["client_id"],
    "code": code,
    "redirect_uri": REDIRECT_URI,
}).encode(), headers={
    "Authorization": f"Basic {basic}",
    "Content-Type": "application/x-www-form-urlencoded",
})
tok = json.load(urllib.request.urlopen(req, timeout=30))

subprocess.run(["gh", "secret", "set", "ST_INITIAL_REFRESH_TOKEN", "-R", REPO],
               input=tok["refresh_token"].encode(), check=True)
subprocess.run(["git", "-C", HERE, "pull", "-q"], check=True)
if os.path.exists(os.path.join(HERE, "tokens.enc")):
    subprocess.run(["git", "-C", HERE, "rm", "-q", "tokens.enc"], check=True)
    subprocess.run(["git", "-C", HERE, "commit", "-qm", "Re-authorize SmartThings"], check=True)
    subprocess.run(["git", "-C", HERE, "push", "-q"], check=True)
print("Authorized; scopes:", tok.get("scope"))
