from functools import wraps
from flask import abort, session, flash, redirect, url_for, current_app, request
from flask_login import logout_user, current_user
from datetime import datetime, date, timedelta
import os
import base64
import binascii
import hmac
import secrets
from flask import redirect, url_for, flash
from flask_login import current_user
from .models import User, TipoInstrumento, Naipe, FuncaoBanda, Cidade, Logradouro, SistemaConfig
from . import db
from sqlalchemy import text
from werkzeug.utils import secure_filename

SENHA_PADRAO = "123456"

# Versão do texto do termo (auditoria LGPD — atualize quando o texto legal mudar).
TERMO_AUTORIZACAO_FOTO_VERSAO = "2026-04-13"


def obter_token_csrf():
    """Retorna o token CSRF associado a sessão atual."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validar_csrf():
    """Bloqueia POSTs sem token correspondente à sessão atual."""
    token_enviado = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    token_esperado = session.get("csrf_token")
    if not token_esperado or not token_enviado or not hmac.compare_digest(
        token_enviado, token_esperado
    ):
        abort(400, description="Token CSRF ausente ou inválido.")


def idade_anos_hoje(data_nascimento):
    if not data_nascimento:
        return None
    hoje = date.today()
    anos = hoje.year - data_nascimento.year
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        anos -= 1
    return anos


def exige_autorizacao_foto_menor(data_nascimento):
    """Menor de 18 anos, ou data desconhecida (tratamos como sensível quando houver foto)."""
    if data_nascimento is None:
        return True
    idade = idade_anos_hoje(data_nascimento)
    return idade is not None and idade < 18


def consentimento_foto_obrigatorio(data_nascimento, tem_upload_novo, aluno_id, foto_path_atual):
    if not exige_autorizacao_foto_menor(data_nascimento):
        return False
    if tem_upload_novo:
        return True
    if foto_path_atual and aluno_id:
        from .models import AutorizacaoFotoMenor
        existe = AutorizacaoFotoMenor.query.filter_by(
            aluno_id=aluno_id, foto_path_coberto=foto_path_atual
        ).first()
        return existe is None
    return False


def validar_payload_autorizacao_foto(form):
    nome = normalizar_campo_texto(form.get("autorizacao_responsavel_nome"))
    par = (form.get("autorizacao_responsavel_parentesco") or "").strip().upper()
    sig = (form.get("assinatura_foto_data") or "").strip()
    aceite = form.get("autorizacao_foto_aceite") == "1"
    if not nome or len(nome) < 3:
        return False, "Informe o nome completo do responsável que assina a autorização de uso da imagem."
    if par not in ("PAI", "MAE", "RESPONSAVEL_LEGAL", "OUTRO"):
        return False, "Selecione o vínculo do signatário com o menor."
    if not aceite:
        return False, "É necessário aceitar o termo para armazenar a foto do menor."
    if not sig.startswith("data:image"):
        return False, "A assinatura digital (desenho no quadro) do responsável é obrigatória."
    try:
        _, b64 = sig.split(",", 1)
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error):
        return False, "Assinatura inválida. Desenhe novamente no quadro e tente salvar."
    if len(raw) < 120:
        return False, "Assinatura muito curta. Desenhe no quadro com traço visível."
    return True, {
        "nome": nome,
        "parentesco": par,
        "cpf": (form.get("autorizacao_responsavel_cpf") or "").strip() or None,
        "assinatura_data_url": sig,
    }


def salvar_assinatura_data_url(data_url, aluno_id):
    """Grava PNG da assinatura capturada no navegador (rede interna). Retorna caminho relativo a static/."""
    if not data_url or not data_url.startswith("data:image"):
        return None
    try:
        _, b64 = data_url.split(",", 1)
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error):
        return None
    if len(raw) < 120:
        return None
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_abs = os.path.join(base_dir, "static", "uploads", "autorizacoes_menor")
    os.makedirs(upload_abs, exist_ok=True)
    fn = f"assinatura_aluno_{aluno_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
    path_abs = os.path.join(upload_abs, fn)
    with open(path_abs, "wb") as f:
        f.write(raw)
    return os.path.join("uploads", "autorizacoes_menor", fn)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        if not current_user.is_admin:
            flash("Acesso restrito ao administrador.")
            return redirect(url_for("main.dashboard"))

        return f(*args, **kwargs)
    return decorated_function


def profissional_required(f):
    """Decorador para usuários profissionais (não-admin) - apenas login_required"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Faça login para continuar.")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def normalizar_campo_texto(campo):
    """Normaliza campo texto: CAIXA ALTA, remove espaços extras"""
    if campo:
        return ' '.join(campo.strip().upper().split())
    return campo

