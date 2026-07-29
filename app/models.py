
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


# ========================
# MODELO DE USUÁRIO (Auth)
# ========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)

    login_attempts = db.Column(db.Integer, default=0)
    blocked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class SistemaConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(1000), nullable=True)

    def __repr__(self):
        return f"<SistemaConfig {self.key}={self.value}>"


# ========================
# MODELOS DE BANDA MARCIAL
# ========================

# Tabela de referência: Naipe (seções da banda)
class Naipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    
    # Relacionamento com instrumentos
    instrumentos = db.relationship('Instrumento', backref='naipe', lazy=True)


# Tabela de referência: Funções na banda
class FuncaoBanda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_funcao = db.Column(db.String(100), nullable=False)


# Tabela de referência: Tipos de instrumento
class TipoInstrumento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    
    # Relacionamento com instrumentos
    instrumentos = db.relationship('Instrumento', backref='tipo', lazy=True)


# Tabela: Escolas
class Escola(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300))
    
    # Relacionamento com alunos
    alunos = db.relationship('AlunoEscola', backref='escola', lazy=True)


# Tabela: Alunos
class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    naturalidade = db.Column(db.String(100))
    cin_rg = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(20))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(300))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    foto_path = db.Column(db.String(500))
    ativo = db.Column(db.Boolean, default=True)
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(200))
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_banda.id'))
    funcao = db.relationship('FuncaoBanda', backref='alunos')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    data_entrada_banda = db.Column(db.Date, nullable=True)
    data_desligamento_banda = db.Column(db.Date, nullable=True)
    
    # Relacionamentos
    responsaveis = db.relationship('Responsavel', backref='aluno', lazy=True, cascade='all, delete-orphan')
    uniforme = db.relationship('Uniforme', backref='aluno', lazy=True, cascade='all, delete-orphan')
    presencas = db.relationship('Presenca', backref='aluno', lazy=True, cascade='all, delete-orphan')
    instrumentos = db.relationship('AlunoInstrumento', backref='aluno', lazy=True, cascade='all, delete-orphan')
    escolas = db.relationship('AlunoEscola', backref='aluno', lazy=True, cascade='all, delete-orphan')
    autorizacoes_foto = db.relationship(
        'AutorizacaoFotoMenor',
        back_populates='aluno',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class HardDeleteAlunoLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False, index=True)
    deletado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    justificativa = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AutorizacaoFotoMenor(db.Model):
    """Consentimento do responsável para armazenar imagem do menor (LGPD / ECA Digital — trilha em rede interna)."""
    __tablename__ = 'autorizacao_foto_menor'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False, index=True)
    foto_path_coberto = db.Column(db.String(500), nullable=False)
    responsavel_nome = db.Column(db.String(200), nullable=False)
    responsavel_parentesco = db.Column(db.String(40), nullable=False)
    responsavel_cpf = db.Column(db.String(14))
    assinatura_path = db.Column(db.String(500), nullable=False)
    termo_versao = db.Column(db.String(32), nullable=False)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_origem = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    aluno = db.relationship('Aluno', back_populates='autorizacoes_foto')
    registrado_por = db.relationship('User', foreign_keys=[registrado_por_id])


# Tabela: Responsáveis (pais/responsáveis)
class Responsavel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    nome_pai = db.Column(db.String(200))
    nome_mae = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(150))
    endereco = db.Column(db.String(300))


# Tabela: Relação Aluno-Escola
class AlunoEscola(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    data_matricula = db.Column(db.Date, default=datetime.utcnow().date)


# Tabela: Instrumentos
class Instrumento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipo_instrumento.id'))
    naipe_id = db.Column(db.Integer, db.ForeignKey('naipe.id'))
    patrimonio = db.Column(db.String(50), unique=True)
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    estado = db.Column(db.String(50))  # Novo, Bom, Regular, Ruim
    data_aquisicao = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamento com alunos
    alunos = db.relationship('AlunoInstrumento', backref='instrumento', lazy=True, cascade='all, delete-orphan')


# Tabela: Relação Aluno-Instrumento
class AlunoInstrumento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    instrumento_id = db.Column(db.Integer, db.ForeignKey('instrumento.id'), nullable=False)
    data_emprestimo = db.Column(db.Date, default=datetime.utcnow().date)
    data_devolucao = db.Column(db.Date, nullable=True)
    observacoes = db.Column(db.Text)


# Tabela: Uniformes
class Uniforme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_entrega = db.Column(db.Date)
    tamanho = db.Column(db.String(10))
    observacoes = db.Column(db.Text)


# Tabela: Presenças
class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_presenca = db.Column(db.Date, default=datetime.utcnow().date)
    presente = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)



# ========================
# Tabelas de Endereçamento
# ========================

class Cidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    codigo_ibge = db.Column(db.Integer)
    ddd = db.Column(db.String(2))

    # relacionamento com logradouros
    logradouros = db.relationship(
        'Logradouro',
        backref='cidade',
        lazy=True,
        cascade='all, delete-orphan'
    )


class Logradouro(db.Model):
    cep = db.Column(db.String(11), index=True, nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))
    descricao = db.Column(db.String(100), nullable=False)
    cidade_id = db.Column(db.Integer, db.ForeignKey('cidade.id'), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    complemento = db.Column(db.String(100))
    descricao_sem_numero = db.Column(db.String(100))
    descricao_cidade = db.Column(db.String(100))
    codigo_cidade_ibge = db.Column(db.Integer)
    descricao_bairro = db.Column(db.String(100))


# ===============================================
# |            tabela autorização               |
# ===============================================
class AutorizacaoViagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=False)
    autorizado = db.Column(db.Boolean, default=False)
    data_autorizacao = db.Column(db.Date)
    observacoes = db.Column(db.Text)


    aluno = db.relationship('Aluno', backref='autorizacoes')

    evento = db.relationship('Evento', backref=db.backref('evento_viagem', uselist=False))



# ===============================================
# |              tabela Evento                  |
# ===============================================
class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cidade = db.Column(db.String(100))
    data_evento = db.Column(db.Date)
    nome_evento = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    responsavel = db.Column(db.String(150))
    taxa = db.Column(db.Float)
    isento = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="A_CONFIRMAR")



    autorizacoes_evento = db.relationship('AutorizacaoViagem', backref=db.backref('evento_aut', uselist=False), lazy=True)





