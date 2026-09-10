from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import timedelta
from .models import (
    User,
    Aluno,
    Escola,
    Instrumento,
    TipoInstrumento,
    Naipe,
    FuncaoBanda,
    Responsavel,
    Uniforme,
    AlunoInstrumento,
    AlunoEscola,
    Ensaio,
    Presenca,
    Evento,
    Logradouro,
    Cidade,
)
from . import db
from .utils import (
    admin_required,
    profissional_required,
    SENHA_PADRAO,
    normalizar_campo_texto,
    normalizar_telefone,
    consentimento_foto_obrigatorio,
    validar_payload_autorizacao_foto,
    registrar_autorizacao_foto_menor,
    obter_autorizacao_foto_vigente,
    TERMO_AUTORIZACAO_FOTO_VERSAO,
    session_timeout,
    update_activity,
    validar_senha_complexidade,
    limpar_logs_antigos,
    definir_configuracao,
)

from .backup import (
    listar_backups,
    criar_backup,
    restaurar_backup,
    excluir_backup,
    validar_backup,
    obter_caminho_backup,
)
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy import text

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
@session_timeout
def dashboard():
    update_activity()
    stats = {
        'total_alunos': Aluno.query.count(),
        'alunos_ativos': Aluno.query.filter_by(ativo=True).count(),
        'total_escolas': Escola.query.count(),
        'instrumentos_ativos': Instrumento.query.filter_by(ativo=True).count(),
        'usuarios': User.query.filter_by(is_active=True).count(),
        'usuarios_admin': User.query.filter_by(is_admin=True, is_active=True).count()
    }
    return render_template("dashboard.html", stats=stats)


@main_bp.route("/admin")
@login_required
@admin_required
def painel_admin():
    return render_template("dashboard.html")


@main_bp.route("/admin/eventos")
@login_required
@profissional_required
def listar_eventos():
    eventos = Evento.query.order_by(Evento.data_evento.desc(), Evento.id.desc()).all()
    return render_template("admin_eventos.html", eventos=eventos)


