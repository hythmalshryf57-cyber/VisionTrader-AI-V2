import subprocess
import time
import os
import sys

def test_boot():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    with open("boot_test_output.log", "w", encoding="utf-8") as f:
        proc = subprocess.Popen(
            [sys.executable, "-u", "main.py"],
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=r"c:\Users\user\Desktop\visiontrader_ai\backend"
        )
        
        time.sleep(8)
        proc.kill()
        
    with open("boot_test_output.log", "r", encoding="utf-8") as f:
        outs = f.read()
        
    if "Application startup complete." in outs:
        print("SERVER STARTED = YES")
    else:
        print("SERVER STARTED = NO")

if __name__ == "__main__":
    test_boot()