def normalizar_telefone(telefone):
    """Remove tudo exceto números e aplica máscara (11) 99999-9999"""
    if not telefone:
        return telefone
    # Remove tudo exceto números
    numeros = ''.join(filter(str.isdigit, telefone))
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return telefone


def obter_configuracao(chave, default=None):
    config = SistemaConfig.query.filter_by(key=chave).first()
    return config.value if config else default


def obter_configuracao_int(chave, default=None):
    valor = obter_configuracao(chave)
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def obter_todas_configuracoes():
    configs = SistemaConfig.query.all()
    return {config.key: config.value for config in configs}


def definir_configuracao(chave, valor):
    config = SistemaConfig.query.filter_by(key=chave).first()
    if config:
        config.value = valor
    else:
        config = SistemaConfig(key=chave, value=valor)
        db.session.add(config)
    db.session.commit()
    return config


def carregar_configuracoes_app(app):
    with app.app_context():
        for chave, valor in obter_todas_configuracoes().items():
            if chave == "upload_maximo":
                try:
                    app.config["MAX_CONTENT_LENGTH"] = int(valor) * 1024 * 1024
                except (TypeError, ValueError):
                    pass
            elif chave == "backup_folder":
                if valor:
                    app.config["BACKUP_FOLDER"] = valor
            elif chave == "session_timeout_minutes":
                try:
                    minutos = int(valor)
                    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=minutos)
                    app.config["SESSION_TIMEOUT_MINUTES"] = minutos
                except (TypeError, ValueError):
                    pass
            elif chave == "login_attempts_limit":
                try:
                    app.config["LOGIN_ATTEMPTS_LIMIT"] = int(valor)
                except (TypeError, ValueError):
                    pass
            else:
                app.config[chave.upper()] = valor


def validar_senha_complexidade(senha):
    if not senha or len(senha) < 6:
        return False, "Senha deve ter no mínimo 6 caracteres."

    requisitos = []
    if obter_configuracao('password_lower', '1') == '1' and not any(c.islower() for c in senha):
        requisitos.append('uma letra minúscula')
    if obter_configuracao('password_upper', '1') == '1' and not any(c.isupper() for c in senha):
        requisitos.append('uma letra maiúscula')
    if obter_configuracao('password_number', '1') == '1' and not any(c.isdigit() for c in senha):
        requisitos.append('um número')
    if obter_configuracao('password_symbol', '1') == '1' and not any(c in '!@#$%^&*()-_=+[{]}\\|;:",<.>/?' for c in senha):
        requisitos.append('um caractere especial')

    if requisitos:
        if len(requisitos) == 1:
            mensagem = requisitos[0]
        else:
            mensagem = ', '.join(requisitos[:-1]) + ' e ' + requisitos[-1]
        return False, f"Senha deve conter {mensagem}."

    return True, None


def limpar_logs_antigos():
    dias = obter_configuracao_int('log_retention_days', None)
    if dias is None or dias <= 0:
        return

    from .models import HardDeleteAlunoLog
    limite = datetime.utcnow() - timedelta(days=dias)
    HardDeleteAlunoLog.query.filter(HardDeleteAlunoLog.created_at < limite).delete(synchronize_session=False)
    db.session.commit()


def criar_admin_padrao():
    admin = User.query.filter_by(is_admin=True).first()

    if not admin:
        novo_admin = User(
            username="admin",
            is_admin=True,
            must_change_password=True
        )
        novo_admin.set_password(SENHA_PADRAO)

        db.session.add(novo_admin)
        db.session.commit()

def criar_dados_iniciais():
    """Cria dados iniciais para o sistema (tipos de instrumento, naipes, funções)"""
    
    # Criar tipos de instrumento se não existirem
    if not TipoInstrumento.query.first():
        tipos = [
            TipoInstrumento(nome="SOPRO"),
            TipoInstrumento(nome="PERCUSSÃO"),
        ]
        db.session.add_all(tipos)
    
    # Criar naipes se não existirem
    if not Naipe.query.first():
        naipes = [
            Naipe(nome="MADEIRA"),
            Naipe(nome="METAIS"),
            Naipe(nome="PERCUSSÃO"),
            Naipe(nome="CLARIM"),
        ]
        db.session.add_all(naipes)
    
    # Criar funções da banda se não existirem
    if not FuncaoBanda.query.first():
        funcoes = [
            FuncaoBanda(nome_funcao="MAESTRO"),
            FuncaoBanda(nome_funcao="INSTRUTOR"),
            FuncaoBanda(nome_funcao="ALUNO"),
            FuncaoBanda(nome_funcao="COREÓGRAFO"),
        ]
        db.session.add_all(funcoes)
    
    db.session.commit()