@main_bp.route("/admin/evento/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_evento():
    if request.method == "POST":
        nome_evento = normalizar_campo_texto(request.form.get("nome_evento"))
        data_evento = request.form.get("data_evento")
        if not nome_evento:
            flash("Informe o nome do evento.", "danger")
            return redirect(url_for("main.criar_evento"))
        try:
            data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Informe uma data válida para o evento.", "danger")
            return redirect(url_for("main.criar_evento"))

        evento = Evento(
            nome_evento=nome_evento,
            data_evento=data_evento,
            cidade=normalizar_campo_texto(request.form.get("cidade")),
            responsavel=normalizar_campo_texto(request.form.get("responsavel")),
            telefone=normalizar_telefone(request.form.get("telefone")),
            status=request.form.get("status") or "A_CONFIRMAR",
        )
        db.session.add(evento)
        db.session.commit()
        flash("Evento criado. Registre a lista de chamada.", "success")
        return redirect(url_for("main.registrar_presenca_evento", evento_id=evento.id))

    return render_template("admin_evento_form.html", evento=None)


@main_bp.route("/admin/evento/<int:evento_id>/edit", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    if request.method == "POST":
        nome_evento = normalizar_campo_texto(request.form.get("nome_evento"))
        try:
            data_evento = datetime.strptime(
                request.form.get("data_evento"), "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            flash("Informe uma data válida para o evento.", "danger")
            return redirect(url_for("main.editar_evento", evento_id=evento.id))
        if not nome_evento:
            flash("Informe o nome do evento.", "danger")
            return redirect(url_for("main.editar_evento", evento_id=evento.id))
        evento.nome_evento = nome_evento
        evento.data_evento = data_evento
        evento.cidade = normalizar_campo_texto(request.form.get("cidade"))
        evento.responsavel = normalizar_campo_texto(request.form.get("responsavel"))
        evento.telefone = normalizar_telefone(request.form.get("telefone"))
        evento.status = request.form.get("status") or "A_CONFIRMAR"
        db.session.commit()
        flash("Evento atualizado com sucesso.", "success")
        return redirect(url_for("main.listar_eventos"))
    return render_template("admin_evento_form.html", evento=evento)


@main_bp.route("/admin/evento/<int:evento_id>/cancel", methods=["POST"])
@login_required
@profissional_required
def cancelar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    evento.status = "CANCELADO"
    db.session.commit()
    flash("Evento cancelado. O histórico de presença foi preservado.", "warning")
    return redirect(url_for("main.listar_eventos"))


@main_bp.route("/admin/ensaios")
@login_required
@profissional_required
def listar_ensaios():
    ensaios = Ensaio.query.order_by(
        Ensaio.data_ensaio.desc(), Ensaio.id.desc()
    ).all()
    return render_template("admin_ensaios.html", ensaios=ensaios)


@main_bp.route("/admin/ensaio/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_ensaio():
    if request.method == "POST":
        titulo = normalizar_campo_texto(request.form.get("titulo")) or "ENSAIO"
        data_ensaio = request.form.get("data_ensaio")
        try:
            data_ensaio = datetime.strptime(data_ensaio, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Informe uma data válida para o ensaio.", "danger")
            return redirect(url_for("main.criar_ensaio"))

        ensaio = Ensaio(
            titulo=titulo,
            data_ensaio=data_ensaio,
            horario=request.form.get("horario", "").strip() or None,
            local=normalizar_campo_texto(request.form.get("local")),
            observacoes=request.form.get("observacoes", "").strip() or None,
            status="AGENDADO",
            criado_por_id=current_user.id,
        )
        db.session.add(ensaio)
        db.session.commit()
        flash("Ensaio criado. Registre a chamada para iniciar a presença.", "success")
        return redirect(url_for("main.registrar_presenca", ensaio_id=ensaio.id))

    return render_template("admin_ensaio_form.html", ensaio=None)


@main_bp.route("/admin/ensaio/<int:ensaio_id>/edit", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_ensaio(ensaio_id):
    ensaio = Ensaio.query.get_or_404(ensaio_id)
    if request.method == "POST":
        titulo = normalizar_campo_texto(request.form.get("titulo")) or "ENSAIO"
        try:
            data_ensaio = datetime.strptime(
                request.form.get("data_ensaio"), "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            flash("Informe uma data válida para o ensaio.", "danger")
            return redirect(url_for("main.editar_ensaio", ensaio_id=ensaio.id))
        ensaio.titulo = titulo
        ensaio.data_ensaio = data_ensaio
        ensaio.horario = request.form.get("horario", "").strip() or None
        ensaio.local = normalizar_campo_texto(request.form.get("local"))
        ensaio.observacoes = request.form.get("observacoes", "").strip() or None
        ensaio.status = request.form.get("status") or "AGENDADO"
        db.session.commit()
        flash("Ensaio atualizado com sucesso.", "success")
        return redirect(url_for("main.listar_ensaios"))
    return render_template("admin_ensaio_form.html", ensaio=ensaio)


@main_bp.route("/admin/ensaio/<int:ensaio_id>/cancel", methods=["POST"])
@login_required
@profissional_required
def cancelar_ensaio(ensaio_id):
    ensaio = Ensaio.query.get_or_404(ensaio_id)
    ensaio.status = "CANCELADO"
    db.session.commit()
    flash("Ensaio cancelado. O histórico de presença foi preservado.", "warning")
    return redirect(url_for("main.listar_ensaios"))


@main_bp.route("/admin/ensaio/<int:ensaio_id>/presenca", methods=["GET", "POST"])
@login_required
@profissional_required
def registrar_presenca(ensaio_id):
    ensaio = Ensaio.query.get_or_404(ensaio_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == "POST":
        for aluno in alunos:
            status = request.form.get(f"presenca_{aluno.id}", "ausente")
            presente = status == "presente"
            observacoes = "JUSTIFICADO" if status == "justificado" else None
            registro = Presenca.query.filter_by(
                aluno_id=aluno.id, ensaio_id=ensaio.id
            ).first()
            if registro is None:
                registro = Presenca(aluno_id=aluno.id, ensaio_id=ensaio.id)
                db.session.add(registro)
            registro.presente = presente
            registro.observacoes = observacoes
            registro.data_presenca = ensaio.data_ensaio
            registro.registrado_por_id = current_user.id
            registro.registrado_at = datetime.utcnow()

        db.session.commit()
        flash("Lista de presença salva com sucesso.", "success")
        return redirect(url_for("main.registrar_presenca", ensaio_id=ensaio.id))

    registros = {
        registro.aluno_id: registro
        for registro in Presenca.query.filter_by(ensaio_id=ensaio.id).all()
    }
    grupos = {}
    for aluno in alunos:
        associacao = next(
            (item for item in aluno.instrumentos if item.data_devolucao is None), None
        )
        grupo = associacao.instrumento.nome if associacao and associacao.instrumento else "SEM INSTRUMENTO"
        grupos.setdefault(grupo, []).append(aluno)

    return render_template(
        "admin_presenca.html",
        atividade_titulo=ensaio.titulo,
        atividade_data=ensaio.data_ensaio,
        atividade_horario=ensaio.horario,
        atividade_local=ensaio.local,
        atividade_url=url_for("main.listar_ensaios"),
        grupos=sorted(grupos.items()),
        registros=registros,
    )


@main_bp.route("/admin/evento/<int:evento_id>/presenca", methods=["GET", "POST"])
@login_required
@profissional_required
def registrar_presenca_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == "POST":
        for aluno in alunos:
            status = request.form.get(f"presenca_{aluno.id}", "ausente")
            registro = Presenca.query.filter_by(
                aluno_id=aluno.id, evento_id=evento.id
            ).first()
            if registro is None:
                registro = Presenca(aluno_id=aluno.id, evento_id=evento.id)
                db.session.add(registro)
            registro.presente = status == "presente"
            registro.observacoes = "JUSTIFICADO" if status == "justificado" else None
            registro.data_presenca = evento.data_evento
            registro.registrado_por_id = current_user.id
            registro.registrado_at = datetime.utcnow()
        db.session.commit()
        flash("Lista de presença do evento salva com sucesso.", "success")
        return redirect(url_for("main.registrar_presenca_evento", evento_id=evento.id))

    registros = {
        registro.aluno_id: registro
        for registro in Presenca.query.filter_by(evento_id=evento.id).all()
    }
    grupos = {}
    for aluno in alunos:
        associacao = next(
            (item for item in aluno.instrumentos if item.data_devolucao is None), None
        )
        grupo = associacao.instrumento.nome if associacao and associacao.instrumento else "SEM INSTRUMENTO"
        grupos.setdefault(grupo, []).append(aluno)

    return render_template(
        "admin_presenca.html",
        atividade_titulo=evento.nome_evento,
        atividade_data=evento.data_evento,
        atividade_horario=None,
        atividade_local=evento.cidade,
        atividade_url=url_for("main.listar_eventos"),
        grupos=sorted(grupos.items()),
        registros=registros,
    )


@main_bp.route("/admin/evento/<int:evento_id>/relatorio")
@login_required
@profissional_required
def relatorio_presenca_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    registros = Presenca.query.filter_by(evento_id=evento.id).all()
    registros_por_aluno = {registro.aluno_id: registro for registro in registros}

    grupos = {}
    for aluno in alunos:
        associacao = next(
            (item for item in aluno.instrumentos if item.data_devolucao is None), None
        )
        instrumento = associacao.instrumento if associacao else None
        grupo = instrumento.nome if instrumento else "SEM INSTRUMENTO"
        grupos.setdefault(grupo, []).append({
            "aluno": aluno,
            "registro": registros_por_aluno.get(aluno.id),
        })

    return render_template(
        "admin_relatorio_presenca_evento.html",
        evento=evento,
        grupos=sorted(grupos.items(), key=lambda item: item[0].casefold()),
        total_alunos=len(alunos),
        total_presentes=sum(
            1 for registro in registros if registro.presente
        ),
        total_justificados=sum(
            1 for registro in registros if registro.observacoes == "JUSTIFICADO"
        ),
        total_registrados=len(registros),
    )


@main_bp.route("/admin/presencas/historico")
@login_required
@profissional_required
def historico_presencas():
    aluno_id = request.args.get("aluno_id", type=int)
    alunos = Aluno.query.order_by(Aluno.nome).all()
    registros_query = Presenca.query.filter(
        db.or_(Presenca.ensaio_id.isnot(None), Presenca.evento_id.isnot(None))
    )
    if aluno_id:
        registros_query = registros_query.filter_by(aluno_id=aluno_id)
    registros = registros_query.order_by(Presenca.data_presenca.desc()).all()

    estatisticas = {}
    for aluno in alunos:
        registros_aluno = [item for item in registros if item.aluno_id == aluno.id]
        total = len(registros_aluno)
        presentes = sum(1 for item in registros_aluno if item.presente)
        estatisticas[aluno.id] = {
            "total": total,
            "presentes": presentes,
            "percentual": round((presentes / total) * 100, 1) if total else None,
        }

    return render_template(
        "admin_historico_presencas.html",
        alunos=alunos,
        aluno_id=aluno_id,
        registros=registros,
        estatisticas=estatisticas,
    )


@main_bp.route("/admin/presencas/diaria")
@login_required
@profissional_required
def relatorio_presenca_diaria():
    data_str = request.args.get("data", "")
    try:
        data_relatorio = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        data_relatorio = datetime.utcnow().date()

    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    registros = (
        Presenca.query.filter_by(data_presenca=data_relatorio)
        .order_by(Presenca.registrado_at.desc(), Presenca.id.desc())
        .all()
    )
    registros_por_aluno = {}
    for registro in registros:
        registros_por_aluno.setdefault(registro.aluno_id, registro)

    grupos = {}
    for aluno in alunos:
        associacao = next(
            (item for item in aluno.instrumentos if item.data_devolucao is None), None
        )
        instrumento = associacao.instrumento if associacao else None
        grupo = instrumento.nome if instrumento else "SEM INSTRUMENTO"
        grupos.setdefault(grupo, []).append({
            "aluno": aluno,
            "registro": registros_por_aluno.get(aluno.id),
        })

    atividades = []
    atividades.extend(
        f"Ensaio: {ensaio.titulo}"
        + (f" · {ensaio.local}" if ensaio.local else "")
        for ensaio in Ensaio.query.filter_by(data_ensaio=data_relatorio).all()
    )
    atividades.extend(
        f"Evento: {evento.nome_evento}"
        + (f" · {evento.cidade}" if evento.cidade else "")
        for evento in Evento.query.filter_by(data_evento=data_relatorio).all()
    )

    return render_template(
        "admin_relatorio_presenca_diaria.html",
        data_relatorio=data_relatorio,
        grupos=sorted(grupos.items(), key=lambda item: item[0].casefold()),
        atividades=atividades,
        total_alunos=len(alunos),
        total_presentes=sum(
            1 for registro in registros_por_aluno.values() if registro.presente
        ),
    )


@main_bp.route("/admin/users")
@login_required
@admin_required
@session_timeout
def listar_usuarios():
    update_activity()
    usuarios = User.query.all()
    return render_template("admin_users.html", usuarios=usuarios)


@main_bp.route("/admin/user/create", methods=["GET", "POST"])
@login_required
@admin_required
def criar_usuario():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        is_admin = request.form.get("is_admin") == "on"

        if not username or not password:
            flash("Usuário e senha são obrigatórios.")
            return redirect(url_for("main.criar_usuario"))

        if User.query.filter_by(username=username).first():
            flash("Usuário já existe.")
            return redirect(url_for("main.criar_usuario"))

        valida, mensagem = validar_senha_complexidade(password)
        if not valida:
            flash(mensagem)
            return redirect(url_for("main.criar_usuario"))

        novo_usuario = User(
            username=username,
            is_admin=is_admin,
            must_change_password=True
        )
        novo_usuario.set_password(password)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário criado com sucesso!")
        return redirect(url_for("main.listar_usuarios"))

    return render_template("admin_user_form.html", usuario=None, titulo="Criar Usuário")


@main_bp.route("/admin/user/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(user_id):
    usuario = User.query.get_or_404(user_id)
    
    # Proteção para usuário 'admin'
    if usuario.username == 'admin' and usuario.id != current_user.id:
        flash("Usuário 'admin' é protegido contra alterações para garantir manutenção do sistema.", "warning")
        return redirect(url_for("main.listar_usuarios"))

    if request.method == "POST":
        # username NÃO é atualizado para preservar acesso - apenas em criação
        is_admin = request.form.get("is_admin") == "on"
        nova_senha = request.form.get("password")

        usuario.is_admin = is_admin

        if nova_senha:
            valida, mensagem = validar_senha_complexidade(nova_senha)
            if not valida:
                flash(mensagem)
                return redirect(url_for("main.editar_usuario", user_id=user_id))
            usuario.set_password(nova_senha)
            usuario.must_change_password = True

        db.session.commit()

        flash("Usuário atualizado com sucesso. Username preservado para segurança de acesso.")
        return redirect(url_for("main.listar_usuarios"))

    return render_template("admin_user_form.html", usuario=usuario, titulo="Editar Usuário")


@main_bp.route("/admin/user/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def excluir_usuario(user_id):
    usuario = User.query.get_or_404(user_id)
    
    # Proteção para usuário 'admin'
    if usuario.username == 'admin' and usuario.id != current_user.id:
        flash("Usuário 'admin' não pode ser excluído para garantir manutenção do sistema.", "warning")
        return redirect(url_for("main.listar_usuarios"))

    if usuario.id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.")
        return redirect(url_for("main.listar_usuarios"))

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuário excluído com sucesso!")
    return redirect(url_for("main.listar_usuarios"))


@main_bp.route("/admin/reset-password/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def resetar_senha(user_id):
    user = User.query.get_or_404(user_id)
    
    # Proteção para usuário 'admin'
    if user.username == 'admin' and user.id != current_user.id:
        flash("Senha do usuário 'admin' não pode ser resetada para garantir manutenção do sistema.", "warning")
        return redirect(url_for("main.listar_usuarios"))

    user.set_password(SENHA_PADRAO)
    user.must_change_password = True
    db.session.commit()

    flash(f"Senha redefinida para '{SENHA_PADRAO}'.")
    return redirect(url_for("main.listar_usuarios"))


@main_bp.route("/admin/toggle-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_usuario(user_id):
    user = User.query.get_or_404(user_id)
    
    # Proteção para usuário 'admin'
    if user.username == 'admin' and user.id != current_user.id:
        flash("Usuário 'admin' não pode ser bloqueado para garantir manutenção do sistema.", "warning")
        return redirect(url_for("main.listar_usuarios"))

    if user.id == current_user.id:
        flash("Você não pode bloquear seu próprio usuário.")
        return redirect(url_for("main.listar_usuarios"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "ativado" if user.is_active else "bloqueado"
    flash(f"Usuário {status}.")
    return redirect(url_for("main.listar_usuarios"))


# ========================
# ROTAS PARA GESTÃO DE ALUNOS (INTEGRANTES DA BANDA)
# ========================

@main_bp.route("/admin/alunos")
@login_required
def listar_alunos():
    """Lista todos os alunos com filtros opcionais"""
    nome_busca = request.args.get('busca', '')
    ativo_filter = request.args.get('ativo', '')
    
    query = Aluno.query
    
    if nome_busca:
        query = query.filter(Aluno.nome.ilike(f'%{nome_busca}%'))
    
    if ativo_filter == '1':
        query = query.filter(Aluno.ativo == True)
    elif ativo_filter == '0':
        query = query.filter(Aluno.ativo == False)
    
    alunos = query.order_by(Aluno.nome).all()
    
    return render_template("admin_alunos.html", 
                           alunos=alunos, 
                           busca=nome_busca, 
                           ativo_filter=ativo_filter)


@main_bp.route("/admin/aluno/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_aluno():
    """Cria um novo aluno (integrante da banda)"""
    escolas = Escola.query.all()
    funcoes = FuncaoBanda.query.all()
    instrumentos = Instrumento.query.filter_by(ativo=True).all()
    tipos_instrumento = TipoInstrumento.query.all()
    naipes = Naipe.query.all()
    
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        data_nascimento = request.form.get("data_nascimento")
        funcao_id = request.form.get("funcao_id")
        naturalidade = normalizar_campo_texto(request.form.get("naturalidade"))
        cin_rg = request.form.get("cin_rg").upper().strip()
        email = request.form.get("email").lower().strip() if request.form.get("email") else None
        telefone = normalizar_telefone(request.form.get("telefone"))
        cep = request.form.get("cep")
        endereco = normalizar_campo_texto(request.form.get("endereco"))
        numero = normalizar_campo_texto(request.form.get("numero"))
        complemento = normalizar_campo_texto(request.form.get("complemento"))
        bairro = normalizar_campo_texto(request.form.get("bairro"))
        cidade = normalizar_campo_texto(request.form.get("cidade"))
        estado = request.form.get("estado").upper().strip() if request.form.get("estado") else None
        data_entrada_banda = request.form.get("data_entrada_banda")
        data_desligamento_banda = request.form.get("data_desligamento_banda")
        
        if not nome:
            flash("Nome é obrigatório.")
            return redirect(url_for("main.criar_aluno"))
        
        if cin_rg and Aluno.query.filter_by(cin_rg=cin_rg).first():
            flash("RG já cadastrado.")
            return redirect(url_for("main.criar_aluno"))
        
        data_nasc = None
        if data_nascimento:
            try:
                data_nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de nascimento inválida.")
                return redirect(url_for("main.criar_aluno"))

        data_entrada = None
        if data_entrada_banda:
            try:
                data_entrada = datetime.strptime(data_entrada_banda, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de entrada na banda inválida.")
                return redirect(url_for("main.criar_aluno"))

        data_desligamento = None
        if data_desligamento_banda:
            try:
                data_desligamento = datetime.strptime(data_desligamento_banda, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de desligamento da banda inválida.")
                return redirect(url_for("main.criar_aluno"))

        # Define o status ativo baseado na data de desligamento
        ativo = data_desligamento is None

        foto = request.files.get("foto")
        tem_upload_novo = bool(foto and foto.filename)
        precisa_aut_foto = consentimento_foto_obrigatorio(
            data_nasc, tem_upload_novo, None, None
        )
        dados_auth_foto = None
        if precisa_aut_foto:
            ok_auth, payload_auth = validar_payload_autorizacao_foto(request.form)
            if not ok_auth:
                flash(payload_auth)
                return redirect(url_for("main.criar_aluno"))
            dados_auth_foto = payload_auth

        novo_aluno = Aluno(
            nome=nome,
            data_nascimento=data_nasc,
            naturalidade=naturalidade,
            cin_rg=cin_rg,
            email=email,
            telefone=telefone,
            cep=cep,
            endereco=endereco,
            numero=numero,
            complemento=complemento,
            funcao_id=funcao_id,
            data_entrada_banda=data_entrada,
            data_desligamento_banda=data_desligamento,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            ativo=ativo
        )
        db.session.add(novo_aluno)
        db.session.flush()

        if foto and foto.filename:
            foto_path = salvar_foto_aluno(foto, novo_aluno.id)
            if foto_path:
                novo_aluno.foto_path = foto_path

        if precisa_aut_foto:
            if not novo_aluno.foto_path:
                db.session.rollback()
                flash(
                    "Para menor de 18 anos é obrigatório salvar uma foto válida junto com a autorização assinada."
                )
                return redirect(url_for("main.criar_aluno"))
            if not registrar_autorizacao_foto_menor(
                novo_aluno.id,
                novo_aluno.foto_path,
                dados_auth_foto,
                current_user.id,
                request,
            ):
                db.session.rollback()
                flash("Não foi possível registrar a assinatura digital. Tente novamente.")
                return redirect(url_for("main.criar_aluno"))

        nome_pai = request.form.get("nome_pai")
        nome_mae = request.form.get("nome_mae")
        telefone_responsavel = request.form.get("telefone_responsavel")
        email_responsavel = request.form.get("email_responsavel")
        endereco_responsavel = request.form.get("endereco_responsavel")
        
        if nome_pai or nome_mae or telefone_responsavel:
            responsavel = Responsavel(
                aluno_id=novo_aluno.id,
                nome_pai=nome_pai,
                nome_mae=nome_mae,
                telefone=telefone_responsavel,
                email=email_responsavel,
                endereco=endereco_responsavel
            )
            db.session.add(responsavel)
        
        escola_id = request.form.get("escola_id")
        if escola_id:
            aluno_escola = AlunoEscola(
                aluno_id=novo_aluno.id,
                escola_id=int(escola_id)
            )
            db.session.add(aluno_escola)

        instrumento_id = request.form.get("instrumento_id")
        if instrumento_id:
            instrumento = Instrumento.query.filter_by(
                id=instrumento_id, ativo=True
            ).first()
            if not instrumento:
                db.session.rollback()
                flash("Instrumento selecionado é inválido ou está inativo.")
                return redirect(url_for("main.criar_aluno"))
            db.session.add(AlunoInstrumento(
                aluno_id=novo_aluno.id,
                instrumento_id=instrumento.id,
                observacoes=normalizar_campo_texto(
                    request.form.get("instrumento_observacoes")
                ),
            ))
        
        db.session.commit()
        
        flash("Aluno criado com sucesso!")
        return redirect(url_for("main.listar_alunos"))
    
    return render_template(
        "admin_aluno_form.html",
        aluno=None,
        titulo="Novo Integrante",
        funcoes=funcoes,
        escolas=escolas,
        instrumentos=instrumentos,
        tipos_instrumento=tipos_instrumento,
        naipes=naipes,
        termo_autorizacao_foto_versao=TERMO_AUTORIZACAO_FOTO_VERSAO,
        pendente_autorizacao_foto=False,
        autorizacao_foto_registrada=None,
        exige_nova_assinatura_no_envio=True,
    )


@main_bp.route("/admin/aluno/edit/<int:aluno_id>", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    
    escolas = Escola.query.all()
    funcoes = FuncaoBanda.query.all()
    instrumentos = Instrumento.query.filter_by(ativo=True).all()
    associacao_instrumento_atual = AlunoInstrumento.query.filter_by(
        aluno_id=aluno.id, data_devolucao=None
    ).first()
    if (
        associacao_instrumento_atual
        and associacao_instrumento_atual.instrumento
        and associacao_instrumento_atual.instrumento not in instrumentos
    ):
        instrumentos.append(associacao_instrumento_atual.instrumento)
    tipos_instrumento = TipoInstrumento.query.all()
    naipes = Naipe.query.all()
    
    if request.method == "POST":
        funcao_id = request.form.get("funcao_id")
        nome = normalizar_campo_texto(request.form.get("nome"))
        data_nascimento = request.form.get("data_nascimento")
        naturalidade = normalizar_campo_texto(request.form.get("naturalidade"))
        cin_rg = request.form.get("cin_rg").upper().strip()
        email = request.form.get("email").lower().strip() if request.form.get("email") else None
        telefone = normalizar_telefone(request.form.get("telefone"))
        cep = request.form.get("cep")
        endereco = normalizar_campo_texto(request.form.get("endereco"))
        numero = normalizar_campo_texto(request.form.get("numero"))
        complemento = normalizar_campo_texto(request.form.get("complemento"))
        bairro = normalizar_campo_texto(request.form.get("bairro"))
        cidade = normalizar_campo_texto(request.form.get("cidade"))
        estado = request.form.get("estado").upper().strip() if request.form.get("estado") else None
        data_entrada_banda = request.form.get("data_entrada_banda")
        data_desligamento_banda = request.form.get("data_desligamento_banda")
        
        if not nome:
            flash("Nome é obrigatório.")
            return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))
        
        if cin_rg:
            aluno_existente = Aluno.query.filter_by(cin_rg=cin_rg).first()
            if aluno_existente and aluno_existente.id != aluno_id:
                flash("RG já cadastrado para outro aluno.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))
        
        data_nasc = None
        if data_nascimento:
            try:
                data_nasc = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de nascimento inválida.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        data_entrada = None
        if data_entrada_banda:
            try:
                data_entrada = datetime.strptime(data_entrada_banda, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de entrada na banda inválida.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        data_desligamento = None
        if data_desligamento_banda:
            try:
                data_desligamento = datetime.strptime(data_desligamento_banda, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de desligamento da banda inválida.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        # Define o status ativo baseado na data de desligamento
        ativo = data_desligamento is None

        foto = request.files.get("foto")
        tem_upload_novo = bool(foto and foto.filename)
        precisa_aut_foto = consentimento_foto_obrigatorio(
            data_nasc, tem_upload_novo, aluno.id, aluno.foto_path
        )
        dados_auth_foto = None
        if precisa_aut_foto:
            ok_auth, payload_auth = validar_payload_autorizacao_foto(request.form)
            if not ok_auth:
                flash(payload_auth)
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))
            dados_auth_foto = payload_auth

        aluno.nome = nome
        aluno.data_nascimento = data_nasc
        aluno.naturalidade = naturalidade
        aluno.cin_rg = cin_rg
        aluno.email = email
        aluno.telefone = telefone
        aluno.cep = cep
        aluno.endereco = endereco
        aluno.numero = numero
        aluno.complemento = complemento
        aluno.funcao_id = funcao_id
        aluno.data_entrada_banda = data_entrada
        aluno.data_desligamento_banda = data_desligamento
        aluno.ativo = ativo
        aluno.bairro = bairro
        aluno.cidade = cidade
        aluno.estado = estado

        if foto and foto.filename:
            foto_path = salvar_foto_aluno(foto, aluno.id)
            if foto_path:
                aluno.foto_path = foto_path

        if precisa_aut_foto:
            if not aluno.foto_path:
                db.session.rollback()
                flash(
                    "É necessário manter ou enviar uma foto válida junto com a autorização do responsável."
                )
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))
            if not registrar_autorizacao_foto_menor(
                aluno.id,
                aluno.foto_path,
                dados_auth_foto,
                current_user.id,
                request,
            ):
                db.session.rollback()
                flash("Não foi possível registrar a assinatura digital. Tente novamente.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        nome_pai = request.form.get("nome_pai")
        nome_mae = request.form.get("nome_mae")
        telefone_responsavel = request.form.get("telefone_responsavel")
        email_responsavel = request.form.get("email_responsavel")
        endereco_responsavel = request.form.get("endereco_responsavel")
        
        responsavel = Responsavel.query.filter_by(aluno_id=aluno.id).first()
        
        if responsavel:
            responsavel.nome_pai = nome_pai
            responsavel.nome_mae = nome_mae
            responsavel.telefone = telefone_responsavel
            responsavel.email = email_responsavel
            responsavel.endereco = endereco_responsavel
        elif nome_pai or nome_mae or telefone_responsavel:
            responsavel = Responsavel(
                aluno_id=aluno.id,
                nome_pai=nome_pai,
                nome_mae=nome_mae,
                telefone=telefone_responsavel,
                email=email_responsavel,
                endereco=endereco_responsavel
            )
            db.session.add(responsavel)
        
        escola_id = request.form.get("escola_id")
        
        AlunoEscola.query.filter_by(aluno_id=aluno.id).delete()
        
        if escola_id:
            aluno_escola = AlunoEscola(
                aluno_id=aluno.id,
                escola_id=int(escola_id)
            )
            db.session.add(aluno_escola)

        instrumento_id = request.form.get("instrumento_id")
        instrumento_atual = AlunoInstrumento.query.filter_by(
            aluno_id=aluno.id, data_devolucao=None
        ).first()
        instrumento_novo = None
        if instrumento_id:
            instrumento_novo = Instrumento.query.filter_by(
                id=instrumento_id, ativo=True
            ).first()
            if not instrumento_novo:
                db.session.rollback()
                flash("Instrumento selecionado é inválido ou está inativo.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        if instrumento_atual and (
            not instrumento_novo or instrumento_atual.instrumento_id != instrumento_novo.id
        ):
            instrumento_atual.data_devolucao = datetime.utcnow().date()

        if instrumento_novo and (
            not instrumento_atual or instrumento_atual.instrumento_id != instrumento_novo.id
        ):
            db.session.add(AlunoInstrumento(
                aluno_id=aluno.id,
                instrumento_id=instrumento_novo.id,
                observacoes=normalizar_campo_texto(
                    request.form.get("instrumento_observacoes")
                ),
            ))
        elif instrumento_atual:
            instrumento_atual.observacoes = normalizar_campo_texto(
                request.form.get("instrumento_observacoes")
            )
        
        db.session.commit()
        
        flash("Aluno atualizado com sucesso!")
        return redirect(url_for("main.listar_alunos"))

    pendente_autorizacao_foto = consentimento_foto_obrigatorio(
        aluno.data_nascimento, False, aluno.id, aluno.foto_path
    )
    autorizacao_foto_registrada = obter_autorizacao_foto_vigente(aluno.id, aluno.foto_path)
    exige_nova_assinatura_no_envio = pendente_autorizacao_foto or (
        bool(aluno.foto_path) and autorizacao_foto_registrada is None
    )

    return render_template(
        "admin_aluno_form.html",
        aluno=aluno,
        titulo="Editar Integrante",
        funcoes=funcoes,
        escolas=escolas,
        instrumentos=instrumentos,
        tipos_instrumento=tipos_instrumento,
        naipes=naipes,
        termo_autorizacao_foto_versao=TERMO_AUTORIZACAO_FOTO_VERSAO,
        pendente_autorizacao_foto=pendente_autorizacao_foto,
        autorizacao_foto_registrada=autorizacao_foto_registrada,
        exige_nova_assinatura_no_envio=exige_nova_assinatura_no_envio,
    )


@main_bp.route("/admin/aluno/toggle/<int:aluno_id>", methods=["POST"])
@login_required
@profissional_required
def toggle_aluno(aluno_id):
    """Ativa ou inativa um aluno"""
    aluno = Aluno.query.get_or_404(aluno_id)
    
    aluno.ativo = not aluno.ativo
    db.session.commit()
    
    status = "ativado" if aluno.ativo else "inativado"
    flash(f"Aluno {status} com sucesso!")
    return redirect(url_for("main.listar_alunos"))


@main_bp.route("/admin/aluno/delete/<int:aluno_id>", methods=["POST"])
@login_required
@profissional_required
def excluir_aluno(aluno_id):
    """Exclui um aluno (soft delete - inativa ao invés de excluir)"""
    aluno = Aluno.query.get_or_404(aluno_id)
    
    aluno.ativo = False
    db.session.commit()
    
    flash("Aluno inativado com sucesso! (Dados preservados)")
    return redirect(url_for("main.listar_alunos"))


@main_bp.route("/admin/aluno/hard-delete/<int:aluno_id>", methods=["POST"])
@login_required
@admin_required
def hard_delete_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)

    justificativa = (request.form.get("justificativa") or "").strip()
    if not justificativa:
        flash("Justificativa é obrigatória para exclusão total.", "error")
        return redirect(url_for("main.listar_alunos"))

    # Salva log (auditoria)
    from .models import HardDeleteAlunoLog, AutorizacaoFotoMenor
    log_row = HardDeleteAlunoLog(
        aluno_id=aluno.id,
        deletado_por_id=current_user.id,
        justificativa=justificativa,
    )
    db.session.add(log_row)

    # Remove arquivos físicos (se existirem)
    try:
        if aluno.foto_path:
            foto_abs = os.path.join(os.getcwd(), "static", aluno.foto_path.split("uploads/")[-1]) if "uploads/" in aluno.foto_path else os.path.join(os.getcwd(), "static", aluno.foto_path)
            if os.path.exists(foto_abs):
                os.remove(foto_abs)

        # Assinaturas dos responsáveis (menor de idade)
        autorizacoes = AutorizacaoFotoMenor.query.filter_by(aluno_id=aluno.id).all()
        for a in autorizacoes:
            if a.assinatura_path:
                # assinatura_path é relativo a static/
                assinatura_rel = a.assinatura_path
                assinatura_abs = os.path.join(os.getcwd(), "static", assinatura_rel.replace("uploads/", "")) if assinatura_rel.startswith("uploads/") else os.path.join(os.getcwd(), "static", assinatura_rel)
                assinatura_abs = assinatura_abs.replace("\\", "/")
                if os.path.exists(assinatura_abs):
                    os.remove(assinatura_abs)
    except Exception:
        # Não bloqueia a exclusão total caso a remoção de arquivo falhe
        pass

    db.session.delete(aluno)
    db.session.commit()

    flash("Aluno excluído totalmente com sucesso! (Dados e dependências removidos)")
    return redirect(url_for("main.listar_alunos"))


# ========================
# ROTAS PARA GESTÃO DE ESCOLAS
# ========================

@main_bp.route("/admin/escolas")
@login_required
def listar_escolas():
    """Lista todas as escolas"""
    escolas = Escola.query.order_by(Escola.nome).all()
    return render_template("admin_escolas.html", escolas=escolas)


@main_bp.route("/admin/relatorio-escolas")
@login_required
@profissional_required
def relatorio_escolas():
    """Relatório geral de escolas - Versão profissional"""
    from datetime import datetime
    
    escolas = Escola.query.order_by(Escola.nome).all()
    
    total_escolas = len(escolas)
    total_matriculas = sum(len(e.alunos) for e in escolas)
    data_geracao = datetime.now()
    
    return render_template("relatorio_escolas_profissional.html",
                           escolas=escolas,
                           total_escolas=total_escolas,
                           total_matriculas=total_matriculas,
                           data_geracao=data_geracao)


@main_bp.route("/admin/escola/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_escola():
    """Cria uma nova escola"""
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        endereco = normalizar_campo_texto(request.form.get("endereco"))
        
        if not nome:
            flash("Nome da escola é obrigatório.")
            return redirect(url_for("main.criar_escola"))
        
        escola = Escola(nome=nome, endereco=endereco)
        db.session.add(escola)
        db.session.commit()
        
        flash("Escola criada com sucesso!")
        return redirect(url_for("main.listar_escolas"))
    
    return render_template("admin_escola_form.html", escola=None, titulo="Nova Escola")


@main_bp.route("/admin/escola/edit/<int:escola_id>", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_escola(escola_id):
    """Edita uma escola existente"""
    escola = Escola.query.get_or_404(escola_id)
    
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        endereco = normalizar_campo_texto(request.form.get("endereco"))
        
        if not nome:
            flash("Nome da escola é obrigatório.")
            return redirect(url_for("main.editar_escola", escola_id=escola_id))
        
        escola.nome = nome
        escola.endereco = endereco
        db.session.commit()
        
        flash("Escola atualizada com sucesso!")
        return redirect(url_for("main.listar_escolas"))
    
    return render_template("admin_escola_form.html", escola=escola, titulo="Editar Escola")


@main_bp.route("/admin/instrumentos")
@login_required
def listar_instrumentos():
    """Lista instrumentos com filtros"""
    nome_busca = request.args.get('busca', '')
    ativo_filter = request.args.get('ativo', '')
    tipo_filter = request.args.get('tipo_id', '')
    
    query = Instrumento.query
    
    if nome_busca:
        query = query.filter(Instrumento.nome.ilike(f'%{nome_busca}%'))
    if ativo_filter == '1':
        query = query.filter(Instrumento.ativo == True)
    elif ativo_filter == '0':
        query = query.filter(Instrumento.ativo == False)
    if tipo_filter:
        query = query.filter(Instrumento.tipo_id == int(tipo_filter))
    
    instrumentos = query.order_by(Instrumento.nome).all()
    tipos_instrumento = TipoInstrumento.query.all()
    
    return render_template("admin_instrumentos.html", 
                          instrumentos=instrumentos,
                          tipos_instrumento=tipos_instrumento,
                          busca=nome_busca,
                          ativo_filter=ativo_filter,
                          tipo_filter=tipo_filter)


@main_bp.route("/admin/instrumento/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_instrumento():
    tipos_instrumento = TipoInstrumento.query.all()
    naipes = Naipe.query.all()
    
    if request.method == "POST":
        nome = request.form.get("nome")
        if not nome:
            flash("Nome obrigatório")
            return redirect(url_for("main.criar_instrumento"))
        
        patrimonio = request.form.get("patrimonio")
        if patrimonio and Instrumento.query.filter_by(patrimonio=patrimonio).first():
            flash("Patrimônio já cadastrado")
            return redirect(url_for("main.criar_instrumento"))
        
        # Converter data_aquisicao para objeto date
        data_aquisicao_str = request.form.get("data_aquisicao")
        data_aquisicao = None
        if data_aquisicao_str:
            try:
                data_aquisicao = datetime.strptime(data_aquisicao_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de aquisição inválida (use YYYY-MM-DD).")
                return redirect(url_for("main.criar_instrumento"))

        novo = Instrumento(
            nome=nome,
            tipo_id=request.form.get("tipo_id"),
            naipe_id=request.form.get("naipe_id"),
            patrimonio=patrimonio,
            marca=request.form.get("marca"),
            modelo=request.form.get("modelo"),
            estado=request.form.get("estado"),
            data_aquisicao=data_aquisicao,
            observacoes=request.form.get("observacoes"),
            ativo=True
        )
        db.session.add(novo)
        db.session.commit()
        flash("Instrumento criado!")
        return redirect(url_for("main.listar_instrumentos"))
    
    return render_template("admin_instrumento_form.html", titulo="Novo Instrumento",
                          instrumento=None, tipos_instrumento=tipos_instrumento, naipes=naipes)


@main_bp.route("/admin/instrumento/edit/<int:instrumento_id>", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_instrumento(instrumento_id):
    inst = Instrumento.query.get_or_404(instrumento_id)
    tipos = TipoInstrumento.query.all()
    naipes = Naipe.query.all()
    
    if request.method == "POST":
        patrimonio = request.form.get("patrimonio")
        if patrimonio != inst.patrimonio and Instrumento.query.filter_by(patrimonio=patrimonio).first():
            flash("Patrimônio já usado")
            return redirect(url_for("main.editar_instrumento", instrumento_id=inst.id))
        
        inst.nome = request.form.get("nome")
        inst.tipo_id = request.form.get("tipo_id")
        inst.naipe_id = request.form.get("naipe_id")
        inst.patrimonio = patrimonio
        inst.marca = request.form.get("marca")
        inst.modelo = request.form.get("modelo")
        # Converter data_aquisicao para objeto date
        data_aquisicao_str = request.form.get("data_aquisicao")
        data_aquisicao = None
        if data_aquisicao_str:
            try:
                data_aquisicao = datetime.strptime(data_aquisicao_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Data de aquisição inválida (use YYYY-MM-DD).")
                return redirect(url_for("main.editar_instrumento", instrumento_id=inst.id))

        inst.estado = request.form.get("estado")
        inst.data_aquisicao = data_aquisicao
        inst.observacoes = request.form.get("observacoes")
        db.session.commit()
        flash("Instrumento atualizado!")
        return redirect(url_for("main.listar_instrumentos"))
    
    return render_template("admin_instrumento_form.html", titulo="Editar Instrumento",
                          instrumento=inst, tipos_instrumento=tipos, naipes=naipes)


@main_bp.route("/admin/instrumento/toggle/<int:instrumento_id>", methods=["POST"])
@login_required
@profissional_required
def toggle_instrumento(instrumento_id):
    inst = Instrumento.query.get_or_404(instrumento_id)
    inst.ativo = not inst.ativo
    db.session.commit()
    flash(f"Instrumento {'ativado' if inst.ativo else 'inativado'}")
    return redirect(url_for("main.listar_instrumentos"))


@main_bp.route("/admin/instrumento/delete/<int:instrumento_id>", methods=["POST"])
@login_required
@profissional_required
def excluir_instrumento(instrumento_id):
    inst = Instrumento.query.get_or_404(instrumento_id)
    db.session.delete(inst)
    db.session.commit()
    flash("Instrumento excluído")
    return redirect(url_for("main.listar_instrumentos"))


# ========================
# ROTAS PARA GESTÃO DE TIPOS DE INSTRUMENTO
# ========================

@main_bp.route("/admin/tipos", methods=["GET", "POST"])
@login_required
@profissional_required
def listar_tipos():
    """Lista tipos de instrumento e permite criar novo"""
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        if not nome:
            flash("Nome do tipo é obrigatório.")
            return redirect(url_for("main.listar_tipos"))
        if TipoInstrumento.query.filter(db.func.lower(TipoInstrumento.nome) == nome.lower()).first():
            flash("Tipo já cadastrado.")
            return redirect(url_for("main.listar_tipos"))
        tipo = TipoInstrumento(nome=nome)
        db.session.add(tipo)
        db.session.commit()
        flash("Tipo criado com sucesso!")
        return redirect(url_for("main.listar_tipos"))

    tipos = TipoInstrumento.query.order_by(TipoInstrumento.nome).all()
    return render_template("admin_tipos.html", tipos=tipos)


@main_bp.route("/admin/tipo/edit/<int:tipo_id>", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_tipo(tipo_id):
    """Edita um tipo de instrumento"""
    tipo = TipoInstrumento.query.get_or_404(tipo_id)
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        if not nome:
            flash("Nome do tipo é obrigatório.")
            return redirect(url_for("main.editar_tipo", tipo_id=tipo_id))
        existente = TipoInstrumento.query.filter(
            db.func.lower(TipoInstrumento.nome) == nome.lower(),
            TipoInstrumento.id != tipo_id
        ).first()
        if existente:
            flash("Já existe outro tipo com esse nome.")
            return redirect(url_for("main.editar_tipo", tipo_id=tipo_id))
        tipo.nome = nome
        db.session.commit()
        flash("Tipo atualizado com sucesso!")
        return redirect(url_for("main.listar_tipos"))
    return render_template("admin_tipos.html", tipos=TipoInstrumento.query.order_by(TipoInstrumento.nome).all(), tipo_editar=tipo)


@main_bp.route("/admin/tipo/delete/<int:tipo_id>", methods=["POST"])
@login_required
@profissional_required
def excluir_tipo(tipo_id):
    """Exclui um tipo de instrumento se não houver dependências"""
    tipo = TipoInstrumento.query.get_or_404(tipo_id)
    if tipo.instrumentos:
        flash(f"Não é possível excluir: existem {len(tipo.instrumentos)} instrumento(s) vinculado(s) a este tipo.", "warning")
        return redirect(url_for("main.listar_tipos"))
    db.session.delete(tipo)
    db.session.commit()
    flash("Tipo excluído com sucesso!")
    return redirect(url_for("main.listar_tipos"))


# ========================
# ROTAS PARA GESTÃO DE NAIPES
# ========================

@main_bp.route("/admin/naipes", methods=["GET", "POST"])
@login_required
@profissional_required
def listar_naipes():
    """Lista naipes e permite criar novo"""
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        if not nome:
            flash("Nome do naipe é obrigatório.")
            return redirect(url_for("main.listar_naipes"))
        if Naipe.query.filter(db.func.lower(Naipe.nome) == nome.lower()).first():
            flash("Naipe já cadastrado.")
            return redirect(url_for("main.listar_naipes"))
        naipe = Naipe(nome=nome)
        db.session.add(naipe)
        db.session.commit()
        flash("Naipe criado com sucesso!")
        return redirect(url_for("main.listar_naipes"))

    naipes = Naipe.query.order_by(Naipe.nome).all()
    return render_template("admin_naipes.html", naipes=naipes)


@main_bp.route("/admin/naipe/edit/<int:naipe_id>", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_naipe(naipe_id):
    """Edita um naipe"""
    naipe = Naipe.query.get_or_404(naipe_id)
    if request.method == "POST":
        nome = normalizar_campo_texto(request.form.get("nome"))
        if not nome:
            flash("Nome do naipe é obrigatório.")
            return redirect(url_for("main.editar_naipe", naipe_id=naipe_id))
        existente = Naipe.query.filter(
            db.func.lower(Naipe.nome) == nome.lower(),
            Naipe.id != naipe_id
        ).first()
        if existente:
            flash("Já existe outro naipe com esse nome.")
            return redirect(url_for("main.editar_naipe", naipe_id=naipe_id))
        naipe.nome = nome
        db.session.commit()
        flash("Naipe atualizado com sucesso!")
        return redirect(url_for("main.listar_naipes"))
    return render_template("admin_naipes.html", naipes=Naipe.query.order_by(Naipe.nome).all(), naipe_editar=naipe)


@main_bp.route("/admin/naipe/delete/<int:naipe_id>", methods=["POST"])
@login_required
@profissional_required
def excluir_naipe(naipe_id):
    """Exclui um naipe se não houver dependências"""
    naipe = Naipe.query.get_or_404(naipe_id)
    if naipe.instrumentos:
        flash(f"Não é possível excluir: existem {len(naipe.instrumentos)} instrumento(s) vinculado(s) a este naipe.", "warning")
        return redirect(url_for("main.listar_naipes"))
    db.session.delete(naipe)
    db.session.commit()
    flash("Naipe excluído com sucesso!")
    return redirect(url_for("main.listar_naipes"))


@main_bp.route("/admin/escola/delete/<int:escola_id>", methods=["POST"])
@login_required
@admin_required
def excluir_escola(escola_id):
    escola = Escola.query.get_or_404(escola_id)
    
    db.session.delete(escola)
    db.session.commit()
    
    flash("Escola excluída com sucesso!")
    return redirect(url_for("main.listar_escolas"))


# ========================
# ROTAS PARA BUSCA DE CEP
# ========================

@main_bp.route("/admin/buscar-cep/<cep>")
@login_required
@profissional_required
def buscar_cep(cep):
    """Busca CEP na tabela de logradouros local"""
    cep = cep.replace('-', '').replace('.', '')
    
    logradouro = Logradouro.query.filter_by(cep=cep).first()
    
    if logradouro:
        return jsonify({
            'success': True,
            'logradouro': {
                'cep': logradouro.cep,
                'tipo': logradouro.tipo,
                'descricao': logradouro.descricao,
                'bairro': logradouro.descricao_bairro,
                'cidade': logradouro.descricao_cidade,
                'uf': logradouro.uf,
                'complemento': logradouro.complemento
            }
        })
    
    return jsonify({'success': False, 'message': 'CEP não encontrado'})


@main_bp.route("/admin/salvar-logradouro", methods=["POST"])
@login_required
@profissional_required
def salvar_logradouro():
    """Salva novo logradouro buscado da API ViaCEP"""
    data = request.get_json()
    
    cep = data.get('cep', '').replace('-', '').replace('.', '')
    
    existente = Logradouro.query.filter_by(cep=cep).first()
    if existente:
        return jsonify({'success': True, 'message': 'CEP já existe'})
    
    cidade_nome = data.get('descricao_cidade', '')
    uf = data.get('uf', 'SP')
    
    cidade = Cidade.query.filter(
        Cidade.descricao.ilike(f'%{cidade_nome}%'),
        Cidade.uf == uf
    ).first()
    
    if not cidade:
        cidade = Cidade(
            descricao=cidade_nome,
            uf=uf,
            codigo_ibge=None,
            ddd=None
        )
        db.session.add(cidade)
        db.session.flush()
    
    logradouro = Logradouro(
        cep=cep,
        tipo=data.get('tipo', ''),
        descricao=data.get('descricao', ''),
        cidade_id=cidade.id,
        uf=uf,
        complemento=data.get('complemento'),
        descricao_sem_numero=data.get('descricao', ''),
        descricao_cidade=cidade_nome,
        codigo_cidade_ibge=cidade.codigo_ibge,
        descricao_bairro=data.get('descricao_bairro', '')
    )
    
    db.session.add(logradouro)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Logradouro salvo com sucesso'})


def salvar_foto_aluno(foto_file, aluno_id):
    """Salva a foto do aluno e retorna o caminho"""
    if not foto_file or foto_file.filename == '':
        return None
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if allowed_file(foto_file.filename):
        ext = foto_file.filename.rsplit('.', 1)[1].lower()
        filename = f"aluno_{aluno_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        
        upload_folder = os.path.join('static', 'uploads', 'alunos')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        foto_file.save(filepath)
        
        return os.path.join('uploads', 'alunos', filename)
    
    return None


@main_bp.route("/admin/relatorios-alunos")
@login_required
def relatorios_alunos():
    """Página inicial dos relatórios de alunos"""
    return render_template("relatorios_alunos.html")


@main_bp.route("/admin/relatorio-geral-alunos")
@login_required
def relatorio_geral_alunos():
    """Relatório geral de alunos ativos - Versão profissional"""
    from datetime import datetime
    
    alunos = Aluno.query.outerjoin(Responsavel).outerjoin(AlunoEscola).outerjoin(Escola).filter(
        Aluno.ativo == True
    ).order_by(Aluno.nome).all()
    
    total_alunos = Aluno.query.filter(Aluno.ativo == True).count()
    data_geracao = datetime.now()
    
    return render_template("relatorio_geral_alunos_profissional.html", 
                           alunos=alunos, 
                           total_alunos=total_alunos,
                           data_geracao=data_geracao)


@main_bp.route("/admin/relatorio-aluno/<int:aluno_id>")
@login_required
def relatorio_aluno(aluno_id):
    """Relatório individual profissional"""
    aluno = Aluno.query.options(
        db.joinedload(Aluno.responsaveis),
        db.joinedload(Aluno.escolas).joinedload(AlunoEscola.escola)
    ).get_or_404(aluno_id)
    
    data_geracao = datetime.now()
    
    return render_template("relatorio_aluno_individual_profissional.html", 
                           aluno=aluno, 
                           data_geracao=data_geracao)


# ========================
# ROTAS PARA BACKUP E RESTAURAÇÃO
# ========================

@main_bp.route("/admin/backup")
@login_required
@admin_required
def painel_backup():
    """Painel de gerenciamento de backups do banco de dados"""
    backups = listar_backups()
    caminho_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "database.db")
    db_existe = os.path.exists(caminho_db)
    db_tamanho = os.path.getsize(caminho_db) if db_existe else 0
    return render_template(
        "admin_backup.html",
        backups=backups,
        db_existe=db_existe,
        db_tamanho=db_tamanho,
    )


@main_bp.route("/admin/backup/criar", methods=["POST"])
@login_required
@admin_required
def gerar_backup():
    """Gera um novo backup do banco de dados"""
    try:
        caminho_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "database.db")
        caminho_backup = criar_backup(caminho_db)
        nome_arquivo = os.path.basename(caminho_backup)
        flash(f"Backup criado com sucesso: {nome_arquivo}")
    except Exception as e:
        flash(f"Erro ao criar backup: {str(e)}", "error")
    return redirect(url_for("main.painel_backup"))


@main_bp.route("/admin/backup/restaurar", methods=["POST"])
@login_required
@admin_required
def restore_backup():
    """Restaura o banco de dados a partir de um backup"""
    nome_backup = request.form.get("nome_backup")
    if not nome_backup:
        flash("Nenhum backup selecionado.", "error")
        return redirect(url_for("main.painel_backup"))

    caminho_backup = obter_caminho_backup(nome_backup)
    if not caminho_backup:
        flash("Arquivo de backup não encontrado.", "error")
        return redirect(url_for("main.painel_backup"))

    # Validar backup
    valido, msg = validar_backup(caminho_backup)
    if not valido:
        flash(msg, "error")
        return redirect(url_for("main.painel_backup"))

    try:
        caminho_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "database.db")
        sucesso, msg = restaurar_backup(caminho_backup, caminho_db)
        if sucesso:
            flash(msg + " É necessário reiniciar a aplicação para que as alterações tenham efeito.")
        else:
            flash(msg, "error")
    except Exception as e:
        flash(f"Erro ao restaurar backup: {str(e)}", "error")

    return redirect(url_for("main.painel_backup"))


@main_bp.route("/admin/backup/excluir", methods=["POST"])
@login_required
@admin_required
def deletar_backup():
    """Exclui um arquivo de backup"""
    nome_backup = request.form.get("nome_backup")
    if not nome_backup:
        flash("Nenhum backup selecionado.", "error")
        return redirect(url_for("main.painel_backup"))

    caminho_backup = obter_caminho_backup(nome_backup)
    if not caminho_backup:
        flash("Arquivo de backup não encontrado.", "error")
        return redirect(url_for("main.painel_backup"))

    sucesso, msg = excluir_backup(caminho_backup)
    if sucesso:
        flash(msg)
    else:
        flash(msg, "error")

    return redirect(url_for("main.painel_backup"))


@main_bp.route("/admin/creditos")
@login_required
def creditos():
    """Página de Créditos do sistema"""
    return render_template("Copywrite.html")


@main_bp.route("/admin/logs/hard-delete-alunos")
@login_required
@admin_required
def logs_hard_delete_alunos():
    """Exibe auditoria de exclusões totais (hard delete) de integrantes."""
    from .models import HardDeleteAlunoLog

    logs = (
        HardDeleteAlunoLog.query.order_by(HardDeleteAlunoLog.created_at.desc()).all()
    )

    return render_template("admin_logs_hard_delete_alunos.html", logs=logs)


@main_bp.route("/admin/configuracoes", methods=["GET", "POST"])
@login_required
@admin_required
def configuracoes():
    """Página de configurações do sistema para administradores"""
    if request.method == "POST":
        logo = request.files.get("logo_banda")
        if logo and logo.filename:
            filename = secure_filename(logo.filename)
            allowed_ext = os.path.splitext(filename)[1].lower()
            if allowed_ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
                flash("Formato de logo inválido.", "danger")
                return redirect(url_for("main.configuracoes"))

            upload_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "imgs")
            os.makedirs(upload_folder, exist_ok=True)
            saved_name = f"login_logo{allowed_ext}"
            logo_path = os.path.join(upload_folder, saved_name)
            logo.save(logo_path)
            definir_configuracao("login_logo_path", f"imgs/{saved_name}")

        valores = {}

        if "login_titulo" in request.form:
            valores["login_title"] = request.form.get("login_titulo", "").strip()
        if "login_subtitulo" in request.form:
            valores["login_subtitle"] = request.form.get("login_subtitulo", "").strip()
        if "cor-accent" in request.form:
            valores["theme_accent"] = request.form.get("cor-accent", "#0d6efd")
        if "cor-fundo" in request.form:
            valores["theme_bg"] = request.form.get("cor-fundo", "#121212")
        if "cor-navbar" in request.form:
            valores["navbar_bg"] = request.form.get("cor-navbar", "#343a40")
        if "cor-superficie" in request.form:
            valores["surface_bg"] = request.form.get("cor-superficie", "#1f1f1f")
        if "cor-texto-aba-ativa" in request.form:
            valores["tab_active_text"] = request.form.get("cor-texto-aba-ativa", "#ffffff")
        if "cor-fundo-aba-ativa" in request.form:
            valores["tab_active_bg"] = request.form.get("cor-fundo-aba-ativa", "#0d6efd")
        if "cor-texto-aba-inativa" in request.form:
            valores["tab_inactive_text"] = request.form.get("cor-texto-aba-inativa", "#adb5bd")
        if "cor-fundo-aba-inativa" in request.form:
            valores["tab_inactive_bg"] = request.form.get("cor-fundo-aba-inativa", "#212529")
        if "texto-rodape" in request.form:
            valores["footer_text"] = request.form.get("texto-rodape", "").strip()
        if "timeout-sessao" in request.form:
            valores["session_timeout_minutes"] = request.form.get("timeout-sessao", "30").strip()
        if "tentativas-login" in request.form:
            valores["login_attempts_limit"] = request.form.get("tentativas-login", "5").strip()

        if any(key in request.form for key in ["req-minuscula", "req-maiuscula", "req-numero", "req-simbolo", "timeout-sessao", "tentativas-login"]):
            valores["password_lower"] = "1" if "req-minuscula" in request.form else "0"
            valores["password_upper"] = "1" if "req-maiuscula" in request.form else "0"
            valores["password_number"] = "1" if "req-numero" in request.form else "0"
            valores["password_symbol"] = "1" if "req-simbolo" in request.form else "0"

        if "upload-maximo" in request.form:
            valores["upload_maximo"] = request.form.get("upload-maximo", "50").strip()
        if "pasta-backup" in request.form:
            valores["backup_folder"] = request.form.get("pasta-backup", "instance/backups").strip()
        if "log-retencao" in request.form:
            valores["log_retention_days"] = request.form.get("log-retencao", "30").strip()

        for chave, valor in valores.items():
            definir_configuracao(chave, valor)

        if "upload_maximo" in valores:
            try:
                current_app.config["MAX_CONTENT_LENGTH"] = int(valores["upload_maximo"]) * 1024 * 1024
            except (TypeError, ValueError):
                pass

        if "backup_folder" in valores:
            backup_folder = valores.get("backup_folder")
            if backup_folder:
                if not os.path.isabs(backup_folder):
                    backup_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), backup_folder)
                os.makedirs(backup_folder, exist_ok=True)
                current_app.config["BACKUP_FOLDER"] = backup_folder

        if "session_timeout_minutes" in valores:
            try:
                timeout_minutes = int(valores["session_timeout_minutes"])
                if timeout_minutes > 0:
                    current_app.config["SESSION_TIMEOUT_MINUTES"] = timeout_minutes
                    current_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=timeout_minutes)
            except (TypeError, ValueError):
                pass

        if "login_attempts_limit" in valores:
            try:
                attempts_limit = int(valores["login_attempts_limit"])
                if attempts_limit > 0:
                    current_app.config["LOGIN_ATTEMPTS_LIMIT"] = attempts_limit
            except (TypeError, ValueError):
                pass

        if "log_retention_days" in valores:
            limpar_logs_antigos()

        flash("Configurações salvas com sucesso.", "success")
        return redirect(url_for("main.configuracoes"))

    return render_template("admin_configuracoes.html")


@main_bp.route("/admin/manutencao/limpar-cache", methods=["POST"])
@login_required
@admin_required
def limpar_cache():
    """Limpa caches temporários do sistema"""
    try:
        # Limpar cache de templates Flask
        current_app.jinja_env.cache = {}

        # Limpar arquivos temporários
        import tempfile
        import shutil

        temp_dir = tempfile.gettempdir()
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(filepath) and filename.startswith('flask_'):
                    os.unlink(filepath)
            except Exception:
                pass

        flash("Cache limpo com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao limpar cache: {str(e)}", "danger")

    return redirect(url_for("main.configuracoes"))


@main_bp.route("/admin/manutencao/verificar-integridade", methods=["POST"])
@login_required
@admin_required
def verificar_integridade():
    """Verifica a integridade dos dados e estruturas do banco"""
    try:
        from .models import db

        # Verificar conexão com banco
        db.session.execute(text("SELECT 1"))

        # Verificar tabelas principais
        tabelas = ['aluno', 'user', 'tipo_instrumento', 'naipe', 'funcao_banda']
        tabelas_faltando = []

        for tabela in tabelas:
            result = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tabela"),
                {"tabela": tabela},
            )
            if not result.fetchone():
                tabelas_faltando.append(tabela)

        if tabelas_faltando:
            flash(f"Tabelas faltando: {', '.join(tabelas_faltando)}", "warning")
        else:
            flash("Integridade do banco verificada com sucesso.", "success")

    except Exception as e:
        flash(f"Erro na verificação de integridade: {str(e)}", "danger")

    return redirect(url_for("main.configuracoes"))


@main_bp.route("/admin/manutencao/reindexar", methods=["POST"])
@login_required
@admin_required
def reindexar_banco():
    """Reindexa tabelas do banco para otimizar consultas"""
    try:
        from .models import db

        # Reindexar tabelas principais (SQLite não tem REINDEX, mas podemos analisar)
        tabelas = ['aluno', 'user', 'tipo_instrumento', 'naipe', 'funcao_banda']

        for tabela in tabelas:
            try:
                # Para SQLite, podemos executar ANALYZE para atualizar estatísticas
                db.session.execute(text(f"ANALYZE {tabela}"))
            except Exception:
                pass  # Ignorar erros em tabelas que podem não existir

        flash("Reindexação concluída com sucesso.", "success")

    except Exception as e:
        flash(f"Erro na reindexação: {str(e)}", "danger")

    return redirect(url_for("main.configuracoes"))

