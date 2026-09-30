import json
import sys
import os

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright nao encontrado. Instalando dependencias automaticamente...")
    os.system("pip install playwright")
    os.system("playwright install chromium")
    from playwright.sync_api import sync_playwright

def load_session(cookie_file, headless_mode=False):
    if not os.path.exists(cookie_file):
        print(f"Erro: Arquivo '{cookie_file}' nao encontrado.")
        return

    with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            cookies = json.load(f)
        except json.JSONDecodeError:
            print("Erro: O arquivo nao é um JSON valido.")
            return

    # Formatar os cookies para o padrao que o Playwright aceita
    pw_cookies = []
    for c in cookies:
        # Pega o dominio de "domain" ou "host" (dependendo do formato do grabber)
        domain = c.get("domain") or c.get("host")
        if not domain:
            continue
            
        pw_cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": domain,
            "path": c.get("path", "/"),
            "secure": c.get("secure", c.get("is_secure", False)),
            "httpOnly": c.get("httpOnly", c.get("is_httponly", False)),
        }
        
        # Ajustar sameSite (Playwright so aceita Strict, Lax, None, ou omite)
        samesite = str(c.get("sameSite", "")).capitalize()
        if samesite in ["Strict", "Lax", "None"]:
            pw_cookie["sameSite"] = samesite
            
        # Playwright rejects invalid expires formats (e.g. Chrome microseconds epoch)
        # So we just ignore them. The cookies will be injected as session cookies.
        pw_cookies.append(pw_cookie)

    print(f"[*] Injetando {len(pw_cookies)} cookies na sessao...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless_mode, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        
        # Injetar um por um para ignorar cookies corrompidos que causariam erro no protocolo
        sucesso = 0
        for ck in pw_cookies:
            # Forcar tipos corretos
            ck["name"] = str(ck["name"])
            ck["value"] = str(ck["value"])
            ck["domain"] = str(ck["domain"])
            ck["path"] = str(ck.get("path", "/"))
            ck["secure"] = bool(ck.get("secure", False))
            ck["httpOnly"] = bool(ck.get("httpOnly", False))
            
            try:
                context.add_cookies([ck])
                sucesso += 1
            except Exception as e:
                print(f"[!] Erro ao injetar cookie {ck['name']} (Dominio: {ck['domain']}): {e}")
                
        print(f"[+] {sucesso} cookies injetados com sucesso de um total de {len(pw_cookies)}!")
        
        page = context.new_page()
        
        # Como o Google tem varios dominios (google.com, google.com.br, youtube.com)
        # Vamos bater na raiz do Google primeiro para assentar os cookies
        print("[*] Acessando google.com para assentar a sessao...")
        page.goto("https://www.google.com/")
        page.wait_for_timeout(2000)
        
        print("[*] Redirecionando para a conta...")
        page.goto("https://myaccount.google.com/")
        
        print("\n[+] SESSAO ESTABELECIDA. Navegador sob seu controle.")
        print("[!] Feche a janela do Playwright Inspector ou o navegador para encerrar o script.")
        
        # Pausa a execucao para o navegador nao fechar sozinho
        page.pause()

if __name__ == "__main__":
    # Aponta pro JSON que voce esta olhando agora
    cookie_path = r"xaitax_output\Brave\Default\cookies.json"
    headless_mode = False
    
    # Se quiser testar outro, so passar como argumento
    for arg in sys.argv[1:]:
        if arg == "--headless":
            headless_mode = True
        else:
            cookie_path = arg
            
    load_session(cookie_path, headless_mode)