def importar_municipios():
    """Importa dados de municípios e logradouros do arquivo SQL"""
    
    # Verificar se já existem dados
    if Cidade.query.first():
        return  # Dados já foram importados
    
    # Caminho para o arquivo SQL
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_file = os.path.join(base_dir, "municipios.sql")
    
    if not os.path.exists(sql_file):
        return
    
    # Ler e executar o arquivo SQL
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Executar SQL diretamente no banco de dados
    import re
    
    # Buscar INSERTs da tabela cidade
    cidade_pattern = r"INSERT INTO `cidade` VALUES ([^;]+);"
    cidade_matches = re.findall(cidade_pattern, sql_content, re.DOTALL)
    
    for match in cidade_matches:
        # Parse dos valores
        values = match.strip()
        if values.startswith('(') and values.endswith(')'):
            # Parse dos campos: (id,'nome',uf,codigo_ibge,ddd)
            values = values[1:-1]  # Remove parênteses externos
            parts = values.split('),(')
            
            for part in parts:
                part = part.strip().strip('()')
                if part:
                    # Separar os campos
                    campos = part.split(',')
                    if len(campos) >= 5:

                        id_val = int(campos[0].strip())
                        nome = normalizar_campo_texto(campos[1].strip().strip("'"))
                        uf = campos[2].strip().strip("'")
                        cod_ibge = int(campos[3].strip())
                        ddd = campos[4].strip().strip("'")
                        
                        cidade = Cidade(
                            id=id_val,
                            descricao=nome,
                            uf=uf,
                            codigo_ibge=cod_ibge,
                            ddd=ddd
                        )
                        db.session.add(cidade)
    
    db.session.commit()
    
    # Executar INSERTs da tabela logradouro
    logradouro_pattern = r"INSERT INTO `logradouro` VALUES ([^;]+);"
    logradouro_matches = re.findall(logradouro_pattern, sql_content, re.DOTALL)
    
    for match in logradouro_matches:
        values = match.strip()
        if values.startswith('(') and values.endswith(')'):
            values = values[1:-1]
            parts = values.split('),(')
            
            for part in parts:
                part = part.strip().strip('()')
                if part:
                    campos = part.split(',')
                    if len(campos) >= 11:
                        cep = campos[0].strip().strip("'")
                        id_val = int(campos[1].strip())
                        tipo = normalizar_campo_texto(campos[2].strip().strip("'"))
                        descricao = normalizar_campo_texto(campos[3].strip().strip("'"))
                        cidade_id = int(campos[4].strip())
                        uf = campos[5].strip().strip("'")
                        complemento = normalizar_campo_texto(campos[6].strip().strip("'")) if campos[6].strip() != 'NULL' else None
                        descricao_sem_numero = normalizar_campo_texto(campos[7].strip().strip("'")) if campos[7].strip() != 'NULL' else None
                        descricao_cidade = normalizar_campo_texto(campos[8].strip().strip("'")) if campos[8].strip() != 'NULL' else None
                        codigo_cidade_ibge = int(campos[9].strip()) if campos[9].strip() != 'NULL' else None
                        descricao_bairro = normalizar_campo_texto(campos[10].strip().strip("'")) if campos[10].strip() != 'NULL' else None
                        
                        logradouro = Logradouro(
                            cep=cep,
                            id=id_val,
                            tipo=tipo,
                            descricao=descricao,
                            cidade_id=cidade_id,
                            uf=uf,
                            complemento=complemento,
                            descricao_sem_numero=descricao_sem_numero,
                            descricao_cidade=descricao_cidade,
                            codigo_cidade_ibge=codigo_cidade_ibge,
                            descricao_bairro=descricao_bairro
                        )
                        db.session.add(logradouro)
    
    db.session.commit()


