@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Ultimate Grabber ^& Persistence Cleaner

:: =======================================================
:: ELEVACAO AUTOMATICA PARA ADMINISTRADOR (UAC)
:: =======================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo =======================================================
    echo  [*] Solicitando privilegios de Administrador...
    echo =======================================================
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
color 0B

echo =======================================================
echo          REMOVEDOR COMPLETO DE GRABBER E TRILHAS
echo =======================================================
echo.

:: -------------------------------------------------------
:: 1. FINALIZAR PROCESSOS DO GRABBER E DISCORD
:: -------------------------------------------------------
echo [*] 1. Finalizando processos ativos do grabber e Discord...
taskkill /f /im Discord.exe >nul 2>&1
taskkill /f /im DiscordCanary.exe >nul 2>&1
taskkill /f /im DiscordPTB.exe >nul 2>&1
taskkill /f /im DiscordDevelopment.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im chromelevator_x64.exe >nul 2>&1
taskkill /f /im elevator_payload.exe >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$pbk = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Network\Connections\pbk'); Get-Process -ErrorAction SilentlyContinue | Where-Object { try { $_.Path -and ($_.Path.StartsWith($pbk, [System.StringComparison]::OrdinalIgnoreCase)) } catch { $false } } | Stop-Process -Force -ErrorAction SilentlyContinue; Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { ($_.ExecutablePath -and $_.ExecutablePath -like '*\Microsoft\Network\Connections\pbk\*') -or ($_.CommandLine -and ($_.CommandLine -match 'ms\.py|chromelevator|msoobe_')) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };"
echo   [+] Processos encerrados com sucesso.

:: -------------------------------------------------------
:: 2. REMOVER TAREFA AGENDADA [SCHTASKS]
:: -------------------------------------------------------
echo.
echo [*] 2. Removendo Tarefas Agendadas...
schtasks /delete /tn "MicrosoftNetworkSync" /f >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName 'MicrosoftNetworkSync' -Confirm:$false -ErrorAction SilentlyContinue;"
echo   [+] Tarefa agendada 'MicrosoftNetworkSync' removida.

:: -------------------------------------------------------
:: 3. LIMPAR CHAVES DO REGISTRO [RUN, LOGON E UAC HIJACK]
:: -------------------------------------------------------
echo.
echo [*] 3. Limpando chaves do Registro [Run, Logon, UAC Hijack]...
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "RasManager" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "MicrosoftNetSync" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "Windows Defender Updater" /f >nul 2>&1

reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "RasManager" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "MicrosoftNetSync" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "Windows Defender Updater" /f >nul 2>&1

reg delete "HKCU\Environment" /v "UserInitMprLogonScript" /f >nul 2>&1
reg delete "HKCU\Software\Classes\ms-settings" /f >nul 2>&1
echo   [+] Chaves de inicializacao limpas.

:: -------------------------------------------------------
:: 4. REMOVER PERSISTENCIA WMI PERMANENTE
:: -------------------------------------------------------
echo.
echo [*] 4. Limpando assinaturas de persistencia WMI...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$wFilter = 'NetSyncFilter'; $wConsumer = 'NetSyncConsumer'; Get-CimInstance -Namespace 'root/subscription' -ClassName '__FilterToConsumerBinding' -ErrorAction SilentlyContinue | Where-Object { ($_.Filter -match $wFilter) -or ($_.Consumer -match $wConsumer) } | Remove-CimInstance -ErrorAction SilentlyContinue; Get-CimInstance -Namespace 'root/subscription' -ClassName 'CommandLineEventConsumer' -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $wConsumer } | Remove-CimInstance -ErrorAction SilentlyContinue; Get-CimInstance -Namespace 'root/subscription' -ClassName '__EventFilter' -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $wFilter } | Remove-CimInstance -ErrorAction SilentlyContinue;"
echo   [+] Assinaturas WMI verificadas e limpas.

:: -------------------------------------------------------
:: 5. REMOVER ATALHOS DE STARTUP
:: -------------------------------------------------------
echo.
echo [*] 5. Removendo atalhos da pasta Inicializar [Startup]...
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NetSync.lnk" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WinDefendUpdater.*" >nul 2>&1
del /f /q "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NetSync.lnk" >nul 2>&1
del /f /q "%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WinDefendUpdater.*" >nul 2>&1
echo   [+] Atalhos de inicializacao removidos.

