#!/usr/bin/env python3
import subprocess
import os
import time

env = os.environ.copy()
env['GIT_TERMINAL_PROMPT'] = '0'

git = r'C:\Program Files\Git\bin\git.exe'
cwd = r'C:\Users\Mark\.qclaw\workspace'

print("=== Git push test ===")
print(f"Git path: {git}")
print(f"CWD: {cwd}")

# First, check if we can fetch (read-only) - this uses the same auth
proc = subprocess.Popen(
    [git, '-C', cwd, 'push', '-u', 'origin', 'main', '--progress'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env=env
)

print(f"Started process PID: {proc.pid}")
time.sleep(5)

# Check if still running
if proc.poll() is None:
    print("Still running after 5s, checking output...")
    # Try to read with timeout
    try:
        stdout, stderr = proc.communicate(timeout=10)
        print("STDOUT:", stdout.decode('utf-8', errors='replace')[-2000:])
        print("STDERR:", stderr.decode('utf-8', errors='replace')[-1000:])
    except subprocess.TimeoutExpired:
        print("Still hanging after additional 10s, killing...")
        proc.kill()
        stdout, stderr = proc.communicate()
        print("STDOUT after kill:", stdout.decode('utf-8', errors='replace')[-1000:])
        print("STDERR after kill:", stderr.decode('utf-8', errors='replace')[-500:])
else:
    stdout, stderr = proc.communicate()
    print("STDOUT:", stdout.decode('utf-8', errors='replace')[-2000:])
    print("STDERR:", stderr.decode('utf-8', errors='replace')[-1000:])
    print("RC:", proc.returncode)