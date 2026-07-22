from pathlib import Path
import subprocess
import sys
import time

backend_dir = Path(__file__).parent
cmd = [sys.executable, '-u', 'main.py']
print('RUNNING', cmd, 'in', backend_dir)

p = subprocess.Popen(cmd, cwd=backend_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    try:
        out, _ = p.communicate(timeout=12)
    except subprocess.TimeoutExpired:
        print('PROCESS STILL RUNNING AFTER TIMEOUT, READING PARTIAL OUTPUT')
        out = p.stdout.read()
        p.terminate()
        p.wait(timeout=5)
    print('---CAPTURED-OUTPUT---')
    print(out)
finally:
    if p.poll() is None:
        p.terminate()
        p.wait(timeout=5)
