#!/usr/bin/env python3
import urllib.request
import json

req = urllib.request.Request(
    'https://api.github.com/repos/markl3692024-beep/ecoerprojects/commits?per_page=5',
    headers={'User-Agent': 'GitWindows/2.54.0'}
)
resp = urllib.request.urlopen(req, timeout=10)
commits = json.loads(resp.read())
print('Recent commits on GitHub:')
for c in commits[:3]:
    msg = c['commit']['message'].split('\n')[0]
    print(f'  {c["sha"][:7]} - {msg}')