
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
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
    theme_preset = db.Column(db.String(20), nullable=False, default="padrao")
    font_scale = db.Column(db.String(20), nullable=False, default="padrao")

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    cartao_passe = db.relationship(
        'CartaoPasse',
        back_populates='aluno',
        uselist=False,
        cascade='all, delete-orphan',
    )
    cotas_mensais_passe = db.relationship(
        'CotaMensalPasse',
        back_populates='aluno',
        lazy=True,
        cascade='all, delete-orphan',
    )


class CartaoPasse(db.Model):
    __tablename__ = 'cartao_passe'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(
        db.Integer,
        db.ForeignKey('aluno.id'),
        nullable=False,
        unique=True,
        index=True,
    )
    numero_controle = db.Column(db.String(80), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    aluno = db.relationship('Aluno', back_populates='cartao_passe')


class CotaMensalPasse(db.Model):
    __tablename__ = 'cota_mensal_passe'
    __table_args__ = (
        UniqueConstraint(
            'aluno_id',
            'mes_referencia',
            name='uq_cota_mensal_passe_aluno_mes',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(
        db.Integer,
        db.ForeignKey('aluno.id'),
        nullable=False,
        index=True,
    )
    mes_referencia = db.Column(db.Date, nullable=False, index=True)
    quantidade_disponibilizada = db.Column(db.Integer, nullable=False, default=0)
    criado_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    aluno = db.relationship('Aluno', back_populates='cotas_mensais_passe')
    movimentos = db.relationship(
        'MovimentoPasse',
        back_populates='cota',
        lazy=True,
        cascade='all, delete-orphan',
    )


class MovimentoPasse(db.Model):
    __tablename__ = 'movimento_passe'

    id = db.Column(db.Integer, primary_key=True)
    cota_id = db.Column(db.Integer, db.ForeignKey('cota_mensal_passe.id'), nullable=False, index=True)
    presenca_id = db.Column(db.Integer, db.ForeignKey('presenca.id'), nullable=True, index=True)
    data_hora = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='CONSUMO')
    motivo = db.Column(db.Text)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    cota = db.relationship('CotaMensalPasse', back_populates='movimentos')
    presenca = db.relationship('Presenca', back_populates='movimentos_passe')
    registrado_por = db.relationship('User', foreign_keys=[registrado_por_id])


class HardDeleteAlunoLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False, index=True)
    deletado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    justificativa = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    data_matricula = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())


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
    data_emprestimo = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    data_devolucao = db.Column(db.Date, nullable=True)
    observacoes = db.Column(db.Text)


# Tabela: Uniformes
class Uniforme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_entrega = db.Column(db.Date)
    tamanho = db.Column(db.String(10))
    observacoes = db.Column(db.Text)


# Tabela: Atividades avulsas e treinamentos
class Atividade(db.Model):
    __tablename__ = 'atividade'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False, default='TREINAMENTO')
    titulo = db.Column(db.String(200), nullable=False)
    data_atividade = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.String(5))
    horario_fim = db.Column(db.String(5))
    local = db.Column(db.String(200))
    area = db.Column(db.String(120))
    responsavel = db.Column(db.String(150))
    observacoes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='REALIZADA')
    criado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    criado_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    presencas = db.relationship(
        'Presenca', back_populates='atividade', lazy=True, cascade='all, delete-orphan'
    )


# Tabela: Ensaios
class Ensaio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, default="ENSAIO")
    data_ensaio = db.Column(db.Date, nullable=False)
    horario = db.Column(db.String(20))
    local = db.Column(db.String(200))
    observacoes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="AGENDADO")
    criado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    criado_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    presencas = db.relationship(
        'Presenca', backref='ensaio', lazy=True, cascade='all, delete-orphan'
    )


