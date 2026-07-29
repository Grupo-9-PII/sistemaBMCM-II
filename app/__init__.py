
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import timedelta
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça login para acessar esta página."

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(Config.BASE_DIR, "templates"),
        static_folder=os.path.join(Config.BASE_DIR, "static"),
    )
    app.config.from_object(Config)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)


    db.init_app(app)
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
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_system_settings():
        return {"system_settings": obter_todas_configuracoes()}

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

