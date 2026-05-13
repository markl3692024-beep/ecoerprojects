#!/usr/bin/env python3
"""Try GitHub API via HTTPS to check if we can authenticate"""
import urllib.request
import urllib.error
import json

# Try a simple GitHub API request
req = urllib.request.Request(
    'https://api.github.com/repos/markl3692024-beep/ecoerprojects',
    headers={'User-Agent': 'GitWindows/2.54.0', 'Accept': 'application/vnd.github.v3+json'}
)

try:
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read())
    print(f"Repository: {data.get('full_name')}")
    print(f"Default branch: {data.get('default_branch')}")
    print(f"Public: {data.get('visibility')}")
    print(f"Clone URL: {data.get('clone_url')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")