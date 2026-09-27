"""
Módulo de backup e restauração do banco de dados SQLite.
Utiliza compactação ZIP para cópias locais do banco de dados.
"""

import os
import secrets
import zipfile
import shutil
from datetime import datetime
from pathlib import Path

import pyzipper
from flask import current_app

# Nome da subpasta de backups na pasta do usuário
PASTA_BACKUP = "BKPSISTBMCM"


def obter_senha_backup(criar=True):
    """Obtém a senha configurada ou cria uma chave local persistente."""
    try:
        senha = current_app.config.get("BACKUP_PASSWORD")
        base_dir = current_app.config.get("BASE_DIR")
    except RuntimeError:
        senha = os.environ.get("BACKUP_PASSWORD")
        base_dir = os.getcwd()

    if senha:
        if len(senha) < 16:
            raise ValueError("BACKUP_PASSWORD deve ter pelo menos 16 caracteres.")
        return senha

    senha_path = Path(base_dir or os.getcwd()) / "instance" / ".backup_password"
    if senha_path.is_file():
        senha = senha_path.read_text(encoding="utf-8").strip()
        if len(senha) < 16:
            raise RuntimeError("A chave local de backup está inválida.")
        os.chmod(senha_path, 0o600)
        return senha
    if not criar:
        return None

    senha_path.parent.mkdir(parents=True, exist_ok=True)
    senha = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(
            senha_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
    except FileExistsError:
        senha = senha_path.read_text(encoding="utf-8").strip()
        if len(senha) < 16:
            raise RuntimeError("A chave local de backup está inválida.")
        os.chmod(senha_path, 0o600)
        return senha
    with os.fdopen(descriptor, "w", encoding="utf-8") as password_file:
        password_file.write(senha)
    return senha


def obter_caminho_backup(nome_backup):
    """Retorna um caminho de backup válido dentro da pasta configurada."""
    if not nome_backup or os.path.basename(nome_backup) != nome_backup:
        return None
    if not nome_backup.startswith("backup_") or not nome_backup.endswith(".zip"):
        return None

    pasta_backup = Path(obter_pasta_backup_usuario()).resolve()
    caminho_backup = (pasta_backup / nome_backup).resolve()
    if caminho_backup.parent != pasta_backup or not caminho_backup.is_file():
        return None
    return str(caminho_backup)


def obter_pasta_backup_usuario():
    """Retorna o caminho absoluto da pasta de backups do usuário."""
    pasta_backup = None
    try:
        pasta_backup = current_app.config.get("BACKUP_FOLDER")
    except RuntimeError:
        pasta_backup = None

    if pasta_backup:
        pasta = Path(pasta_backup)
        if not pasta.is_absolute():
            pasta = Path(current_app.root_path) / pasta_backup
    else:
        home = Path.home()
        pasta = home / PASTA_BACKUP

    pasta.mkdir(parents=True, exist_ok=True)
    return str(pasta)


def listar_backups():
    """Lista todos os backups disponíveis ordenados por data (mais recente primeiro)."""
    pasta = obter_pasta_backup_usuario()
    backups = []
    for arquivo in os.listdir(pasta):
        if arquivo.startswith("backup_") and arquivo.endswith(".zip"):
            caminho = os.path.join(pasta, arquivo)
            stat = os.stat(caminho)
            try:
                with pyzipper.AESZipFile(caminho, "r") as archive:
                    encrypted = bool(archive.getinfo("database.db").flag_bits & 0x1)
            except (KeyError, OSError, zipfile.BadZipFile, pyzipper.BadZipFile):
                encrypted = False
            backups.append({
                "nome": arquivo,
                "caminho": caminho,
                "data": datetime.fromtimestamp(stat.st_mtime),
                "tamanho_bytes": stat.st_size,
                "tamanho_formatado": formatar_tamanho(stat.st_size),
                "criptografado": encrypted,
            })
    backups.sort(key=lambda x: x["data"], reverse=True)
    return backups


def formatar_tamanho(bytes_tamanho):
    """Formata bytes para KB, MB, etc."""
    for unidade in ["B", "KB", "MB", "GB"]:
        if bytes_tamanho < 1024:
            return f"{bytes_tamanho:.1f} {unidade}"
        bytes_tamanho /= 1024
    return f"{bytes_tamanho:.1f} TB"


def criar_backup(caminho_db, senha=None):
    """
    Cria um backup compactado do banco de dados.
    Retorna o caminho do arquivo de backup criado.
    """
    if not os.path.exists(caminho_db):
        raise FileNotFoundError(f"Banco de dados não encontrado: {caminho_db}")
    senha = senha or obter_senha_backup()

    pasta_backup = obter_pasta_backup_usuario()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    nome_backup = f"backup_{timestamp}.zip"
    caminho_backup = os.path.join(pasta_backup, nome_backup)

    with pyzipper.AESZipFile(
        caminho_backup,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(senha.encode("utf-8"))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        zf.write(caminho_db, arcname="database.db")
    os.chmod(caminho_backup, 0o600)

    return caminho_backup


def validar_backup(caminho_backup, senha=None):
    """Valida se o arquivo de backup é um ZIP válido."""
    try:
        with pyzipper.AESZipFile(caminho_backup, "r") as zf:
            if "database.db" not in zf.namelist():
                return False, "Arquivo de backup inválido: database.db não encontrado."
            info = zf.getinfo("database.db")
            if info.flag_bits & 0x1:
                senha = senha or obter_senha_backup(criar=False)
                if not senha:
                    return False, "A senha de proteção deste backup não está configurada."
                zf.setpassword(senha.encode("utf-8"))
            arquivo_corrompido = zf.testzip()
            if arquivo_corrompido:
                return False, "Arquivo de backup inválido ou corrompido."
            return True, "Backup válido."
    except RuntimeError:
        return False, "Senha incorreta ou arquivo de backup corrompido."
    except (zipfile.BadZipFile, OSError):
        return False, "Arquivo de backup inválido ou corrompido."


def restaurar_backup(caminho_backup, caminho_db, senha=None):
    """
    Restaura o banco de dados a partir de um backup.
    Faz cópia de segurança do DB atual antes de restaurar.
    Retorna (sucesso, mensagem).
    """
    if senha is None:
        senha = obter_senha_backup(criar=False)

    # Validar backup
    valido, msg = validar_backup(caminho_backup, senha)
    if not valido:
        return False, msg

    # Preserve o banco atual em um ZIP criptografado antes da restauração.
    if os.path.exists(caminho_db):
        criar_backup(caminho_db, senha=senha or obter_senha_backup())

    # Extrair backup
    try:
        with pyzipper.AESZipFile(caminho_backup, "r") as zf:
            info = zf.getinfo("database.db")
            if info.flag_bits & 0x1:
                zf.setpassword(senha.encode("utf-8"))
            # Extrair para pasta temporária primeiro
            pasta_temp = os.path.join(os.path.dirname(caminho_db), "temp_restore")
            os.makedirs(pasta_temp, exist_ok=True)
            zf.extract("database.db", path=pasta_temp)

            # Mover para o local correto
            caminho_temp_db = os.path.join(pasta_temp, "database.db")
            shutil.move(caminho_temp_db, caminho_db)

            # Limpar pasta temporária
            shutil.rmtree(pasta_temp, ignore_errors=True)

        return True, "Backup restaurado com sucesso."
    except Exception:
        current_app.logger.exception("Erro ao restaurar backup")
        return False, "Não foi possível restaurar o backup. Verifique o log do sistema."


def excluir_backup(caminho_backup):
    """Exclui um arquivo de backup."""
    try:
        os.remove(caminho_backup)
        return True, "Backup excluído com sucesso."
    except Exception as e:
        current_app.logger.exception("Erro ao excluir backup")
        return False, "Não foi possível excluir o backup. Verifique o log do sistema."

