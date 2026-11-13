import subprocess, time, urllib.request
from pathlib import Path
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
PROFILE = Path("chrome-rv").resolve()

def alive():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2); return True
    except Exception: return False

if not alive():
    subprocess.Popen([CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
                      "--no-first-run", "--no-default-browser-check",
                      "https://www.revisionvillage.com"],
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                     close_fds=True)
    for _ in range(40):
        if alive(): break
        time.sleep(0.5)
print("CDP ready:", alive())
