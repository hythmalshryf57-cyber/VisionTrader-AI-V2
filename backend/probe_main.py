"""
Mini probe: adds BOOT_STEP prints to main.py imports area (read-only analysis).
Runs main.py but intercepts prints to determine last step before hang.
"""
import sys, os, subprocess, time

# Inject probe prints into a temp copy of main.py
BACKEND = r'c:\Users\user\Desktop\visiontrader_ai\backend'
MAIN_PATH = os.path.join(BACKEND, 'main.py')
PROBE_PATH = os.path.join(BACKEND, 'main_probe.py')

with open(MAIN_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

INJECTIONS = [
    ('from database import get_db', 'print("[PROBE-1] importing database", flush=True)\n'),
    ('from supabase_client import', 'print("[PROBE-2] importing supabase_client", flush=True)\n'),
    ('from services.auto_scanner import auto_scanner', 'print("[PROBE-3] importing auto_scanner", flush=True)\n'),
    ('from services.cache_service import cache_service', 'print("[PROBE-4] importing cache_service", flush=True)\n'),
    ('from services.vector_memory import vector_memory', 'print("[PROBE-5] importing vector_memory", flush=True)\n'),
    ('from services.trade_manager import trade_manager_service', 'print("[PROBE-6] importing trade_manager", flush=True)\n'),
    ('from services.trade_protection import trade_protection_service', 'print("[PROBE-7] importing trade_protection", flush=True)\n'),
    ('from services.market_protection import market_protection_service', 'print("[PROBE-8] importing market_protection", flush=True)\n'),
    ('from services.deep_market import deep_market_scanner', 'print("[PROBE-9] importing deep_market", flush=True)\n'),
    ('from services.calendar_service import calendar_service', 'print("[PROBE-10] importing calendar_service", flush=True)\n'),
    ('from services.ai_core import ai_core_service', 'print("[PROBE-11] importing ai_core (AIService init will run!)", flush=True)\n'),
]

for marker, probe in INJECTIONS:
    if marker in content:
        content = content.replace(marker, probe + marker, 1)

# After all imports, before app routes
after_imports_marker = 'create_tables(models.Base)'
if after_imports_marker in content:
    content = content.replace(
        after_imports_marker,
        'print("[PROBE-12] create_tables running", flush=True)\n' + after_imports_marker + '\nprint("[PROBE-13] create_tables done, routes about to register", flush=True)',
        1
    )

# Before uvicorn.run
uvicorn_marker = 'uvicorn.run("main:app"'
if uvicorn_marker in content:
    content = content.replace(
        uvicorn_marker,
        'print("[PROBE-14] uvicorn.run starting!", flush=True)\n    ' + uvicorn_marker,
        1
    )

with open(PROBE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Probe file written. Running...", flush=True)

env = os.environ.copy()
env['PYTHONUTF8'] = '1'

proc = subprocess.Popen(
    [sys.executable, '-u', 'main_probe.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, env=env, cwd=BACKEND
)

last_probe = None
all_output = []
deadline = time.time() + 50

while time.time() < deadline:
    try:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        line = line.rstrip()
        all_output.append(line)
        print(line, flush=True)
        if '[PROBE' in line:
            last_probe = line
        if 'Application startup complete' in line:
            print('\n*** SERVER BOOTED SUCCESSFULLY! ***', flush=True)
            break
    except Exception:
        break

if proc.poll() is None:
    proc.terminate()
    proc.wait()

print(f'\n=== LAST PROBE BEFORE HANG: {last_probe} ===', flush=True)

# Cleanup
try:
    os.remove(PROBE_PATH)
except Exception:
    pass
