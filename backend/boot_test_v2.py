import os
import subprocess
import sys
import time
import re

AI_CORE_PATH = r'c:\Users\user\Desktop\visiontrader_ai\backend\services\ai_core.py'
BACKEND_DIR  = r'c:\Users\user\Desktop\visiontrader_ai\backend'
TASKS = ['_daily_tune', '_weekly_cluster_tune', '_monthly_review']

def set_enabled_task(task_to_enable):
    with open(AI_CORE_PATH, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
    for i, line in enumerate(lines):
        for task in TASKS:
            if 'threading.Thread(target=' + task in line:
                lines[i] = re.sub(r'^(\s*)#*\s*threading\.Thread', r'\1# threading.Thread', line)
                if task == task_to_enable:
                    lines[i] = lines[i].replace('# threading.Thread', 'threading.Thread')
    with open(AI_CORE_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def test_boot(task_name, timeout=45):
    set_enabled_task(task_name)
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    log_file = os.path.join(BACKEND_DIR, 'isolation_test.log')
    with open(log_file, 'w', encoding='utf-8') as f:
        proc = subprocess.Popen(
            [sys.executable, '-u', 'main.py'],
            stdout=f, stderr=subprocess.STDOUT,
            env=env, cwd=BACKEND_DIR
        )
        deadline = time.time() + timeout
        booted = False
        while time.time() < deadline:
            time.sleep(1)
            if proc.poll() is not None:
                break
            try:
                with open(log_file, 'r', encoding='utf-8') as rf:
                    if 'Application startup complete.' in rf.read():
                        booted = True
                        break
            except Exception:
                pass
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
    with open(log_file, 'r', encoding='utf-8') as f:
        outs = f.read()
    booted = booted or ('Application startup complete.' in outs)
    return booted, outs

results = []

print('Testing BASELINE (no tasks)...', flush=True)
booted, _ = test_boot(None)
status = 'YES' if booted else 'NO'
results.append(('NO_TASKS_BASELINE', 'NO', status))
print('  -> ' + status, flush=True)

for task in TASKS:
    print('Testing ' + task + '...', flush=True)
    booted, outs = test_boot(task)
    status = 'YES' if booted else 'NO'
    results.append((task, 'YES', status))
    print('  -> ' + status, flush=True)
    if not booted:
        err_path = os.path.join(BACKEND_DIR, task + '_error.log')
        with open(err_path, 'w', encoding='utf-8') as f:
            f.write(outs)
        print('  [LOG saved: ' + err_path + ']', flush=True)

print()
print('| Task Name            | Started? | Server Booted? |')
print('| -------------------- | -------- | -------------- |')
for name, started, booted in results:
    print('| ' + name.ljust(20) + ' | ' + started.ljust(8) + ' | ' + booted.ljust(14) + ' |')