:: -------------------------------------------------------
:: 6. DESTRAVAR E APAGAR PASTA DE PERSISTENCIA [PBK]
:: -------------------------------------------------------
echo.
echo [*] 6. Destravando e excluindo pasta oculta de persistencia [pbk]...
set "PBK_DIR=%APPDATA%\Microsoft\Network\Connections\pbk"
if not exist "%PBK_DIR%" goto pbk_cleaned

attrib -r -s -h "%PBK_DIR%\*.*" /s /d >nul 2>&1
attrib -r -s -h "%PBK_DIR%" >nul 2>&1
rmdir /s /q "%PBK_DIR%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path -LiteralPath '$env:APPDATA\Microsoft\Network\Connections\pbk') { Get-ChildItem -LiteralPath '$env:APPDATA\Microsoft\Network\Connections\pbk' -Force -Recurse -ErrorAction SilentlyContinue | ForEach-Object { try { $_.Attributes = 'Normal' } catch {} }; Remove-Item -LiteralPath '$env:APPDATA\Microsoft\Network\Connections\pbk' -Recurse -Force -ErrorAction SilentlyContinue; }"

if exist "%PBK_DIR%" (
    echo   [!] AVISO: Nao foi possivel remover a pasta pbk completamente.
) else (
    echo   [+] Pasta de persistencia pbk removida com sucesso.
)
goto pbk_done

:pbk_cleaned
echo   [+] Pasta de persistencia pbk nao encontrada [ja limpa].

:pbk_done

:: -------------------------------------------------------
:: 7. LIMPAR ARQUIVOS TEMPORARIOS RESIDUAIS
:: -------------------------------------------------------
echo.
echo [*] 7. Limpando pastas temporarias e residuos de extracao...
for /d %%x in ("%TEMP%\g_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bch_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bms_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bbr_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bop_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bed_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bbrv_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\bya_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\chromelevator*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%TEMP%\elevator_*") do rmdir /s /q "%%x" >nul 2>&1

del /f /q "%TEMP%\chromelevator*.*" >nul 2>&1
del /f /q "%TEMP%\msoobe_*.*" >nul 2>&1
del /f /q "%TEMP%\elevator_*.*" >nul 2>&1
del /f /q "%TEMP%\MC_Tokens_FULL.txt" >nul 2>&1

for /d %%x in ("%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\cache_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\pwcache_*") do rmdir /s /q "%%x" >nul 2>&1
for /d %%x in ("%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\chromelevator*") do rmdir /s /q "%%x" >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\chromelevator*.*" >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\elevator*.*" >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\EdgeUpdate\Download\msoobe*.*" >nul 2>&1
echo   [+] Arquivos e caches temporarios higienizados.

:: -------------------------------------------------------
:: 8. RESTAURAR ARQUIVO HOSTS DO WINDOWS
:: -------------------------------------------------------
echo.
echo [*] 8. Desbloqueando sites e limpando arquivo HOSTS...
attrib -r -s -h "%SystemRoot%\System32\drivers\etc\hosts" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$h = [System.IO.Path]::Combine($env:SystemRoot, 'System32\drivers\etc\hosts'); if (Test-Path $h) { [System.IO.File]::SetAttributes($h, [System.IO.FileAttributes]::Normal); $lines = @([System.IO.File]::ReadAllLines($h) | Where-Object { $_ -notmatch '(?i)(virustotal|avast|totalav|scanguard|totaladblock|pcprotect|mcafee|bitdefender|norton|avg|malwarebytes|pandasecurity|avira|eset|zillya|kaspersky|sophos|adaware|bullguard|clamav|drweb|emsisoft|f-secure|zonealarm|trendmicro|ccleaner)' }); [System.IO.File]::WriteAllLines($h, $lines); }"
echo   [+] Arquivo HOSTS restaurado [sites de AV liberados].

