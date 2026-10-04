from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import requests
import pyzipper
import zipfile
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app.utils as utils
import app.routes as routes
import app.google_calendar as google_calendar
import app.google_drive as google_drive
import app.google_oauth as google_oauth
import app.backup as backup
from app import create_app, db
from app.models import Aluno, Atividade, AutorizacaoViagem, CartaoPasse, CotaMensalPasse, Ensaio, MovimentoPasse, Presenca, User, Comunicacao, ComunicacaoDestinatario, Responsavel, Evento, Naipe, Instrumento, AlunoInstrumento, ContatoComunicacao, SistemaConfig, GoogleCalendarSync
from config import Config, obter_secret_key_local, proxima_versao


def test_incremento_de_versao_com_transporte():
    assert proxima_versao(1, 4, 6) == (1, 4, 7)
    assert proxima_versao(1, 4, 99) == (1, 5, 0)
    assert proxima_versao(1, 99, 99) == (2, 0, 0)


def test_dashboard_exibe_indicadores_operacionais(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="INDICADOR", ativo=True)
        atividade = Atividade(
            tipo="TREINAMENTO",
            titulo="Treino do dashboard",
            data_atividade=date.today(),
        )
        db.session.add_all([aluno, atividade])
        db.session.flush()
        db.session.add(Presenca(aluno_id=aluno.id, atividade_id=atividade.id, presente=True))
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Atividades" in response.data
    assert b"Presen\xc3\xa7as" in response.data
    assert b"Hoje" in response.data


def test_calendario_agenda_filtra_registros_e_exibe_status_da_chamada(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="ALUNO CALENDARIO", ativo=True)
        atividade_com_chamada = Atividade(
            tipo="TREINAMENTO",
            titulo="Treino administrativo",
            data_atividade=date(2026, 9, 10),
        )
        atividade_sem_chamada = Atividade(
            tipo="OUTRA",
            titulo="Registro que não deve aparecer",
            data_atividade=date(2026, 9, 11),
        )
        db.session.add_all([aluno, atividade_com_chamada, atividade_sem_chamada])
        db.session.flush()
        db.session.add(
            Presenca(
                aluno_id=aluno.id,
                atividade_id=atividade_com_chamada.id,
                data_presenca=atividade_com_chamada.data_atividade,
                presente=True,
            )
        )
        db.session.commit()

    response = client.get(
        "/admin/calendario?mes=2026-09&visao=agenda&tipo=Atividade&q=administrativo"
    )
    assert response.status_code == 200
    assert b"Treino administrativo" in response.data
    assert b"Registrada" in response.data
    assert b"1 presente(s)" in response.data
    assert b"Registro que n\xc3\xa3o deve aparecer" not in response.data


def test_resumo_mensal_de_presencas_exibe_estatisticas(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="ALUNO RESUMO", ativo=True)
        atividade = Atividade(
            tipo="TREINAMENTO",
            titulo="Resumo mensal",
            data_atividade=date.today(),
        )
        db.session.add_all([aluno, atividade])
        db.session.flush()
        registro = Presenca(aluno_id=aluno.id, atividade_id=atividade.id, presente=True)
        db.session.add(registro)
        db.session.commit()
        registro.presente = False
        db.session.commit()

    response = client.get("/admin/presencas/resumo?mes=2026-09")
    assert response.status_code == 200
    assert b"Resumo mensal de presen\xc3\xa7as" in response.data
    assert b"1" in response.data
    assert b"relatorio-profissional" in response.data


def test_relatorio_profissional_presenca_exibe_resumo_por_aluno_e_atividade(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="ALUNO RELATORIO", ativo=True)
        atividade = Atividade(tipo="TREINAMENTO", titulo="Treino final", data_atividade=date(2026, 9, 10))
        db.session.add_all([aluno, atividade])
        db.session.flush()
        db.session.add(Presenca(aluno_id=aluno.id, atividade_id=atividade.id, presente=True))
        db.session.commit()

    response = client.get("/admin/presencas/relatorio-profissional?mes=2026-09")
    assert response.status_code == 200
    assert b"RELAT\xc3\x93RIO PROFISSIONAL DE PRESEN\xc3\x87A" in response.data
    assert b"ALUNO RELATORIO" in response.data


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
        assert {
            "uq_presenca_aluno_ensaio",
            "uq_presenca_aluno_evento",
            "uq_presenca_aluno_atividade",
        } <= indices


