from datetime import date
from pathlib import Path

import pytest
import requests
import pyzipper
import zipfile
from dotenv import dotenv_values
from sqlalchemy import text

import app.utils as utils
import app.routes as routes
import app.google_calendar as google_calendar
import app.google_drive as google_drive
import app.google_oauth as google_oauth
import app.backup as backup
from app import create_app, db
from app.models import Aluno, Ensaio, Presenca, User, Comunicacao, ComunicacaoDestinatario, Responsavel, Evento, Naipe, Instrumento, AlunoInstrumento, ContatoComunicacao, SistemaConfig, GoogleCalendarSync
from config import Config, obter_secret_key_local, proxima_versao


def test_incremento_de_versao_com_transporte():
    assert proxima_versao(1, 4, 6) == (1, 4, 7)
    assert proxima_versao(1, 4, 99) == (1, 5, 0)
    assert proxima_versao(1, 99, 99) == (2, 0, 0)


def test_secret_key_local_eh_persistente(tmp_path):
    primeira_chave = obter_secret_key_local(str(tmp_path))
    segunda_chave = obter_secret_key_local(str(tmp_path))

    assert primeira_chave == segunda_chave
    assert len(primeira_chave) >= 32
    assert (tmp_path / "instance" / ".secret_key").is_file()