:: -------------------------------------------------------
:: 9. DESINFECTAR INJECAO NO DISCORD [INDEX.JS]
:: -------------------------------------------------------
echo.
echo [*] 9. Limpando injecao de backdoor no Discord...
powershell -NoProfile -ExecutionPolicy Bypass -Command "@('Discord', 'DiscordCanary', 'DiscordPTB', 'DiscordDevelopment') | ForEach-Object { $base = Join-Path $env:LOCALAPPDATA $_; if (Test-Path $base) { Get-ChildItem -Path $base -Filter 'index.js' -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.DirectoryName -like '*discord_desktop_core*' } | ForEach-Object { $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue; if ($content -and $content.Trim() -ne \"module.exports = require('./core.asar');\") { Set-ItemProperty -LiteralPath $_.FullName -Name IsReadOnly -Value $false -ErrorAction SilentlyContinue; Set-Content -LiteralPath $_.FullName -Value \"module.exports = require('./core.asar');\" -Encoding utf8 -Force; Write-Host \"      [+] Desinfectado: $($_.FullName)\"; } } } };"
echo   [+] Nucleo do Discord inspecionado e restaurado.

:: -------------------------------------------------------
:: 10. RESTAURAR WINDOWS DEFENDER E REMOVER EXCLUSOES
:: -------------------------------------------------------
echo.
echo [*] 10. Restaurando Microsoft Defender e removendo exclusoes maliciosas...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $perm = Join-Path $env:APPDATA 'Microsoft\Network\Connections\pbk'; $edge = Join-Path $env:LOCALAPPDATA 'Microsoft\EdgeUpdate\Download'; $temp = $env:TEMP; $mp = Get-MpPreference -ErrorAction SilentlyContinue; if ($mp) { foreach ($ex in @($perm, $edge, $temp)) { Remove-MpPreference -ExclusionPath $ex -ErrorAction SilentlyContinue; } foreach ($proc in @('chromelevator_x64.exe', 'elevator_payload.exe', 'msoobe_', 'svchost.exe')) { Remove-MpPreference -ExclusionProcess $proc -ErrorAction SilentlyContinue; } } Set-MpPreference -DisableRealtimeMonitoring $false -DisableIOAVProtection $false -DisableScriptScanning $false -DisableIntrusionPreventionSystem $false -EnableControlledFolderAccess Enabled -EnableNetworkProtection Enabled -MAPSReporting Advanced -SubmitSamplesConsent SendAllSamples -ErrorAction SilentlyContinue; } catch {}"
echo   [+] Windows Defender reconfigurado com protecao maxima.

:: -------------------------------------------------------
:: 11. VERIFICACAO FINAL DE STATUS
:: -------------------------------------------------------
echo.
echo =======================================================
echo                 RELATORIO DE AUDITORIA
echo =======================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "$allClean = $true; $pbk = Join-Path $env:APPDATA 'Microsoft\Network\Connections\pbk'; if (Test-Path -LiteralPath $pbk) { Write-Host '  [X] Pasta PBK ainda presente!' -ForegroundColor Red; $allClean = $false; } else { Write-Host '  [OK] Pasta de persistencia PBK: REMOVIDA' -ForegroundColor Green; }; $task = Get-ScheduledTask -TaskName 'MicrosoftNetworkSync' -ErrorAction SilentlyContinue; if ($task) { Write-Host '  [X] Tarefa Agendada ainda ativa!' -ForegroundColor Red; $allClean = $false; } else { Write-Host '  [OK] Tarefa Agendada MicrosoftNetworkSync: REMOVIDA' -ForegroundColor Green; }; $proc = Get-Process -ErrorAction SilentlyContinue | Where-Object { try { $_.Path -and ($_.Path.StartsWith($pbk, [System.StringComparison]::OrdinalIgnoreCase)) } catch { $false } }; if ($proc) { Write-Host '  [X] Processos de persistencia ainda em execucao!' -ForegroundColor Red; $allClean = $false; } else { Write-Host '  [OK] Processos maliciosos: NENHUM DETECTADO' -ForegroundColor Green; }; if ($allClean) { Write-Host ''; Write-Host '>>> SISTEMA 100%% LIMPO E DESINFECTADO COM SUCESSO! <<<' -ForegroundColor Green; } else { Write-Host ''; Write-Host '>>> ALGUNS ITENS EXIGEM ATENCAO (VEJA ACIMA) <<<' -ForegroundColor Yellow; }"

echo =======================================================
echo.
pause