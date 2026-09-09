"""
Módulo de backup e restauração do banco de dados SQLite.
Utiliza compactação ZIP para cópias locais do banco de dados.
"""

import os
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from flask import current_app

# Mantida por compatibilidade com chamadas existentes; o ZIP não é criptografado.
SENHA_BACKUP_PADRAO = "SISTBMCM2024"

# Nome da subpasta de backups na pasta do usuário
PASTA_BACKUP = "BKPSISTBMCM"


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
            backups.append({
                "nome": arquivo,
                "caminho": caminho,
                "data": datetime.fromtimestamp(stat.st_mtime),
                "tamanho_bytes": stat.st_size,
                "tamanho_formatado": formatar_tamanho(stat.st_size),
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


def criar_backup(caminho_db):
    """
    Cria um backup compactado do banco de dados.
    Retorna o caminho do arquivo de backup criado.
    """
    if not os.path.exists(caminho_db):
        raise FileNotFoundError(f"Banco de dados não encontrado: {caminho_db}")

    pasta_backup = obter_pasta_backup_usuario()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"backup_{timestamp}.zip"
    caminho_backup = os.path.join(pasta_backup, nome_backup)

    # O módulo zipfile padrão não oferece criptografia AES.
    with zipfile.ZipFile(caminho_backup, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(caminho_db, arcname="database.db")

    return caminho_backup


def validar_backup(caminho_backup):
    """Valida se o arquivo de backup é um ZIP válido."""
    try:
        with zipfile.ZipFile(caminho_backup, "r") as zf:
            if "database.db" not in zf.namelist():
                return False, "Arquivo de backup inválido: database.db não encontrado."
            return True, "Backup válido."
    except zipfile.BadZipFile:
        return False, "Arquivo de backup inválido ou corrompido."


def restaurar_backup(caminho_backup, caminho_db, senha=None):
    """
    Restaura o banco de dados a partir de um backup.
    Faz cópia de segurança do DB atual antes de restaurar.
    Retorna (sucesso, mensagem).
    """
    if senha is None:
        senha = SENHA_BACKUP_PADRAO

    # Validar backup
    valido, msg = validar_backup(caminho_backup)
    if not valido:
        return False, msg

    # Criar cópia de segurança do DB atual
    if os.path.exists(caminho_db):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta_backup = obter_pasta_backup_usuario()
        nome_seguranca = f"database_pre_restore_{timestamp}.db"
        caminho_seguranca = os.path.join(pasta_backup, nome_seguranca)
        shutil.copy2(caminho_db, caminho_seguranca)

    # Extrair backup
    try:
        with zipfile.ZipFile(caminho_backup, "r") as zf:
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
    except Exception as e:
        return False, f"Erro ao restaurar backup: {str(e)}"


def excluir_backup(caminho_backup):
    """Exclui um arquivo de backup."""
    try:
        os.remove(caminho_backup)
        return True, "Backup excluído com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir backup: {str(e)}"

