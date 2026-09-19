
import os
import logging
from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from datetime import timedelta
from config import Config, obter_secret_key_local

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça login para acessar esta página."

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    if user_id is None:
        return None
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(Config.BASE_DIR, "templates"),
        static_folder=os.path.join(Config.BASE_DIR, "static"),
    )

    instance_dir = os.path.join(Config.BASE_DIR, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    app.config.from_object(Config)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('SESSION_COOKIE_SECURE', not app.debug)
    app.config.setdefault('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)

    # Registro de eventos de segurança (tentativas de login falhas, 403, erros).
    logging.basicConfig(
        filename=os.path.join(instance_dir, "app.log"),
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = obter_secret_key_local(Config.BASE_DIR)

    db.init_app(app)
    login_manager.session_protection = "strong"
    login_manager.init_app(app)

    from .auth import auth_bp
    from .routes import main_bp
    from .utils import (
        criar_admin_padrao,
        criar_dados_iniciais,
        importar_municipios,
        migrar_banco_novos_campos,
        carregar_configuracoes_app,
        limpar_logs_antigos,
        obter_todas_configuracoes,
        obter_token_csrf,
        validar_csrf,
        verificar_timeout_sessao,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.before_request
    def proteger_requisicoes():
        resposta_timeout = verificar_timeout_sessao()
        if resposta_timeout is not None:
            return resposta_timeout
        if request.method == "POST":
            validar_csrf()

    @app.before_request
    def proteger_fotos_privadas():
        # Fotos e assinaturas de menores não podem ser lidas sem sessão iniciada,
        # mesmo que alguém conheça a URL exata de /static/uploads/.
        if not current_user.is_authenticated and request.path.startswith("/static/uploads/"):
            return redirect("/login")

    @app.errorhandler(500)
    def manejar_error_500(e):
        app.logger.error("Erro interno do servidor", exc_info=e)
        return "Ocorreu um erro interno. Entre em contato com o administrador.", 500

    @app.errorhandler(413)
    def manejar_error_413(e):
        return "O arquivo excede o tamanho máximo permitido (5 MB).", 413

    @app.context_processor
    def inject_system_settings():
        return {
            "system_settings": obter_todas_configuracoes(),
            "csrf_token": obter_token_csrf(),
            "app_version": app.config["APP_VERSION"],
        }

    with app.app_context():
        instance_dir = os.path.join(Config.BASE_DIR, "instance")
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir, exist_ok=True)
        
        # Criar todas as tabelas no banco de dados
        db.create_all()
        
        # Migrar banco para novos campos (cep, bairro, estado)
        migrar_banco_novos_campos()
        
        # Criar admin padrão
        criar_admin_padrao()
        
        # Criar dados iniciais (tipos de instrumento, naipes, funções)
        criar_dados_iniciais()
        
        # Importar municípios e logradouros do arquivo SQL
        importar_municipios()

        # Carregar configurações salvas no banco para o app
        carregar_configuracoes_app(app)
        limpar_logs_antigos()

    return app