def migrar_banco_novos_campos():
    """Adiciona os novos campos ao banco de dados se não existirem"""
    try:
        # Verificar se a coluna cep existe na tabela aluno
        result = db.session.execute(text("PRAGMA table_info(aluno)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Adicionar coluna cep se não existir
        if 'cep' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN cep VARCHAR(10)"))
        
        # Adicionar coluna bairro se não existir
        if 'bairro' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN bairro VARCHAR(100)"))
        
        # Adicionar coluna estado se não existir
        if 'estado' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN estado VARCHAR(2)"))
        
        # Adicionar coluna numero se não existir
        if 'numero' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN numero VARCHAR(20)"))
        
        # Adicionar coluna complemento se não existir
        if 'complemento' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN complemento VARCHAR(200)"))
        
        if 'funcao_id' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN funcao_id INTEGER"))
        
        # Adicionar coluna data_entrada_banda se não existir
        if 'data_entrada_banda' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN data_entrada_banda DATE"))
        
        # Adicionar coluna data_desligamento_banda se não existir
        if 'data_desligamento_banda' not in columns:
            db.session.execute(text("ALTER TABLE aluno ADD COLUMN data_desligamento_banda DATE"))

        presenca_result = db.session.execute(text("PRAGMA table_info(presenca)"))
        presenca_columns = [row[1] for row in presenca_result.fetchall()]
        if 'ensaio_id' not in presenca_columns:
            db.session.execute(text("ALTER TABLE presenca ADD COLUMN ensaio_id INTEGER"))
        if 'evento_id' not in presenca_columns:
            db.session.execute(text("ALTER TABLE presenca ADD COLUMN evento_id INTEGER"))
        if 'registrado_por_id' not in presenca_columns:
            db.session.execute(text("ALTER TABLE presenca ADD COLUMN registrado_por_id INTEGER"))
        if 'registrado_at' not in presenca_columns:
            db.session.execute(text("ALTER TABLE presenca ADD COLUMN registrado_at DATETIME"))

        ensaio_result = db.session.execute(text("PRAGMA table_info(ensaio)"))
        ensaio_columns = [row[1] for row in ensaio_result.fetchall()]
        if 'status' not in ensaio_columns:
            db.session.execute(text(
                "ALTER TABLE ensaio ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'AGENDADO'"
            ))
        
        db.session.commit()
    except Exception as e:
        print(f"Erro na migração: {e}")
        db.session.rollback()


def obter_autorizacao_foto_vigente(aluno_id, foto_path):
    """Registro de consentimento que cobre exatamente o arquivo de foto atual."""
    if not aluno_id or not foto_path:
        return None
    from .models import AutorizacaoFotoMenor

    return (
        AutorizacaoFotoMenor.query.filter_by(
            aluno_id=aluno_id,
            foto_path_coberto=foto_path,
        )
        .order_by(AutorizacaoFotoMenor.created_at.desc())
        .first()
    )


def registrar_autorizacao_foto_menor(aluno_id, foto_path, dados, user_id, request):
    """Persiste registro de consentimento e arquivo PNG da assinatura."""
    from .models import AutorizacaoFotoMenor

    assin = salvar_assinatura_data_url(dados["assinatura_data_url"], aluno_id)
    if not assin:
        return False
    row = AutorizacaoFotoMenor(
        aluno_id=aluno_id,
        foto_path_coberto=foto_path,
        responsavel_nome=dados["nome"],
        responsavel_parentesco=dados["parentesco"],
        responsavel_cpf=dados["cpf"],
        assinatura_path=assin,
        termo_versao=TERMO_AUTORIZACAO_FOTO_VERSAO,
        registrado_por_id=user_id,
        ip_origem=getattr(request, "remote_addr", None) or "",
    )
    db.session.add(row)
    return True


# Timeout de Sessão por Inatividade (15 minutos)
SESSION_TIMEOUT_MINUTES = 15


def update_activity():
    """Atualiza timestamp da última atividade na session."""
    session.modified = True
    session['last_activity'] = datetime.utcnow().isoformat()


def get_session_timeout_minutes():
    timeout = current_app.config.get('SESSION_TIMEOUT_MINUTES')
    if timeout is None:
        timeout = obter_configuracao_int('session_timeout_minutes', SESSION_TIMEOUT_MINUTES)

    try:
        return int(timeout)
    except (TypeError, ValueError):
        return SESSION_TIMEOUT_MINUTES


def session_timeout(f):
    """Decorator: Verifica inatividade > timeout → logout auto."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            last_activity_str = session.get('last_activity')
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    timeout_minutes = get_session_timeout_minutes()
                    if datetime.utcnow() - last_activity > timedelta(minutes=timeout_minutes):
                        logout_user()
                        flash(f'Sessão expirada por inatividade ({timeout_minutes} minutos). Faça login novamente.', 'warning')
                        return redirect(url_for('auth.login'))
                except ValueError:
                    # Timestamp inválido, reset
                    update_activity()
            else:
                update_activity()
        return f(*args, **kwargs)
    return decorated_function

