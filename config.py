import os
import secrets

# Controle de versão incremental: principal.atualização.contagem.
APP_VERSION_MAJOR = 1
APP_VERSION_UPDATE = 4
APP_VERSION_COUNT = 8
APP_VERSION = f"{APP_VERSION_MAJOR}.{APP_VERSION_UPDATE}.{APP_VERSION_COUNT}"
APP_VERSION_COMPONENT_LIMIT = 99


def proxima_versao(principal, atualizacao, contagem):
    """Retorna a próxima versão aplicando transporte ao ultrapassar 99."""
    componentes = (principal, atualizacao, contagem)
    if any(not isinstance(item, int) or item < 0 for item in componentes):
        raise ValueError("Os componentes da versão devem ser inteiros não negativos.")

    contagem += 1
    if contagem > APP_VERSION_COMPONENT_LIMIT:
        contagem = 0
        atualizacao += 1
    if atualizacao > APP_VERSION_COMPONENT_LIMIT:
        atualizacao = 0
        principal += 1
    return principal, atualizacao, contagem


def obter_secret_key_local(base_dir):
    """Obtém uma chave persistente local sem expô-la no repositório.

    Em produção, `SECRET_KEY` deve ser definida no ambiente. Este fallback
    atende instalações locais e evita gerar uma chave diferente a cada reinício.
    """
    secret_path = os.path.join(base_dir, "instance", ".secret_key")
    if os.path.exists(secret_path):
        with open(secret_path, "r", encoding="utf-8") as secret_file:
            secret_key = secret_file.read().strip()
        if secret_key:
            return secret_key

    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    secret_key = secrets.token_urlsafe(48)
    try:
        descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        with open(secret_path, "r", encoding="utf-8") as secret_file:
            secret_key = secret_file.read().strip()
        if secret_key:
            return secret_key
        raise RuntimeError("O arquivo local de SECRET_KEY existe, mas está vazio.")

    with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
        secret_file.write(secret_key)
    return secret_key

class Config:
    APP_VERSION = APP_VERSION
    # A variável de ambiente tem prioridade. Sem ela, create_app() cria uma
    # chave local persistente em instance/.secret_key, ignorada pelo Git.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    IMPORTAR_LOGRADOUROS_INICIAIS = os.environ.get("IMPORTAR_LOGRADOUROS_INICIAIS") == "1"