# Tabela: Presenças
class Presenca(db.Model):
    __table_args__ = (
        CheckConstraint(
            "(ensaio_id IS NOT NULL AND evento_id IS NULL AND atividade_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NOT NULL AND atividade_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NULL AND atividade_id IS NOT NULL)",
            name="ck_presenca_uma_atividade",
        ),
        Index(
            "uq_presenca_aluno_ensaio", "aluno_id", "ensaio_id", unique=True,
            sqlite_where=db.text("ensaio_id IS NOT NULL"),
        ),
        Index(
            "uq_presenca_aluno_evento", "aluno_id", "evento_id", unique=True,
            sqlite_where=db.text("evento_id IS NOT NULL"),
        ),
        Index(
            "uq_presenca_aluno_atividade", "aluno_id", "atividade_id", unique=True,
            sqlite_where=db.text("atividade_id IS NOT NULL"),
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    ensaio_id = db.Column(db.Integer, db.ForeignKey('ensaio.id'), nullable=True, index=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=True, index=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividade.id'), nullable=True, index=True)
    data_presenca = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    presente = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    registrado_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    registrado_por = db.relationship('User', foreign_keys=[registrado_por_id])
    evento = db.relationship('Evento', foreign_keys=[evento_id], back_populates='presencas')
    atividade = db.relationship('Atividade', back_populates='presencas')
    movimentos_passe = db.relationship(
        'MovimentoPasse',
        back_populates='presenca',
        lazy=True,
        cascade='all, delete-orphan',
    )



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

    evento = db.relationship('Evento', back_populates='autorizacoes_evento')



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

    presencas = db.relationship(
        'Presenca', back_populates='evento', lazy=True, cascade='all, delete-orphan'
    )

    autorizacoes_evento = db.relationship(
        'AutorizacaoViagem',
        back_populates='evento',
        lazy=True,
    )


class GoogleCalendarSync(db.Model):
    __tablename__ = 'google_calendar_sync'
    __table_args__ = (
        CheckConstraint(
            "(ensaio_id IS NOT NULL AND evento_id IS NULL AND atividade_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NOT NULL AND atividade_id IS NULL) OR "
            "(ensaio_id IS NULL AND evento_id IS NULL AND atividade_id IS NOT NULL)",
            name="ck_google_calendar_sync_uma_atividade",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    ensaio_id = db.Column(db.Integer, db.ForeignKey('ensaio.id'), unique=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), unique=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividade.id'), unique=True)
    google_event_id = db.Column(db.String(255), nullable=False, unique=True)
    sincronizado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Comunicacao(db.Model):
    __tablename__ = 'comunicacao'

    id = db.Column(db.Integer, primary_key=True)
    assunto = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='aviso')
    publico = db.Column(db.String(50), default='geral')
    canal = db.Column(db.String(50), default='email')
    status = db.Column(db.String(20), default='rascunho')
    criado_por_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=True)
    ensaio_id = db.Column(db.Integer, db.ForeignKey('ensaio.id'), nullable=True)
    naipe_id = db.Column(db.Integer, db.ForeignKey('naipe.id'), nullable=True)
    contato_externo_id = db.Column(db.Integer, db.ForeignKey('contato_comunicacao.id'), nullable=True)
    destinatario_nome = db.Column(db.String(200), nullable=True)
    destinatario_email = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    enviado_em = db.Column(db.DateTime, nullable=True)

    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    destinatarios = db.relationship(
        'ComunicacaoDestinatario',
        back_populates='comunicacao',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    anexos = db.relationship(
        'ComunicacaoAnexo',
        back_populates='comunicacao',
        lazy=True,
        cascade='all, delete-orphan',
    )

    @property
    def alvo_descricao(self):
        if self.publico == 'responsaveis':
            return 'Responsáveis'
        if self.publico == 'geral':
            return 'Integrantes ativos'
        if self.publico == 'naipe':
            return 'Por naipe'
        if self.publico == 'externo':
            return 'Contatos externos'
        return self.publico.replace('_', ' ').title()


class ComunicacaoDestinatario(db.Model):
    __tablename__ = 'comunicacao_destinatario'

    id = db.Column(db.Integer, primary_key=True)
    comunicacao_id = db.Column(db.Integer, db.ForeignKey('comunicacao.id'), nullable=False)
    tipo_destinatario = db.Column(db.String(30), nullable=False, default='integrante')
    destinatario_id = db.Column(db.Integer, nullable=False)
    destinatario_nome = db.Column(db.String(200), nullable=True)
    destinatario_email = db.Column(db.String(200), nullable=True)
    canal = db.Column(db.String(30), nullable=False, default='email')
    status = db.Column(db.String(20), default='pendente')
    ultimo_erro = db.Column(db.Text, nullable=True)
    enviado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comunicacao = db.relationship('Comunicacao', back_populates='destinatarios')


class ComunicacaoAnexo(db.Model):
    __tablename__ = 'comunicacao_anexo'

    id = db.Column(db.Integer, primary_key=True)
    comunicacao_id = db.Column(db.Integer, db.ForeignKey('comunicacao.id'), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho = db.Column(db.String(500), nullable=False)
    tipo_mime = db.Column(db.String(120), nullable=True)
    tamanho = db.Column(db.Integer, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comunicacao = db.relationship('Comunicacao', back_populates='anexos')


class ContatoComunicacao(db.Model):
    __tablename__ = 'contato_comunicacao'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    telefone = db.Column(db.String(30), nullable=True)
    autorizacao_email = db.Column(db.Boolean, default=False)
    autorizacao_whatsapp = db.Column(db.Boolean, default=False)
    autorizacao_email_em = db.Column(db.DateTime, nullable=True)
    origem_autorizacao_email = db.Column(db.String(200), nullable=True)
    email_revogado_em = db.Column(db.DateTime, nullable=True)
    autorizacao_whatsapp_em = db.Column(db.DateTime, nullable=True)
    origem_autorizacao_whatsapp = db.Column(db.String(200), nullable=True)
    whatsapp_revogado_em = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

