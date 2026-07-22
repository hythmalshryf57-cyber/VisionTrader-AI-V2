"""
Fine-grained probe: injects prints between lines 20-32 of main.py to find the exact hanging import.
"""
import sys, os, subprocess, time

BACKEND = r'c:\Users\user\Desktop\visiontrader_ai\backend'
MAIN_PATH = os.path.join(BACKEND, 'main.py')
PROBE_PATH = os.path.join(BACKEND, 'main_probe2.py')

with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

INJECTIONS = [
    ('from supabase_client import supabase_client, SUPABASE_CONFIGURED', '[A] supabase_client done'),
    ('from config import settings', '[B] config done'),
    ('import models', '[C] models done'),
    ('import auth', '[D] auth done'),
    ('from auth import router as auth_router', '[E] auth router done'),
    ('from admin import router as admin_router', '[F] admin router done'),
    ('from routers.analysis import router as analysis_router', '[G] analysis router done'),
    ('from services.journal_service import journal_service', '[H] journal_service done'),
    ('from services.smart_journal import smart_journal', '[I] smart_journal done'),
    ('from services.voting_engine import voting_engine', '[J] voting_engine done'),
    ('from services.ai_core import ai_core_service', '[K] *** ai_core STARTING (will take ~25s) ***'),
    ('from middleware import SecurityMiddleware, TrialMiddleware', '[L] ai_core DONE, middleware next'),
    ('from services.auto_scanner import auto_scanner', '[M] auto_scanner done'),
]

for marker, label in INJECTIONS:
    if marker in content:
        content = content.replace(
            marker,
            f'print("{label}", flush=True)\n' + marker,
            1
        )
    else:
        print(f"WARNING: marker not found: {marker[:50]}")

with open(PROBE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Probe2 written. Running (will wait up to 60s)...", flush=True)

env = os.environ.copy()
env['PYTHONUTF8'] = '1'

proc = subprocess.Popen(
    [sys.executable, '-u', 'main_probe2.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, env=env, cwd=BACKEND
)

last_probe = 'NONE'
deadline = time.time() + 60

while time.time() < deadline:
    try:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        line = line.rstrip()
        print(line, flush=True)
        for _, label in INJECTIONS:
            if label[:5] in line:
                last_probe = line
        if 'Application startup complete' in line:
            print('\n*** SERVER BOOTED! ***', flush=True)
            break
    except Exception:
        break

if proc.poll() is None:
    proc.terminate()
    proc.wait()

print(f'\n=== LAST STEP COMPLETED BEFORE HANG: {last_probe} ===', flush=True)

try:
    os.remove(PROBE_PATH)
except Exception:
    pass
