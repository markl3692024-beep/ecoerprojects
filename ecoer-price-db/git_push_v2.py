#!/usr/bin/env python3
import subprocess
import os

env = os.environ.copy()
env['GIT_TERMINAL_PROMPT'] = '0'
env['GCM_INTERACTIVE'] = 'never'

git = r'C:\Program Files\Git\bin\git.exe'
cwd = r'C:\Users\Mark\.qclaw\workspace'

proc = subprocess.Popen(
    [git, '-C', cwd, 'push', '-u', 'origin', 'main'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    env=env,
    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
)

print(f"PID: {proc.pid}")
print("Waiting for output...")
lines = []
import time
start = time.time()
while True:
    if proc.poll() is not None:
        break
    if time.time() - start > 20:
        proc.kill()
        print("Killed after 20s")
        break
    try:
        line = proc.stdout.readline()
        if line:
            decoded = line.decode('utf-8', errors='replace')
            print(decoded, end='')
            lines.append(decoded)
    except:
        break

stdout, _ = proc.communicate()
if stdout:
    print("REMAINING STDOUT:", stdout.decode('utf-8', errors='replace'))
print("RC:", proc.returncode)
print("Total output lines:", len(lines))