def test_cartao_passe_opcional_e_cota_mensal_administrativa(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        sem_cartao = Aluno(nome="SEM CARTAO", ativo=True)
        com_cartao = Aluno(nome="COM CARTAO", ativo=True)
        db.session.add_all([sem_cartao, com_cartao])
        db.session.flush()
        sem_cartao_id = sem_cartao.id
        com_cartao_id = com_cartao.id
        db.session.add(CartaoPasse(aluno_id=com_cartao.id, numero_controle="CARTAO-001"))
        db.session.commit()

    resposta = client.get("/admin/passes?mes_referencia=2026-09")
    assert resposta.status_code == 200
    assert b"COM CARTAO" in resposta.data
    assert b"SEM CARTAO" in resposta.data
    assert b"sem cart\xc3\xa3o ativo" in resposta.data
    assert f'<option value="{sem_cartao_id}" disabled>'.encode() in resposta.data

    resposta = client.post(
        "/admin/passes",
        data={
            "aluno_id": com_cartao_id,
            "mes_referencia": "2026-09",
            "quantidade_disponibilizada": "40",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    with app.app_context():
        cota = CotaMensalPasse.query.one()
        assert cota.mes_referencia.isoformat() == "2026-09-01"
        assert cota.quantidade_disponibilizada == 40
        disponibilizacao = MovimentoPasse.query.filter_by(
            cota_id=cota.id,
            tipo="DISPONIBILIZACAO",
        ).one()
        assert disponibilizacao.quantidade == 40

    resposta = client.post(
        "/admin/passes/recarga",
        data={
            "aluno_id": com_cartao_id,
            "mes_referencia": "2026-09",
            "quantidade": "10",
            "motivo": "Quantidade de ensaios superior à cota inicial.",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    with app.app_context():
        recarga = MovimentoPasse.query.filter_by(tipo="RECARGA").one()
        assert recarga.quantidade == 10
        assert recarga.motivo.startswith("Quantidade de ensaios")

    resposta = client.get(
        f"/admin/passes/historico?mes_referencia=2026-09&aluno_id={com_cartao_id}"
    )
    assert resposta.status_code == 200
    assert b"Quantidade de ensaios superior" in resposta.data

    resposta = client.post(
        "/admin/passes/recarga",
        data={
            "aluno_id": com_cartao_id,
            "mes_referencia": "2026-09",
            "quantidade": "5",
            "motivo": "Segunda tentativa",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert b"j\xc3\xa1 foi utilizada neste m\xc3\xaas" in resposta.data


def test_validacoes_admin_passes_rejeitam_valores_invalidos_e_cartao_duplicado(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="PASSES VALIDACAO", ativo=True)
        outro_aluno = Aluno(nome="OUTRO CARTAO", ativo=True)
        db.session.add_all([aluno, outro_aluno])
        db.session.flush()
        cartao = CartaoPasse(aluno_id=aluno.id, numero_controle="VALIDACAO-001")
        db.session.add_all([
            cartao,
            CotaMensalPasse(
                aluno_id=aluno.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=20,
            ),
        ])
        aluno_id = aluno.id
        outro_aluno_id = outro_aluno.id
        db.session.commit()

    resposta = client.post(
        "/admin/passes",
        data={
            "aluno_id": aluno_id,
            "mes_referencia": "2026-09",
            "quantidade_disponibilizada": "-1",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "igual ou maior que zero".encode("utf-8") in resposta.data

    for quantidade, motivo, mensagem in (
        ("0", "Quantidade informada", "maior que zero"),
        ("5", "", "Informe o motivo administrativo"),
    ):
        resposta = client.post(
            "/admin/passes/recarga",
            data={
                "aluno_id": aluno_id,
                "mes_referencia": "2026-09",
                "quantidade": quantidade,
                "motivo": motivo,
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        assert mensagem.encode("utf-8") in resposta.data

    with app.app_context():
        cota = CotaMensalPasse.query.filter_by(aluno_id=aluno_id).one()
        assert cota.quantidade_disponibilizada == 20
        assert MovimentoPasse.query.filter_by(tipo="RECARGA").count() == 0
        with pytest.raises(IntegrityError):
            db.session.add(CartaoPasse(
                aluno_id=outro_aluno_id,
                numero_controle="VALIDACAO-001",
            ))
            db.session.flush()
        db.session.rollback()


def test_lancamento_mensal_e_avulso_de_passes(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        aluno_mensal = Aluno(nome="LANCAMENTO MENSAL", ativo=True)
        aluno_avulso = Aluno(nome="LANCAMENTO AVULSO", ativo=True)
        db.session.add_all([aluno_mensal, aluno_avulso])
        db.session.flush()
        aluno_mensal_id = aluno_mensal.id
        aluno_avulso_id = aluno_avulso.id
        db.session.add_all([
            CartaoPasse(aluno_id=aluno_mensal_id, numero_controle="MENSAL-001"),
            CartaoPasse(aluno_id=aluno_avulso_id, numero_controle="AVULSO-001"),
        ])
        db.session.commit()

    resposta = client.get("/admin/passes?mes_referencia=2026-10")
    assert resposta.status_code == 200
    assert b"Lancar passes" in resposta.data or "Lançar passes".encode() in resposta.data
    assert b"Cota mensal" in resposta.data
    assert b"Avulso" in resposta.data

    resposta = client.post(
        "/admin/passes/lancamento",
        data={
            "modo_lancamento": "mensal",
            "aluno_id": aluno_mensal_id,
            "mes_referencia": "2026-10",
            "quantidade": "30",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    resposta = client.post(
        "/admin/passes/lancamento",
        data={
            "modo_lancamento": "avulso",
            "aluno_id": aluno_mensal_id,
            "mes_referencia": "2026-10",
            "quantidade": "8",
            "motivo": "Mais ensaios neste mês.",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    resposta = client.post(
        "/admin/passes/lancamento",
        data={
            "modo_lancamento": "avulso",
            "aluno_id": aluno_avulso_id,
            "mes_referencia": "2026-10",
            "quantidade": "6",
            "motivo": "Cartão emitido após lançamento mensal.",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    with app.app_context():
        cota_mensal = CotaMensalPasse.query.filter_by(aluno_id=aluno_mensal_id).one()
        assert cota_mensal.quantidade_disponibilizada == 30
        assert routes._saldo_cota_passe(cota_mensal) == 38
        assert MovimentoPasse.query.filter_by(
            cota_id=cota_mensal.id, tipo="RECARGA"
        ).one().motivo == "Mais ensaios neste mês."

        cota_avulsa = CotaMensalPasse.query.filter_by(aluno_id=aluno_avulso_id).one()
        assert cota_avulsa.quantidade_disponibilizada == 0
        assert routes._saldo_cota_passe(cota_avulsa) == 6

    resposta = client.post(
        "/admin/passes/lancamento",
        data={
            "modo_lancamento": "avulso",
            "aluno_id": aluno_mensal_id,
            "mes_referencia": "2026-10",
            "quantidade": "3",
            "motivo": "Outra recarga",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "já foi utilizado neste mês".encode() in resposta.data


def test_presenca_consumo_estorno_e_excecao_sem_cartao(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        ensaio = Ensaio(titulo="Ensaio de teste", data_ensaio=date(2026, 9, 29))
        sem_cartao = Aluno(nome="SEM CARTAO", ativo=True)
        com_cartao = Aluno(nome="COM CARTAO", ativo=True)
        sem_saldo = Aluno(nome="SEM SALDO", ativo=True)
        db.session.add_all([ensaio, sem_cartao, com_cartao, sem_saldo])
        db.session.flush()
        db.session.add_all([
            CartaoPasse(aluno_id=com_cartao.id, numero_controle="CARTAO-002"),
            CartaoPasse(aluno_id=sem_saldo.id, numero_controle="CARTAO-003"),
            CotaMensalPasse(
                aluno_id=com_cartao.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=4,
            ),
            CotaMensalPasse(
                aluno_id=sem_saldo.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=0,
            ),
        ])
        db.session.flush()

        presenca_sem_cartao = Presenca(
            aluno_id=sem_cartao.id,
            ensaio_id=ensaio.id,
            data_presenca=ensaio.data_ensaio,
            presente=True,
        )
        presenca_com_cartao = Presenca(
            aluno_id=com_cartao.id,
            ensaio_id=ensaio.id,
            data_presenca=ensaio.data_ensaio,
            presente=True,
        )
        presenca_sem_saldo = Presenca(
            aluno_id=sem_saldo.id,
            ensaio_id=ensaio.id,
            data_presenca=ensaio.data_ensaio,
            presente=True,
        )
        db.session.add_all([presenca_sem_cartao, presenca_com_cartao, presenca_sem_saldo])
        db.session.flush()

        routes._atualizar_movimento_passe(presenca_sem_cartao)
        routes._atualizar_movimento_passe(presenca_com_cartao)
        assert MovimentoPasse.query.filter_by(presenca_id=presenca_sem_cartao.id).count() == 0
        assert MovimentoPasse.query.filter_by(presenca_id=presenca_com_cartao.id).one().quantidade == -2

        routes._atualizar_movimento_passe(presenca_com_cartao)
        assert MovimentoPasse.query.filter_by(
            presenca_id=presenca_com_cartao.id,
            tipo="CONSUMO",
        ).count() == 1

        presenca_com_cartao.presente = False
        routes._atualizar_movimento_passe(presenca_com_cartao)
        movimentos_estornados = MovimentoPasse.query.filter_by(
            presenca_id=presenca_com_cartao.id
        ).all()
        assert sum(
            movimento.quantidade
            for movimento in movimentos_estornados
        ) == 0
        assert [movimento.tipo for movimento in movimentos_estornados] == ["CONSUMO", "ESTORNO"]

        presenca_com_cartao.presente = True
        routes._atualizar_movimento_passe(presenca_com_cartao)
        routes._atualizar_movimento_passe(presenca_com_cartao)
        movimentos_reativados = MovimentoPasse.query.filter_by(
            presenca_id=presenca_com_cartao.id
        ).all()
        assert sum(movimento.quantidade for movimento in movimentos_reativados) == -2
        assert sum(1 for movimento in movimentos_reativados if movimento.tipo == "CONSUMO") == 2

        with pytest.raises(ValueError, match="são necessários 2"):
            routes._atualizar_movimento_passe(presenca_sem_saldo)


def test_estorno_de_passes_ocorre_com_cartao_inativo_ou_removido(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        ensaio = Ensaio(titulo="Ensaio de estorno", data_ensaio=date(2026, 9, 29))
        aluno_cartao_inativo = Aluno(nome="CARTAO INATIVO", ativo=True)
        aluno_cartao_removido = Aluno(nome="CARTAO REMOVIDO", ativo=True)
        db.session.add_all([ensaio, aluno_cartao_inativo, aluno_cartao_removido])
        db.session.flush()
        cartao_inativo = CartaoPasse(
            aluno_id=aluno_cartao_inativo.id,
            numero_controle="CARTAO-ESTORNO-001",
        )
        cartao_removido = CartaoPasse(
            aluno_id=aluno_cartao_removido.id,
            numero_controle="CARTAO-ESTORNO-002",
        )
        db.session.add_all([
            cartao_inativo,
            cartao_removido,
            CotaMensalPasse(
                aluno_id=aluno_cartao_inativo.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=4,
            ),
            CotaMensalPasse(
                aluno_id=aluno_cartao_removido.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=4,
            ),
        ])
        db.session.flush()
        presencas = [
            Presenca(
                aluno_id=aluno.id,
                ensaio_id=ensaio.id,
                data_presenca=ensaio.data_ensaio,
                presente=True,
            )
            for aluno in (aluno_cartao_inativo, aluno_cartao_removido)
        ]
        db.session.add_all(presencas)
        db.session.commit()

        for presenca in presencas:
            routes._atualizar_movimento_passe(presenca)
        db.session.commit()

        cartao_inativo.ativo = False
        db.session.delete(cartao_removido)
        db.session.commit()
        db.session.expire_all()

        for presenca in presencas:
            presenca.presente = False
            routes._atualizar_movimento_passe(presenca)
        db.session.commit()

        for presenca in presencas:
            movimentos = MovimentoPasse.query.filter_by(presenca_id=presenca.id).all()
            assert [movimento.tipo for movimento in movimentos] == ["CONSUMO", "ESTORNO"]
            assert sum(movimento.quantidade for movimento in movimentos) == 0


def test_chamada_coletiva_faz_rollback_se_um_integrante_nao_tem_saldo(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        ensaio = Ensaio(titulo="Chamada atômica", data_ensaio=date(2026, 9, 30))
        aluno_com_saldo = Aluno(nome="A COM SALDO", ativo=True)
        aluno_sem_saldo = Aluno(nome="B SEM SALDO", ativo=True)
        db.session.add_all([ensaio, aluno_com_saldo, aluno_sem_saldo])
        db.session.flush()
        db.session.add_all([
            CartaoPasse(aluno_id=aluno_com_saldo.id, numero_controle="ATOMICO-001"),
            CartaoPasse(aluno_id=aluno_sem_saldo.id, numero_controle="ATOMICO-002"),
            CotaMensalPasse(
                aluno_id=aluno_com_saldo.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=2,
            ),
            CotaMensalPasse(
                aluno_id=aluno_sem_saldo.id,
                mes_referencia=date(2026, 9, 1),
                quantidade_disponibilizada=0,
            ),
        ])
        db.session.commit()
        ensaio_id = ensaio.id
        aluno_com_saldo_id = aluno_com_saldo.id
        aluno_sem_saldo_id = aluno_sem_saldo.id

    resposta = client.post(
        f"/admin/ensaio/{ensaio_id}/presenca",
        data={
            f"presenca_{aluno_com_saldo_id}": "presente",
            f"presenca_{aluno_sem_saldo_id}": "presente",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    with app.app_context():
        assert Presenca.query.filter_by(ensaio_id=ensaio_id).count() == 0
        assert MovimentoPasse.query.count() == 0


def test_cria_atividade_avulsa_e_registra_presenca(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="ALUNO DE ATIVIDADE", ativo=True)
        db.session.add(aluno)
        db.session.commit()
        aluno_id = aluno.id

    resposta = client.post(
        "/admin/atividade/create",
        data={
            "tipo": "TREINAMENTO",
            "titulo": "Treinamento de percussão",
            "data_atividade": "2026-09-29",
            "horario_inicio": "16:00",
            "horario_fim": "18:00",
            "area": "Percussão",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    with app.app_context():
        atividade = Atividade.query.one()
        atividade_id = atividade.id

    resposta = client.post(
        f"/admin/atividade/{atividade_id}/presenca",
        data={f"presenca_{aluno_id}": "presente", "csrf_token": token},
        follow_redirects=False,
    )
    assert resposta.status_code == 302

    with app.app_context():
        registro = Presenca.query.filter_by(
            aluno_id=aluno_id, atividade_id=atividade_id
        ).one()
        assert registro.presente is True
        assert MovimentoPasse.query.filter_by(presenca_id=registro.id).count() == 0


def test_historico_e_folha_diaria_incluem_atividade_avulsa(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    with app.app_context():
        aluno = Aluno(nome="Aluno de atividade", ativo=True)
        atividade = Atividade(
            tipo="TREINAMENTO",
            titulo="Treinamento de percussão",
            data_atividade=date(2026, 9, 29),
            horario_inicio="16:00",
            horario_fim="18:00",
            local="Sala de ensaio",
            area="Percussão",
            responsavel="Prof. Tarde",
        )
        db.session.add_all([aluno, atividade])
        db.session.flush()
        presenca = Presenca(
            aluno_id=aluno.id,
            atividade_id=atividade.id,
            data_presenca=atividade.data_atividade,
            presente=True,
        )
        db.session.add(presenca)
        db.session.commit()

    response = client.get("/admin/presencas/historico")
    assert response.status_code == 200
    assert "Treinamento de percussão".encode("utf-8") in response.data

    response = client.get("/admin/presencas/diaria?data=2026-09-29")
    assert response.status_code == 200
    assert "Treinamento de percussão".encode("utf-8") in response.data
    assert "Sala de ensaio".encode("utf-8") in response.data


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


def test_central_de_comunicacoes_envia_para_participantes_autorizados_do_evento(monkeypatch):
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
        aluno = Aluno(nome="Integrante autorizado", ativo=True, email="integrante@teste.com")
        aluno_pendente = Aluno(nome="Integrante sem autorização", ativo=True, email="pendente@teste.com")
        aluno_inativo = Aluno(nome="Integrante inativo", ativo=False, email="inativo@teste.com")
        evento = Evento(nome_evento="Apresentação municipal", data_evento=date(2026, 10, 20))
        db.session.add_all([aluno, aluno_pendente, aluno_inativo, evento])
        db.session.commit()
        db.session.add_all([
            AutorizacaoViagem(aluno_id=aluno.id, evento_id=evento.id, autorizado=True),
            AutorizacaoViagem(aluno_id=aluno_pendente.id, evento_id=evento.id, autorizado=False),
            AutorizacaoViagem(aluno_id=aluno_inativo.id, evento_id=evento.id, autorizado=True),
        ])
        db.session.commit()
        evento_id = evento.id

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Orientações do evento",
            "mensagem": "Comparecer no horário combinado.",
            "tipo": "informativo",
            "publico": "evento",
            "evento_id": str(evento_id),
            "canal": "email",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        comunicacao_id = comunicacao.id

    response = client.post(
        f"/admin/comunicacoes/{comunicacao_id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao_id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].destinatario_email == "integrante@teste.com"
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
        outros_contatos = [
            ContatoComunicacao(
                nome="Secretaria de Educação",
                email="educacao@prefeitura.gov.br",
                ativo=True,
                autorizacao_email=True,
            ),
            ContatoComunicacao(
                nome="Secretaria de Esportes",
                email="esportes@prefeitura.gov.br",
                ativo=True,
                autorizacao_email=True,
            ),
        ]
        db.session.add_all([contato, *outros_contatos])
        db.session.commit()
        contato_id = contato.id

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Contato institucional",
            "mensagem": "Mensagem para a prefeitura.",
            "tipo": "informativo",
            "publico": "externo",
            "canal": "email",
            "contato_externo_id": str(contato_id),
            "consentimento_email": "on",
            "origem_consentimento_email": "Autorização registrada pela coordenação",
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
        assert comunicacao.contato_externo_id == contato_id

    emails_enviados = []
    monkeypatch.setattr(
        routes,
        "enviar_email_gmail",
        lambda destinatario, assunto, mensagem, anexos: emails_enviados.append(destinatario),
    )
    app.config["TESTING"] = False
    response = client.post(
        f"/admin/comunicacoes/{comunicacao.id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert emails_enviados == ["cultura@prefeitura.gov.br"]

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao.id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].tipo_destinatario == "contato_externo"
        assert destinatarios[0].destinatario_id == contato_id
        assert destinatarios[0].destinatario_email == "cultura@prefeitura.gov.br"
        assert destinatarios[0].status == "enviado"
        assert ComunicacaoDestinatario.query.filter(
            ComunicacaoDestinatario.comunicacao_id == comunicacao.id,
            ComunicacaoDestinatario.destinatario_email.in_(
                ["educacao@prefeitura.gov.br", "esportes@prefeitura.gov.br"]
            ),
        ).count() == 0
        contato_atualizado = db.session.get(ContatoComunicacao, contato_id)
        assert contato_atualizado.autorizacao_email is True
        assert contato_atualizado.autorizacao_email_em is not None
        assert contato_atualizado.origem_autorizacao_email == "Autorização registrada pela coordenação"


def test_central_bloqueia_email_externo_quando_publico_geral_esta_selecionado(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "chave-de-teste-segura")
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(Config, "IMPORTAR_LOGRADOUROS_INICIAIS", False)
    monkeypatch.setattr(utils, "importar_municipios", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    token = _login_admin(client)

    response = client.post(
        "/admin/comunicacoes/nova",
        data={
            "assunto": "Destinatário externo com público incorreto",
            "mensagem": "Esta comunicação não deve ser criada.",
            "publico": "geral",
            "destinatario_nome": "Contato avulso",
            "destinatario_email": "contato@example.org",
            "csrf_token": token,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        assert Comunicacao.query.filter_by(
            assunto="Destinatário externo com público incorreto"
        ).count() == 0


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
            "consentimento_email": "on",
            "origem_consentimento_email": "Autorização recebida por ofício",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        comunicacao = Comunicacao.query.order_by(Comunicacao.id.desc()).first()
        comunicacao_id = comunicacao.id
        contato_id = comunicacao.contato_externo_id
        assert comunicacao.destinatario_nome == "Secretaria de Educação"
        assert comunicacao.destinatario_email == "educacao@outra-prefeitura.gov.br"
        contato = db.session.get(ContatoComunicacao, comunicacao.contato_externo_id)
        assert contato.autorizacao_email is True
        assert contato.autorizacao_email_em is not None
        assert contato.origem_autorizacao_email == "Autorização recebida por ofício"

    response = client.post(
        f"/admin/comunicacoes/{comunicacao_id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        destinatarios = ComunicacaoDestinatario.query.filter_by(comunicacao_id=comunicacao_id).all()
        assert len(destinatarios) == 1
        assert destinatarios[0].destinatario_id == contato_id
        assert destinatarios[0].destinatario_email == "educacao@outra-prefeitura.gov.br"


def test_central_de_comunicacoes_bloqueia_envio_apos_revogacao(monkeypatch):
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
            nome="Contato autorizado",
            email="autorizado@prefeitura.gov.br",
            autorizacao_email=True,
            autorizacao_email_em=datetime.now(timezone.utc),
            origem_autorizacao_email="Autorização institucional",
            ativo=True,
        )
        db.session.add(contato)
        db.session.flush()
        comunicacao = Comunicacao(
            assunto="Aviso institucional",
            mensagem="Mensagem de teste",
            publico="externo",
            contato_externo_id=contato.id,
            destinatario_nome=contato.nome,
            destinatario_email=contato.email,
            criado_por_id=1,
        )
        db.session.add(comunicacao)
        db.session.commit()
        contato_id = contato.id
        comunicacao_id = comunicacao.id

    response = client.post(
        f"/admin/comunicacoes/contatos/{contato_id}/revogar-email",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.post(
        f"/admin/comunicacoes/{comunicacao_id}/enviar",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        contato = db.session.get(ContatoComunicacao, contato_id)
        assert contato.autorizacao_email is False
        assert contato.email_revogado_em is not None
        assert ComunicacaoDestinatario.query.filter_by(
            comunicacao_id=comunicacao_id
        ).count() == 0


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


def test_google_calendar_atividade_usa_horario_local_e_detalhes(monkeypatch):
    atividade = Atividade(
        tipo="TREINAMENTO",
        titulo="Treinamento de percussão",
        data_atividade=date(2026, 10, 2),
        horario_inicio="18:30",
        horario_fim="20:00",
        local="Sede da Banda",
        area="Percussão",
        responsavel="Coordenação",
        observacoes="Levar baquetas.",
    )

    payload = google_calendar._activity_payload("atividade", atividade)

    assert payload["summary"] == "Treinamento de percussão"
    assert payload["start"]["dateTime"] == "2026-10-02T18:30:00-03:00"
    assert payload["end"]["dateTime"] == "2026-10-02T20:00:00-03:00"
    assert payload["location"] == "Sede da Banda"
    assert "TREINAMENTO" in payload["description"]
    assert "Coordenação" in payload["description"]
    assert "Levar baquetas." in payload["description"]


def test_google_calendar_sincroniza_atividade_sem_duplicar(monkeypatch):
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
        atividade = Atividade(
            tipo="APRESENTACAO",
            titulo="Apresentação da Banda",
            data_atividade=date(2026, 10, 10),
            status="REALIZADA",
        )
        db.session.add(atividade)
        db.session.commit()

        assert google_calendar.sincronizar_atividade("atividade", atividade) is True
        sync = GoogleCalendarSync.query.filter_by(atividade_id=atividade.id).one()
        event_id = sync.google_event_id
        assert chamadas["post"][0][1]["json"]["start"] == {"date": "2026-10-10"}

        atividade.titulo = "Apresentação atualizada"
        assert google_calendar.sincronizar_atividade("atividade", atividade) is True
        assert chamadas["patch"][-1][0].endswith(event_id)
        assert chamadas["patch"][-1][1]["json"]["summary"] == "Apresentação atualizada"
        assert GoogleCalendarSync.query.filter_by(atividade_id=atividade.id).count() == 1

        atividade.status = "CANCELADO"
        assert google_calendar.sincronizar_atividade("atividade", atividade) is True
        assert chamadas["patch"][-1][1]["json"]["status"] == "cancelled"


def test_migracao_calendar_preserva_vinculo_legado_de_ensaio(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    with app.app_context():
        ensaio = Ensaio(titulo="Ensaio vinculado", data_ensaio=date(2026, 10, 15))
        db.session.add(ensaio)
        db.session.commit()
        ensaio_id = ensaio.id

        db.session.execute(text("DROP TABLE google_calendar_sync"))
        db.session.execute(text(
            "CREATE TABLE google_calendar_sync ("
            "id INTEGER PRIMARY KEY, ensaio_id INTEGER UNIQUE, evento_id INTEGER UNIQUE, "
            "google_event_id VARCHAR(255) NOT NULL UNIQUE, sincronizado_em DATETIME, "
            "CHECK ((ensaio_id IS NOT NULL AND evento_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NOT NULL)), "
            "FOREIGN KEY(ensaio_id) REFERENCES ensaio(id), "
            "FOREIGN KEY(evento_id) REFERENCES evento(id)"
            ")"
        ))
        db.session.execute(text(
            "INSERT INTO google_calendar_sync "
            "(id, ensaio_id, evento_id, google_event_id, sincronizado_em) "
            "VALUES (1, :ensaio_id, NULL, 'evento-google-legado', '2026-09-29 12:00:00')"
        ), {"ensaio_id": ensaio_id})
        db.session.commit()

        utils.migrar_banco_novos_campos()

        colunas = db.session.execute(
            text("PRAGMA table_info(google_calendar_sync)")
        ).fetchall()
        assert "atividade_id" in {coluna[1] for coluna in colunas}
        sync = db.session.get(GoogleCalendarSync, 1)
        assert sync.ensaio_id == ensaio_id
        assert sync.evento_id is None
        assert sync.atividade_id is None
        assert sync.google_event_id == "evento-google-legado"


def test_migracao_presenca_legada_preserva_dados_e_cria_indice_de_atividade(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    with app.app_context():
        aluno = Aluno(nome="ALUNO PRESENCA LEGADA", ativo=True)
        ensaio = Ensaio(titulo="Ensaio legado", data_ensaio=date(2026, 9, 15))
        db.session.add_all([aluno, ensaio])
        db.session.commit()
        cota = CotaMensalPasse(
            aluno_id=aluno.id,
            mes_referencia=date(2026, 9, 1),
            quantidade_disponibilizada=10,
        )
        db.session.add(cota)
        db.session.commit()

        db.session.execute(text("DROP TABLE movimento_passe"))
        db.session.execute(text("DROP TABLE presenca"))
        db.session.execute(text(
            "CREATE TABLE presenca ("
            "id INTEGER PRIMARY KEY, aluno_id INTEGER NOT NULL, ensaio_id INTEGER, "
            "evento_id INTEGER, data_presenca DATE, presente BOOLEAN, observacoes TEXT, "
            "registrado_por_id INTEGER, registrado_at DATETIME, "
            "CHECK ((ensaio_id IS NOT NULL AND evento_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NOT NULL)), "
            "FOREIGN KEY(aluno_id) REFERENCES aluno(id), "
            "FOREIGN KEY(ensaio_id) REFERENCES ensaio(id), "
            "FOREIGN KEY(evento_id) REFERENCES evento(id), "
            "FOREIGN KEY(registrado_por_id) REFERENCES user(id)"
            ")"
        ))
        db.session.execute(text(
            "CREATE TABLE movimento_passe ("
            "id INTEGER PRIMARY KEY, cota_id INTEGER NOT NULL, presenca_id INTEGER NOT NULL, "
            "data_hora DATETIME NOT NULL, quantidade INTEGER NOT NULL, "
            "tipo VARCHAR(20) NOT NULL DEFAULT 'CONSUMO', "
            "FOREIGN KEY(cota_id) REFERENCES cota_mensal_passe(id), "
            "FOREIGN KEY(presenca_id) REFERENCES presenca(id)"
            ")"
        ))
        db.session.execute(text(
            "INSERT INTO presenca "
            "(id, aluno_id, ensaio_id, evento_id, data_presenca, presente, "
            "observacoes, registrado_por_id, registrado_at) "
            "VALUES (77, :aluno_id, :ensaio_id, NULL, '2026-09-15', 1, "
            "'registro legado', NULL, '2026-09-15 18:00:00')"
        ), {"aluno_id": aluno.id, "ensaio_id": ensaio.id})
        db.session.execute(text(
            "INSERT INTO movimento_passe "
            "(id, cota_id, presenca_id, data_hora, quantidade, tipo) "
            "VALUES (91, :cota_id, 77, '2026-09-15 18:00:00', -2, 'CONSUMO')"
        ), {"cota_id": cota.id})
        db.session.commit()

        utils.migrar_banco_novos_campos()
        db.session.expire_all()

        registro = db.session.get(Presenca, 77)
        assert registro is not None
        assert registro.aluno_id == aluno.id
        assert registro.ensaio_id == ensaio.id
        assert registro.evento_id is None
        assert registro.atividade_id is None
        assert registro.data_presenca == date(2026, 9, 15)
        assert registro.presente is True
        assert registro.observacoes == "registro legado"
        movimento = db.session.get(MovimentoPasse, 91)
        assert movimento is not None
        assert movimento.cota_id == cota.id
        assert movimento.presenca_id == registro.id
        assert movimento.quantidade == -2
        assert movimento.tipo == "CONSUMO"

        indices = {
            linha[1]
            for linha in db.session.execute(text("PRAGMA index_list('presenca')")).all()
        }
        assert {
            "uq_presenca_aluno_ensaio",
            "uq_presenca_aluno_evento",
            "uq_presenca_aluno_atividade",
        } <= indices


def test_migracao_adiciona_trilha_de_consentimento_a_contato_legado(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    with app.app_context():
        db.session.execute(text("DROP TABLE contato_comunicacao"))
        db.session.execute(text(
            "CREATE TABLE contato_comunicacao ("
            "id INTEGER PRIMARY KEY, nome VARCHAR(200) NOT NULL, email VARCHAR(200), "
            "telefone VARCHAR(30), autorizacao_email BOOLEAN, "
            "autorizacao_whatsapp BOOLEAN, observacoes TEXT, ativo BOOLEAN, criado_em DATETIME"
            ")"
        ))
        db.session.execute(text(
            "INSERT INTO contato_comunicacao "
            "(id, nome, email, autorizacao_email, ativo) "
            "VALUES (1, 'Contato legado', 'legado@prefeitura.gov.br', 1, 1)"
        ))
        db.session.commit()

        utils.migrar_banco_novos_campos()

        colunas = db.session.execute(
            text("PRAGMA table_info(contato_comunicacao)")
        ).fetchall()
        nomes_colunas = {coluna[1] for coluna in colunas}
        assert {
            "autorizacao_email_em",
            "origem_autorizacao_email",
            "email_revogado_em",
            "autorizacao_whatsapp_em",
            "origem_autorizacao_whatsapp",
            "whatsapp_revogado_em",
        }.issubset(nomes_colunas)
        contato = db.session.get(ContatoComunicacao, 1)
        assert contato.nome == "Contato legado"
        assert contato.autorizacao_email is True


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


def test_rota_de_sincronizacao_calendar_para_atividade_exige_login_e_csrf(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    client = app.test_client()
    _autorizar_google_workspace_em_teste(monkeypatch)
    token = _login_admin(client)

    with app.app_context():
        atividade = Atividade(
            tipo="TREINAMENTO",
            titulo="Treinamento da rota",
            data_atividade=date(2026, 10, 20),
        )
        db.session.add(atividade)
        db.session.commit()
        atividade_id = atividade.id

    sincronizadas = []
    monkeypatch.setattr(
        routes,
        "sincronizar_atividade",
        lambda activity_type, activity: sincronizadas.append(
            (activity_type, activity.id)
        ),
    )

    response = client.get("/admin/atividades")
    assert response.status_code == 200
    assert b"Google Calendar" in response.data
    assert client.post(
        f"/admin/atividade/{atividade_id}/calendar/sincronizar"
    ).status_code == 400
    response = client.post(
        f"/admin/atividade/{atividade_id}/calendar/sincronizar",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert sincronizadas == [("atividade", atividade_id)]


def test_calendario_bmcm_agrega_atividades_e_acoes_por_dia(monkeypatch):
    app = _criar_app_calendar_teste(monkeypatch)
    client = app.test_client()
    _login_admin(client)

    with app.app_context():
        ensaio = Ensaio(
            titulo="Ensaio do calendário",
            data_ensaio=date(2026, 10, 20),
            horario="19:00",
            local="Sede",
        )
        evento = Evento(
            nome_evento="Apresentação do calendário",
            data_evento=date(2026, 10, 20),
            cidade="Marília",
        )
        atividade = Atividade(
            tipo="TREINAMENTO",
            titulo="Treinamento do calendário",
            data_atividade=date(2026, 10, 20),
            horario_inicio="16:00",
            horario_fim="17:30",
        )
        db.session.add_all([ensaio, evento, atividade])
        db.session.commit()
        ensaio_id = ensaio.id
        evento_id = evento.id
        atividade_id = atividade.id

    response = client.get(
        "/admin/calendario?mes=2026-10&data=2026-10-20"
    )

    assert response.status_code == 200
    assert "Calendário BMCM".encode("utf-8") in response.data
    assert "terça-feira, 20/10/2026".encode("utf-8") in response.data
    assert "Ensaio do calendário".encode("utf-8") in response.data
    assert "Apresentação do calendário".encode("utf-8") in response.data
    assert "Treinamento do calendário".encode("utf-8") in response.data
    assert f"/admin/ensaio/{ensaio_id}/presenca".encode() in response.data
    assert f"/admin/evento/{evento_id}/presenca".encode() in response.data
    assert f"/admin/atividade/{atividade_id}/presenca".encode() in response.data
    assert f"/admin/evento/{evento_id}/relatorio".encode() in response.data
    assert b"/admin/presencas/diaria?data=2026-10-20" in response.data
    assert b"/admin/atividade/create?data=2026-10-20" in response.data
    assert b"/admin/ensaio/create?data=2026-10-20" in response.data
    assert b"/admin/evento/create?data=2026-10-20" in response.data

    for path in (
        "/admin/atividade/create?data=2026-10-20",
        "/admin/ensaio/create?data=2026-10-20",
        "/admin/evento/create?data=2026-10-20",
    ):
        form_response = client.get(path)
        assert form_response.status_code == 200
        assert b'value="2026-10-20"' in form_response.data

    dia_vazio = client.get(
        "/admin/calendario?mes=2026-10&data=2026-10-21"
    )
    assert dia_vazio.status_code == 200
    assert "Nenhum ensaio, evento ou atividade registrado nesta data.".encode("utf-8") in dia_vazio.data
    assert b">Hoje</a>" in dia_vazio.data


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
    monkeypatch.setattr(routes, "has_scope", lambda scope: False)
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
