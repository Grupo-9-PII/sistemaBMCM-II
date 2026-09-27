from pathlib import Path

import requests
import pyzipper

from .google_oauth import GOOGLE_DRIVE_FILE_SCOPE, get_access_token, has_scope

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_BACKUP_FOLDER_NAME = "BMCM Backups"
DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
BACKUP_MIME_TYPE = "application/zip"


def _headers(content_type=None):
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _listar_arquivos(query, fields):
    arquivos = []
    page_token = None
    while True:
        params = {
            "q": query,
            "fields": f"nextPageToken,files({fields})",
            "pageSize": 100,
            "spaces": "drive",
        }
        if page_token:
            params["pageToken"] = page_token
        response = requests.get(
            DRIVE_FILES_URL,
            headers=_headers(),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        page = response.json()
        arquivos.extend(page.get("files", []))
        page_token = page.get("nextPageToken")
        if not page_token:
            return arquivos


def _localizar_pasta_backups():
    pastas = _listar_arquivos(
        "name = 'BMCM Backups' and "
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        "id,name",
    )
    return pastas[0]["id"] if pastas else None


def _obter_ou_criar_pasta_backups():
    pasta_id = _localizar_pasta_backups()
    if pasta_id:
        return pasta_id

    response = requests.post(
        DRIVE_FILES_URL,
        headers=_headers("application/json"),
        params={"fields": "id,name"},
        json={"name": DRIVE_BACKUP_FOLDER_NAME, "mimeType": DRIVE_FOLDER_MIME_TYPE},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def _validar_arquivo_backup(caminho_backup):
    path = Path(caminho_backup)
    if not path.is_file():
        raise FileNotFoundError("Arquivo de backup não encontrado.")
    if not path.name.startswith("backup_") or path.suffix.lower() != ".zip":
        raise ValueError("Somente arquivos ZIP de backup BMCM podem ser enviados.")
    return path


def enviar_backup_para_drive(caminho_backup):
    if not has_scope(GOOGLE_DRIVE_FILE_SCOPE):
        raise RuntimeError("Autorize o escopo Google Drive nas configurações do sistema.")

    path = _validar_arquivo_backup(caminho_backup)
    try:
        with pyzipper.AESZipFile(path, "r") as archive:
            info = archive.getinfo("database.db")
    except (KeyError, OSError, pyzipper.BadZipFile) as exc:
        raise ValueError("O arquivo não é um backup BMCM válido.") from exc
    if not info.flag_bits & 0x1:
        raise ValueError(
            "Este backup antigo não está criptografado. Crie um novo backup AES-256 antes de enviá-lo ao Drive."
        )

    pasta_id = _obter_ou_criar_pasta_backups()
    arquivos = _listar_arquivos(
        f"'{pasta_id}' in parents and name = '{path.name}' and trashed = false",
        "id,name,modifiedTime,size,webViewLink",
    )
    arquivo_existente = arquivos[0] if arquivos else None
    criado_agora = arquivo_existente is None

    if arquivo_existente:
        arquivo_id = arquivo_existente["id"]
    else:
        response = requests.post(
            DRIVE_FILES_URL,
            headers=_headers("application/json"),
            params={"fields": "id,name,modifiedTime,size,webViewLink"},
            json={
                "name": path.name,
                "mimeType": BACKUP_MIME_TYPE,
                "parents": [pasta_id],
            },
            timeout=30,
        )
        response.raise_for_status()
        arquivo_existente = response.json()
        arquivo_id = arquivo_existente["id"]

    try:
        with path.open("rb") as backup_file:
            response = requests.patch(
                f"{DRIVE_UPLOAD_URL}/{arquivo_id}",
                headers=_headers(BACKUP_MIME_TYPE),
                params={"uploadType": "media", "fields": "id,name,modifiedTime,size,webViewLink"},
                data=backup_file,
                timeout=120,
            )
        response.raise_for_status()
    except (OSError, requests.RequestException):
        if criado_agora:
            try:
                requests.delete(
                    f"{DRIVE_FILES_URL}/{arquivo_id}",
                    headers=_headers(),
                    timeout=20,
                )
            except requests.RequestException:
                pass
        raise

    uploaded = response.json() if response.content else {}
    return {**arquivo_existente, **uploaded, "id": arquivo_id, "name": path.name}


def listar_backups_drive():
    if not has_scope(GOOGLE_DRIVE_FILE_SCOPE):
        raise RuntimeError("Autorize o escopo Google Drive nas configurações do sistema.")

    pasta_id = _localizar_pasta_backups()
    if not pasta_id:
        return []

    return _listar_arquivos(
        f"'{pasta_id}' in parents and trashed = false and mimeType = '{BACKUP_MIME_TYPE}'",
        "id,name,modifiedTime,size,webViewLink",
    )