def _csrf_token(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["csrf_token"]


def _login_admin(client):
    token = _csrf_token(client)
    utils._LOGIN_TENTATIVAS_IP.clear()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "123456", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return token


def _autorizar_google_workspace_em_teste(monkeypatch):
    monkeypatch.setattr(
        routes,
        "google_workspace_status",
        lambda sender_email: {
            "available": True,
            "sender_valid": True,
            "oauth_valid": True,
            "oauth_error": None,
            "reason": "Integrações Google disponíveis.",
        },
    )


def test_inicializacao_limpa_e_protecoes_criticas(monkeypatch):
    """Banco novo deve iniciar e ações mutáveis devem exigir POST com CSRF."""
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    # O parser da base de CEP é validado na inicialização manual; aqui evitamos
    # carregar o arquivo de referência para manter o teste de segurança rápido.
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    with app.app_context():
        assert db.session.execute(text("SELECT COUNT(*) FROM cidade")).scalar() == 0
        assert db.session.execute(text("SELECT COUNT(*) FROM logradouro")).scalar() == 0

        operador = User(username="operador", is_admin=False, must_change_password=False)
        operador.set_password("Senha123!")
        db.session.add(operador)
        db.session.commit()
        operador_id = operador.id

    token = _login_admin(client)

    assert client.get(f"/admin/toggle-user/{operador_id}").status_code == 405
    assert client.post(f"/admin/toggle-user/{operador_id}").status_code == 400
    assert client.post(
        f"/admin/toggle-user/{operador_id}", data={"csrf_token": token}
    ).status_code == 302

    with app.app_context():
        assert db.session.get(User, operador_id).is_active is False

        aluno = Aluno(nome="INTEGRANTE DE TESTE", ativo=True)
        ensaio = Ensaio(titulo="ENSAIO", data_ensaio=date(2026, 9, 9))
        db.session.add_all([aluno, ensaio])
        db.session.commit()
        db.session.add(Presenca(aluno_id=aluno.id, ensaio_id=ensaio.id, presente=True))
        db.session.commit()

        # Os índices parciais preservam a regra de uma chamada por atividade.
        indices = {
            linha[1]
            for linha in db.session.execute(text("PRAGMA index_list('presenca')")).all()
        }
        assert {"uq_presenca_aluno_ensaio", "uq_presenca_aluno_evento"} <= indices


def test_central_de_comunicacoes_cria_mensagem_e_status_inicial(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Aviso de ensaio",
            "mensagem": "Reforço do ensaio de sábado.",
            "tipo": "aviso",
            "publico": "geral",
            "canal": "email",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.first()
        assert comunicacao is not None
        assert comunicacao.assunto == "Aviso de ensaio"
        assert comunicacao.status == "rascunho"
        assert comunicacao.destinatarios.count() == 0

        destinatario = ComunicacaoDestinatario(
            comunicacao_id=comunicacao.id,
            tipo_destinatario="integrante",
            destinatario_id=1,
            status="pendente",
            canal="email",
        )
        db.session.add(destinatario)
        db.session.commit()

        assert ComunicacaoDestinatario.query.count() == 1


def test_central_de_comunicacoes_exibe_destinatarios_e_historico(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="Aluno de teste", ativo=True, email="aluno@teste.com")
        db.session.add(aluno)
        db.session.commit()

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Reunião",
            "mensagem": "Mensagem para a equipe.",
            "tipo": "informativo",
            "publico": "geral",
            "canal": "email",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        assert comunicacao is not None
        assert comunicacao.destinatarios.count() == 0

    response = client.post(
        f"/admin/comunicacoes/{comunicacao.id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        db.session.add(SistemaConfig(key="communication_sender_email", value="comunicacao@bandamarilia.org.br"))
        db.session.commit()

    response = client.get(f"/admin/comunicacoes/{comunicacao.id}")
    assert response.status_code == 200
    assert "Aluno de teste".encode("utf-8") in response.data
    assert "comunicacao@bandamarilia.org.br".encode("utf-8") in response.data
    assert "Histórico".encode("utf-8") in response.data


def test_central_de_comunicacoes_suporta_publico_responsaveis_e_vinculo_atividade(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="Aluno responsável", ativo=True, email="aluno@teste.com")
        db.session.add(aluno)
        db.session.commit()
        responsavel = Responsavel(
            aluno_id=aluno.id,
            nome_pai="Maria da Silva",
            email="responsavel@teste.com",
            telefone="(11) 99999-0000",
        )
        db.session.add(responsavel)
        ensaio = Ensaio(titulo="Ensaio final", data_ensaio=date(2026, 10, 18), local="Ginásio")
        evento = Evento(nome_evento="Apresentação municipal", data_evento=date(2026, 10, 20), cidade="Marília")
        db.session.add_all([responsavel, ensaio, evento])
        db.session.commit()

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Aviso para responsáveis",
            "mensagem": "Mensagem para a família.",
            "tipo": "informativo",
            "publico": "responsaveis",
            "canal": "email",
            "evento_id": "1",
            "ensaio_id": "1",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        assert comunicacao is not None
        assert comunicacao.publico == "responsaveis"
        assert comunicacao.evento_id is not None
        assert comunicacao.ensaio_id is not None

    response = client.post(
        f"/admin/comunicacoes/{comunicacao.id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao.id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].tipo_destinatario == "responsavel"
        assert destinatarios[0].destinatario_id == 1
        assert destinatarios[0].status == "enviado"


def test_central_de_comunicacoes_suporta_publico_naipe(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    with app.app_context():
        naipe = Naipe(nome="Metais")
        db.session.add(naipe)
        db.session.commit()
        instrumento = Instrumento(nome="Trompete", naipe_id=naipe.id)
        db.session.add(instrumento)
        aluno = Aluno(nome="Aluno naipe", ativo=True, email="naipe@teste.com")
        db.session.add(aluno)
        db.session.commit()
        db.session.add(AlunoInstrumento(aluno_id=aluno.id, instrumento_id=instrumento.id))
        db.session.commit()

    with app.app_context():
        naipe = Naipe.query.order_by(Naipe.id.desc()).first()
        assert naipe is not None
        naipe_id = str(naipe.id)

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Instruções do naipe",
            "mensagem": "Mensagem específica para os metais.",
            "tipo": "informativo",
            "publico": "naipe",
            "naipe_id": naipe_id,
            "canal": "email",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        assert comunicacao is not None
        assert comunicacao.publico == "naipe"

    response = client.post(
        f"/admin/comunicacoes/{comunicacao.id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao.id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].tipo_destinatario == "integrante"
        assert destinatarios[0].status == "enviado"


def test_central_de_comunicacoes_suporta_publico_externo(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    with app.app_context():
        contato = ContatoComunicacao(
            nome="Setor de Cultura",
            email="cultura@prefeitura.gov.br",
            telefone="(14) 3321-0000",
            observacoes="Órgão externo",
            ativo=True,
        )
        db.session.add(contato)
        db.session.commit()

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Contato institucional",
            "mensagem": "Mensagem para a prefeitura.",
            "tipo": "informativo",
            "publico": "externo",
            "canal": "email",
            "contato_email": "cultura@prefeitura.gov.br",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        assert comunicacao is not None
        assert comunicacao.publico == "externo"
        assert comunicacao.destinatario_email == "cultura@prefeitura.gov.br"
        assert comunicacao.contato_externo_id == 1

    response = client.post(
        f"/admin/comunicacoes/{comunicacao.id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao.id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].tipo_destinatario == "contato_externo"
        assert destinatarios[0].destinatario_id == 1
        assert destinatarios[0].status == "enviado"


def test_central_de_comunicacoes_exclui_apenas_rascunho_sem_log(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    with app.app_context():
        comunicacao = Comunicacao(
            assunto="Rascunho descartável",
            mensagem="Não deve ser enviado.",
            publico="externo",
            criado_por_id=1,
        )
        db.session.add(comunicacao)
        db.session.commit()
        comunicacao_id = comunicacao.id

    response = client.post(
        f"/admin/comunicacoes/{comunicacao_id}/excluir",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(Comunicacao, comunicacao_id) is None
        assert ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao_id).count() == 0


def test_central_de_comunicacoes_permite_email_externo_avulso(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)

    token = _csrf_token(client)
    _login_admin(client)

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Convite institucional",
            "mensagem": "Convite para apresentação.",
            "tipo": "convite",
            "publico": "externo",
            "canal": "email",
            "destinatario_nome": "Secretaria de Educação",
            "destinatario_email": "educacao@outra-prefeitura.gov.br",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        comunicacao_id = comunicacao.id
        assert comunicacao.destinatario_nome == "Secretaria de Educação"
        assert comunicacao.destinatario_email == "educacao@outra-prefeitura.gov.br"

    response = client.post(
        f"/admin/comunicacoes/{comunicacao_id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao_id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].destinatario_id == 0
        assert destinatarios[0].destinatario_email == "educacao@outra-prefeitura.gov.br"


def _criar_app_calendar_teste(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)
    app = create_app()
    app.config.update(TESTING=True)
    monkeypatch.setattr(google_calendar, "has_scope", lambda scope: True)
    monkeypatch.setattr(google_calendar, "get_access_token", lambda: "calendar-test-token")
    return app


def _criar_backup_zip_aes(caminho):
    with pyzipper.AESZipFile(
        caminho,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as archive:
        archive.setpassword(b"senha-segura-de-teste")
        archive.setencryption(pyzipper.WZ_AES, nbits=256)
        archive.writestr("database.db", b"backup teste")
    return caminho


def test_google_calendar_sincroniza_atualizacao_e_cancelamento_sem_duplicar(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    chamadas = {"post": [], "patch": []}

    class RespostaGoogle:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": chamadas["post"][0][1]["json"]["id"]}

    def post(url, **kwargs):
        chamadas["post"].append((url, kwargs))
        return RespostaGoogle()

    def patch(url, **kwargs):
        chamadas["patch"].append((url, kwargs))
        return RespostaGoogle()

    monkeypatch.setattr(google_calendar.requests, "post", post)
    monkeypatch.setattr(google_calendar.requests, "patch", patch)

    with app.app_context():
        ensaio = Ensaio(
            titulo="Ensaio de teste",
            data_ensaio=date(2026, 10, 5),
            horario="19:30",
            local="Ginásio",
            observacoes="Levar estantes.",
        )
        db.session.add(ensaio)
        db.session.commit()

        assert google_calendar.sincronizar_atividade("ensaio", ensaio) is True
        sync = GoogleCalendarSync.query.filter_by(ensaio_id=ensaio.id).one()
        event_id = sync.google_event_id
        payload = chamadas["post"][0][1]["json"]
        assert payload["id"] == event_id
        assert payload["start"]["dateTime"].endswith("-03:00")
        assert payload["end"]["dateTime"].endswith("-03:00")

        ensaio.titulo = "Ensaio atualizado"
        assert google_calendar.sincronizar_atividade("ensaio", ensaio) is True
        assert chamadas["patch"][-1][0].endswith(event_id)
        assert chamadas["patch"][-1][1]["json"]["summary"] == "Ensaio atualizado"
        assert "id" not in chamadas["patch"][-1][1]["json"]

        ensaio.status = "CANCELADO"
        assert google_calendar.sincronizar_atividade("ensaio", ensaio) is True
        assert chamadas["patch"][-1][1]["json"]["status"] == "cancelled"
        assert GoogleCalendarSync.query.filter_by(ensaio_id=ensaio.id).count() == 1


def test_google_calendar_evento_usa_dia_inteiro_e_recusa_escopo_ausente(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    with app.app_context():
        evento = Evento(
            nome_evento="Apresentação",
            data_evento=date(2026, 10, 12),
            cidade="Marília",
        )
        db.session.add(evento)
        db.session.commit()

        payload = google_calendar._activity_payload("evento", evento)
        assert payload["start"] == {"date": "2026-10-12"}
        assert payload["end"] == {"date": "2026-10-13"}
        assert payload["location"] == "Marília"

        monkeypatch.setattr(google_calendar, "has_scope", lambda scope: False)
        with pytest.raises(RuntimeError, match="escopo do Google Calendar"):
            google_calendar.sincronizar_atividade("evento", evento)


def test_google_oauth_solicita_escopos_dos_servicos_integrados(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "teste.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "segredo-de-teste")
    monkeypatch.setenv(
        "GOOGLE_OAUTH_SCOPES",
        " ".join(
            (
                google_oauth.GMAIL_SEND_SCOPE,
                google_oauth.GOOGLE_CALENDAR_EVENTS_SCOPE,
                google_oauth.GOOGLE_DRIVE_FILE_SCOPE,
            )
        ),
    )

    scopes = google_oauth.google_oauth_config()["scopes"]

    assert set(scopes) == {
        google_oauth.GMAIL_SEND_SCOPE,
        google_oauth.GOOGLE_CALENDAR_EVENTS_SCOPE,
        google_oauth.GOOGLE_DRIVE_FILE_SCOPE,
    }

    monkeypatch.delenv("GOOGLE_OAUTH_SCOPES")
    assert set(google_oauth.google_oauth_config()["scopes"]) == set(scopes)


def test_rota_de_sincronizacao_calendar_exige_login_e_csrf(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    token = _login_admin(client)

    with app.app_context():
        ensaio = Ensaio(titulo="Ensaio da rota", data_ensaio=date(2026, 10, 20))
        db.session.add(ensaio)
        db.session.commit()
        ensaio_id = ensaio.id

    sincronizadas = []
    monkeypatch.setattr(
        routes,
        "sincronizar_atividade",
        lambda activity_type, activity: sincronizadas.append(
            (activity_type, activity.id)
        ),
    )

    assert client.get("/admin/ensaios").status_code == 200
    assert client.post(
        f"/admin/ensaio/{ensaio_id}/calendar/sincronizar"
    ).status_code == 400
    response = client.post(
        f"/admin/ensaio/{ensaio_id}/calendar/sincronizar",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert sincronizadas == [("ensaio", ensaio_id)]


def test_menu_exibe_google_calendar_apenas_com_escopo_autorizado(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    monkeypatch.setattr(google_oauth, "has_scope", lambda scope: False)
    _login_admin(client)

    response = client.get("/admin/ensaios")
    assert b"Google Calendar" not in response.data

    monkeypatch.setattr(google_oauth, "has_scope", lambda scope: True)
    response = client.get("/admin/ensaios")
    assert b"Google Calendar" in response.data
    assert b"https://calendar.google.com/calendar/u/0/r" in response.data


def test_google_drive_cria_pasta_e_envia_backup_sem_duplicar(tmp_path, monkeypatch):
    monkeypatch.setattr(google_drive, "has_scope", lambda scope: True)
    monkeypatch.setattr(google_drive, "get_access_token", lambda: "drive-test-token")
    backup_path = tmp_path / "backup_20260927_120000.zip"
    _criar_backup_zip_aes(backup_path)
    chamadas_get = []
    chamadas_post = []
    chamadas_patch = []

    class RespostaGoogle:
        status_code = 200
        content = b"{}"

        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self.body

    def get(url, **kwargs):
        chamadas_get.append((url, kwargs))
        if len(chamadas_get) == 1:
            return RespostaGoogle({"files": []})
        return RespostaGoogle({"files": []})

    def post(url, **kwargs):
        chamadas_post.append((url, kwargs))
        if len(chamadas_post) == 1:
            return RespostaGoogle({"id": "folder-id", "name": "BMCM Backups"})
        return RespostaGoogle({"id": "backup-id", "name": backup_path.name})

    def patch(url, **kwargs):
        chamadas_patch.append((url, kwargs))
        return RespostaGoogle({"id": "backup-id", "size": "12"})

    monkeypatch.setattr(google_drive.requests, "get", get)
    monkeypatch.setattr(google_drive.requests, "post", post)
    monkeypatch.setattr(google_drive.requests, "patch", patch)

    uploaded = google_drive.enviar_backup_para_drive(str(backup_path))

    assert uploaded["id"] == "backup-id"
    assert len(chamadas_get) == 2
    assert len(chamadas_post) == 2
    assert len(chamadas_patch) == 1
    assert chamadas_post[1][1]["json"]["parents"] == ["folder-id"]
    assert chamadas_patch[0][0].endswith("/backup-id")


def test_google_drive_atualiza_arquivo_existente_e_exige_escopo(tmp_path, monkeypatch):
    monkeypatch.setattr(google_drive, "has_scope", lambda scope: True)
    monkeypatch.setattr(google_drive, "get_access_token", lambda: "drive-test-token")
    backup_path = tmp_path / "backup_20260927_120001.zip"
    _criar_backup_zip_aes(backup_path)
    get_count = 0

    class RespostaGoogle:
        status_code = 200
        content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            nonlocal get_count
            get_count += 1
            if get_count == 1:
                return {"files": [{"id": "folder-id", "name": "BMCM Backups"}]}
            return {"files": [{"id": "existing-backup-id", "name": backup_path.name}]}

    patches = []
    monkeypatch.setattr(google_drive.requests, "get", lambda *args, **kwargs: RespostaGoogle())
    monkeypatch.setattr(
        google_drive.requests,
        "patch",
        lambda url, **kwargs: (patches.append(url) or RespostaGoogle()),
    )
    monkeypatch.setattr(google_drive.requests, "post", lambda *args, **kwargs: pytest.fail("Não deve criar duplicata"))

    uploaded = google_drive.enviar_backup_para_drive(str(backup_path))
    assert uploaded["id"] == "existing-backup-id"
    assert patches[0].endswith("/existing-backup-id")

    monkeypatch.setattr(google_drive, "has_scope", lambda scope: False)
    with pytest.raises(RuntimeError, match="escopo Google Drive"):
        google_drive.enviar_backup_para_drive(str(backup_path))


def test_google_drive_recusa_backup_legado_sem_criptografia(tmp_path, monkeypatch):
    monkeypatch.setattr(google_drive, "has_scope", lambda scope: True)
    backup_path = tmp_path / "backup_legacy.zip"
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("database.db", b"dados sem criptografia")

    with pytest.raises(ValueError, match="backup antigo não está criptografado"):
        google_drive.enviar_backup_para_drive(str(backup_path))


def test_rota_backup_drive_exige_csrf_e_preserva_fluxo_local(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    app.config["BACKUP_FOLDER"] = str(tmp_path)
    backup_path = tmp_path / "backup_20260927_120000.zip"
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("database.db", b"backup-local")
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    token = _login_admin(client)
    enviados = []
    monkeypatch.setattr(
        routes,
        "enviar_backup_para_drive",
        lambda path: enviados.append(path) or {"name": backup_path.name},
    )

    painel = client.get("/admin/backup")
    assert painel.status_code == 200
    assert b"Backups no Google Drive" in painel.data
    assert b"Autorize o escopo Google Drive" in painel.data
    assert b"Legado sem criptografia" in painel.data

    assert client.post(
        "/admin/backup/enviar-drive", data={"nome_backup": backup_path.name}
    ).status_code == 400
    response = client.post(
        "/admin/backup/enviar-drive",
        data={"nome_backup": backup_path.name, "csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert enviados == [str(backup_path)]
    assert backup_path.is_file()


def test_painel_backup_lista_drive_e_mostra_falha_de_api(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    app.config["BACKUP_FOLDER"] = str(tmp_path)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    _login_admin(client)
    monkeypatch.setattr(routes, "has_scope", lambda scope: True)
    monkeypatch.setattr(
        routes,
        "listar_backups_drive",
        lambda: [{
            "id": "drive-backup-id",
            "name": "backup_drive.zip",
            "modifiedTime": "2026-09-27T12:00:00.000Z",
            "size": "1200",
            "webViewLink": "https://drive.google.com/file/d/drive-backup-id/view",
        }],
    )

    response = client.get("/admin/backup")
    assert response.status_code == 200
    assert b"backup_drive.zip" in response.data
    assert b"Backups no Google Drive" in response.data

    monkeypatch.setattr(
        routes,
        "listar_backups_drive",
        lambda: (_ for _ in ()).throw(requests.ConnectionError("indisponível")),
    )
    response = client.get("/admin/backup")
    assert response.status_code == 200
    assert b"N\xc3\xa3o foi poss\xc3\xadvel consultar o Google Drive" in response.data


def test_backup_novo_usa_aes256_e_rejeita_senha_incorreta(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    app.config["BASE_DIR"] = str(tmp_path / "app")
    app.config["BACKUP_FOLDER"] = str(tmp_path / "backups")
    app.config["BACKUP_PASSWORD"] = "senha-de-teste-com-mais-de-16"
    database_path = tmp_path / "database.db"
    database_path.write_bytes(b"dados sensiveis de teste")

    with app.app_context():
        archive_path = backup.criar_backup(str(database_path))
        with pyzipper.AESZipFile(archive_path, "r") as archive:
            info = archive.getinfo("database.db")
            assert info.flag_bits & 0x1
            assert info.wz_aes_strength == 3

        assert backup.validar_backup(archive_path)[0] is True
        assert backup.validar_backup(
            archive_path, senha="senha-incorreta"
        ) == (False, "Senha incorreta ou arquivo de backup corrompido.")

        restored_path = tmp_path / "restored.db"
        restored_path.write_bytes(b"banco anterior")
        sucesso, mensagem = backup.restaurar_backup(
            archive_path, str(restored_path)
        )
        assert sucesso is True, mensagem
        assert restored_path.read_bytes() == database_path.read_bytes()
        assert (Path(archive_path).stat().st_mode & 0o777) == 0o600
        safety_archives = list((tmp_path / "backups").glob("backup_*.zip"))
        assert len(safety_archives) == 2
        for safety_archive in safety_archives:
            with pyzipper.AESZipFile(safety_archive, "r") as archive:
                assert archive.getinfo("database.db").flag_bits & 0x1


def test_backup_legacy_sem_criptografia_continua_restauravel(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    app.config["BASE_DIR"] = str(tmp_path / "app")
    app.config["BACKUP_FOLDER"] = str(tmp_path / "backups")
    app.config["BACKUP_PASSWORD"] = None
    legacy_archive = tmp_path / "backup_legacy.zip"
    with zipfile.ZipFile(legacy_archive, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("database.db", b"banco antigo")

    with app.app_context():
        assert backup.validar_backup(str(legacy_archive)) == (True, "Backup válido.")
        restored_path = tmp_path / "restored-legacy.db"
        sucesso, mensagem = backup.restaurar_backup(
            str(legacy_archive), str(restored_path)
        )
        assert sucesso is True, mensagem
        assert restored_path.read_bytes() == b"banco antigo"


def test_senha_backup_padrao_e_persistente_e_com_permissao_restrita(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    app.config["BASE_DIR"] = str(tmp_path / "app")
    app.config["BACKUP_PASSWORD"] = None

    with app.app_context():
        primeira_senha = backup.obter_senha_backup()
        segunda_senha = backup.obter_senha_backup()

    password_path = tmp_path / "app" / "instance" / ".backup_password"
    assert primeira_senha == segunda_senha
    assert len(primeira_senha) >= 32
    assert password_path.read_text(encoding="utf-8") == primeira_senha
    assert (password_path.stat().st_mode & 0o777) == 0o600


def test_configuracoes_registra_e_revela_senha_somente_apos_reautenticacao(
    tmp_path, monkeypatch
):
    app = _criar_app_calendar_teste(monkeypatch)
    base_dir = tmp_path / "app"
    base_dir.mkdir()
    app.config["BASE_DIR"] = str(base_dir)
    app.config["BACKUP_PASSWORD"] = None
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    csrf_token = _login_admin(client)
    password = "senha-de-backup-segura-123"

    settings = client.get("/admin/configuracoes")
    assert settings.status_code == 200
    assert b"backup-password-register-form" in settings.data
    assert password.encode() not in settings.data

    common_data = {
        "backup_password": password,
        "backup_password_confirm": password,
        "csrf_token": csrf_token,
    }
    rejected = client.post(
        "/admin/configuracoes/backup-password/registrar",
        data={**common_data, "admin_password": "incorreta"},
    )
    assert rejected.status_code == 403
    assert password.encode() not in rejected.data

    registered = client.post(
        "/admin/configuracoes/backup-password/registrar",
        data={**common_data, "admin_password": "123456"},
    )
    env_path = base_dir / ".env"
    assert registered.status_code == 200
    assert dotenv_values(env_path)["BACKUP_PASSWORD"] == password
    assert (env_path.stat().st_mode & 0o777) == 0o600
    assert password.encode() not in registered.data

    hidden = client.get("/admin/configuracoes")
    assert password.encode() not in hidden.data
    revealed = client.post(
        "/admin/configuracoes/backup-password/revelar",
        data={"admin_password": "123456", "csrf_token": csrf_token},
    )
    assert revealed.status_code == 200
    assert revealed.json["backup_password"] == password
    assert revealed.headers["Cache-Control"] == "no-store, private"

    for _ in range(5):
        rejected = client.post(
            "/admin/configuracoes/backup-password/revelar",
            data={"admin_password": "incorreta", "csrf_token": csrf_token},
        )
        assert rejected.status_code == 403
    locked = client.post(
        "/admin/configuracoes/backup-password/revelar",
        data={"admin_password": "123456", "csrf_token": csrf_token},
    )
    assert locked.status_code == 429
    assert client.get("/logout").status_code == 302
    csrf_token = _login_admin(client)
    revealed_again = client.post(
        "/admin/configuracoes/backup-password/revelar",
        data={"admin_password": "123456", "csrf_token": csrf_token},
    )
    assert revealed_again.status_code == 200


def test_configuracoes_recusa_trocar_chave_ja_usada(tmp_path, monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    base_dir = tmp_path / "app"
    app.config["BASE_DIR"] = str(base_dir)
    app.config["BACKUP_PASSWORD"] = None
    with app.app_context():
        senha_atual = backup.obter_senha_backup()

    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    csrf_token = _login_admin(client)
    response = client.post(
        "/admin/configuracoes/backup-password/registrar",
        data={
            "admin_password": "123456",
            "backup_password": "outra-senha-segura-123",
            "backup_password_confirm": "outra-senha-segura-123",
            "csrf_token": csrf_token,
        },
    )

    assert response.status_code == 409
    with app.app_context():
        assert senha_atual == backup.obter_senha_backup()
    assert not (base_dir / ".env").exists()
