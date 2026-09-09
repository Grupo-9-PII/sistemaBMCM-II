from datetime import date

from sqlalchemy import text

import app.utils as utils
from app import create_app, db
from app.models import Aluno, Ensaio, Presenca, User
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
    response = client.post(
        "/login",
        data={"username": "admin", "password": "123456", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return token


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
