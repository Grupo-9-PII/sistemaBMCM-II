from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session, abort
from flask_login import login_required, current_user
import calendar
from datetime import date, timedelta
from dotenv import set_key
from .models import (
    User,
    Aluno,
    AutorizacaoViagem,
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
    Atividade,
    Presenca,
    Evento,
    Logradouro,
    Cidade,
    Comunicacao,
    ComunicacaoDestinatario,
    ComunicacaoAnexo,
    ContatoComunicacao,
    GoogleCalendarSync,
    CartaoPasse,
    CotaMensalPasse,
    MovimentoPasse,
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
    obter_configuracao,
)

from .backup import (
    listar_backups,
    criar_backup,
    restaurar_backup,
    excluir_backup,
    validar_backup,
    obter_caminho_backup,
    obter_senha_backup,
)
from .google_oauth import authorization_url, exchange_code, save_token
from .google_oauth import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    GOOGLE_DRIVE_FILE_SCOPE,
    GMAIL_SEND_SCOPE,
    google_workspace_status,
    has_scope,
    is_gmail_sender,
)
from .google_mail import enviar_email_gmail
from .google_calendar import sincronizar_atividade, sincronizar_se_vinculada
from .google_drive import enviar_backup_para_drive, listar_backups_drive
from datetime import datetime, timezone
from pathlib import Path
import hmac
import os
import requests
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy import text

main_bp = Blueprint("main", __name__)

MESES_CALENDARIO = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)
DIAS_SEMANA_CALENDARIO = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)


def _data_inicial_formulario():
    try:
        return datetime.strptime(request.args.get("data", ""), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


def _status_google_workspace():
    return google_workspace_status(obter_configuracao("communication_sender_email"))


def _get_or_404(model, identifier):
    instance = db.session.get(model, identifier)
    if instance is None:
        abort(404)
    return instance


def _bloquear_central_comunicacoes():
    status = _status_google_workspace()
    if status["available"]:
        return None
    flash(f"Central de comunicação desativada: {status['reason']}", "warning")
    return redirect(url_for("main.dashboard"))


def _sincronizar_calendar(activity_type, activity, somente_vinculada=False):
    try:
        if somente_vinculada:
            result = sincronizar_se_vinculada(activity_type, activity)
        else:
            result = sincronizar_atividade(activity_type, activity)
    except (RuntimeError, ValueError, requests.RequestException):
        current_app.logger.warning(
            "Falha ao sincronizar %s %s com o Google Calendar.",
            activity_type,
            activity.id,
            exc_info=True,
        )
        flash(
            "A atividade foi salva no BMCM, mas não foi sincronizada com o Google Calendar. Verifique a autorização e tente novamente.",
            "warning",
        )
        return False

    if result is None:
        return None
    if result is False:
        flash(
            "A atividade foi cancelada antes de ser sincronizada e não foi publicada no Google Calendar.",
            "info",
        )
    else:
        flash("Atividade sincronizada com o Google Calendar.", "success")
    return result


def _atualizar_movimento_passe(presenca):
    """Sincroniza o consumo de passes da presença sem criar saldo negativo."""
    movimentos = (
        MovimentoPasse.query.filter_by(presenca_id=presenca.id)
        .order_by(MovimentoPasse.data_hora.desc(), MovimentoPasse.id.desc())
        .all()
    )
    movimento_presenca = sum(movimento.quantidade for movimento in movimentos)
    if not presenca.presente:
        if movimento_presenca >= 0:
            return
        movimento_consumo = next(
            (movimento for movimento in movimentos if movimento.quantidade < 0),
            None,
        )
        if movimento_consumo is None:
            raise ValueError("Não foi possível localizar o consumo de passes desta presença.")
        db.session.add(MovimentoPasse(
            cota_id=movimento_consumo.cota_id,
            presenca_id=presenca.id,
            quantidade=-movimento_presenca,
            tipo="ESTORNO",
        ))
        return

    cartao = presenca.aluno.cartao_passe
    if not cartao or not cartao.ativo or movimento_presenca != 0:
        return

    mes_referencia = presenca.data_presenca.replace(day=1)
    cota = CotaMensalPasse.query.filter_by(
        aluno_id=presenca.aluno_id,
        mes_referencia=mes_referencia,
    ).first()
    if cota is None:
        raise ValueError(
            f"Não há cota de passes cadastrada para {presenca.aluno.nome} em "
            f"{mes_referencia.strftime('%m/%Y')}."
        )

    saldo = _saldo_cota_passe(cota)

    if saldo < 2:
        raise ValueError(
            f"{presenca.aluno.nome} possui apenas {saldo} passe(s) disponível(is); "
            "são necessários 2 para registrar a presença."
        )
    db.session.add(MovimentoPasse(
        cota_id=cota.id,
        presenca_id=presenca.id,
        quantidade=-2,
        tipo="CONSUMO",
    ))


def _saldo_cota_passe(cota):
    """Calcula o saldo usando o histórico novo ou o formato legado da cota."""
    movimentos = list(cota.movimentos)
    if any(movimento.tipo == "DISPONIBILIZACAO" for movimento in movimentos):
        return sum(movimento.quantidade for movimento in movimentos)
    return cota.quantidade_disponibilizada + sum(
        movimento.quantidade for movimento in movimentos
    )


def _reautenticar_admin_para_senha_backup(senha_admin):
    tentativas = session.get("backup_password_reauth_failures", 0)
    if tentativas >= 5:
        return "Muitas tentativas. Encerre a sessão e autentique-se novamente.", 429
    if not current_user.check_password(senha_admin or ""):
        session["backup_password_reauth_failures"] = tentativas + 1
        return "Senha do administrador incorreta.", 403
    session.pop("backup_password_reauth_failures", None)
    return None


def _resposta_senha_backup(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@main_bp.route("/admin/google/oauth/start")
@login_required
@admin_required
def iniciar_google_oauth():
    return redirect(authorization_url())


@main_bp.route("/google/oauth/callback")
def callback_google_oauth():
    erro = request.args.get("error")
    if erro:
        flash(f"Autorização Google cancelada: {erro}.", "warning")
        return redirect(url_for("auth.login"))

    try:
        token = exchange_code(request.args.get("code"), request.args.get("state"))
        save_token(token)
    except (ValueError, requests.RequestException) as exc:
        current_app.logger.warning("Falha na autorização OAuth do Google: %s", exc)
        flash("Não foi possível concluir a autorização do Google.", "danger")
        return redirect(url_for("auth.login"))

    flash("Autorização OAuth do Google concluída.", "success")
    return redirect(url_for("main.configuracoes"))


@main_bp.route("/")
@login_required
@session_timeout
def dashboard():
    update_activity()
    hoje = datetime.now(timezone.utc).date()
    stats = {
        'total_alunos': Aluno.query.count(),
        'alunos_ativos': Aluno.query.filter_by(ativo=True).count(),
        'total_escolas': Escola.query.count(),
        'instrumentos_ativos': Instrumento.query.filter_by(ativo=True).count(),
        'usuarios': User.query.filter_by(is_active=True).count(),
        'usuarios_admin': User.query.filter_by(is_admin=True, is_active=True).count(),
        'atividades_total': Atividade.query.count(),
        'presencas_total': Presenca.query.count(),
        'presencas_hoje': Presenca.query.filter_by(data_presenca=hoje).count(),
    }
    return render_template("dashboard.html", stats=stats)


@main_bp.route("/admin")
@login_required
@admin_required
def painel_admin():
    return render_template("dashboard.html")


@main_bp.route("/admin/atividades")
@login_required
@profissional_required
def listar_atividades():
    atividades = Atividade.query.order_by(
        Atividade.data_atividade.desc(), Atividade.id.desc()
    ).all()
    calendar_syncs = {
        sync.atividade_id: sync
        for sync in GoogleCalendarSync.query.filter(
            GoogleCalendarSync.atividade_id.isnot(None)
        ).all()
    }
    return render_template(
        "admin_atividades.html",
        atividades=atividades,
        calendar_syncs=calendar_syncs,
    )


@main_bp.route("/admin/calendario")
@login_required
@profissional_required
def calendario_bmcm():
    hoje = datetime.now().date()
    filtro_tipo = request.args.get("tipo", "").strip()
    filtro_status = request.args.get("status", "").strip()
    filtro_busca = request.args.get("q", "").strip()
    visualizacao = request.args.get("visao", "mes").strip().lower()
    if visualizacao not in {"mes", "agenda"}:
        visualizacao = "mes"
    data_selecionada = None
    try:
        if request.args.get("data"):
            data_selecionada = datetime.strptime(
                request.args["data"], "%Y-%m-%d"
            ).date()
    except ValueError:
        data_selecionada = None

    try:
        mes_inicio = datetime.strptime(
            request.args.get("mes", ""), "%Y-%m"
        ).date().replace(day=1)
    except ValueError:
        mes_inicio = (data_selecionada or hoje).replace(day=1)

    if data_selecionada and data_selecionada.replace(day=1) != mes_inicio:
        mes_inicio = data_selecionada.replace(day=1)

    if not data_selecionada or data_selecionada.replace(day=1) != mes_inicio:
        data_selecionada = hoje if hoje.replace(day=1) == mes_inicio else mes_inicio

    proximo_mes = (mes_inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
    mes_anterior = mes_inicio - timedelta(days=1)
    mes_anterior = mes_anterior.replace(day=1)
    mes_seguinte = proximo_mes

    itens_por_dia = {}
    presencas_por_item = {}
    presencas_mes = Presenca.query.filter(
        Presenca.data_presenca >= mes_inicio,
        Presenca.data_presenca < proximo_mes,
    ).all()
    for registro in presencas_mes:
        if registro.ensaio_id is not None:
            chave = ("Ensaio", registro.ensaio_id)
        elif registro.evento_id is not None:
            chave = ("Evento", registro.evento_id)
        elif registro.atividade_id is not None:
            chave = ("Atividade", registro.atividade_id)
        else:
            continue
        presencas_por_item.setdefault(chave, []).append(registro)

    sincronizados = set()
    for vinculo in GoogleCalendarSync.query.all():
        if vinculo.ensaio_id is not None:
            sincronizados.add(("ensaio", vinculo.ensaio_id))
        elif vinculo.evento_id is not None:
            sincronizados.add(("evento", vinculo.evento_id))
        elif vinculo.atividade_id is not None:
            sincronizados.add(("atividade", vinculo.atividade_id))

    def adicionar_item(tipo, dia, titulo, horario, local, status,
                       url_chamada, url_sincronizar, vinculo_id):
        registros = presencas_por_item.get((tipo, vinculo_id), [])
        item = {
            "id": vinculo_id,
            "data": dia,
            "tipo": tipo,
            "titulo": titulo,
            "horario": horario or "",
            "local": local or "",
            "status": status or "",
            "url_chamada": url_chamada,
            "url_sincronizar": url_sincronizar,
            "sincronizado": (tipo, vinculo_id) in sincronizados,
            "total_presencas": len(registros),
            "presentes": sum(1 for registro in registros if registro.presente),
            "ausentes": sum(1 for registro in registros if not registro.presente),
        }
        item["chamada_status"] = "Registrada" if registros else "Pendente"

        texto_filtro = " ".join(
            (item["tipo"], item["titulo"], item["local"], item["status"])
        ).casefold()
        if filtro_tipo and item["tipo"].casefold() != filtro_tipo.casefold():
            return
        if filtro_status and item["status"].casefold() != filtro_status.casefold():
            return
        if filtro_busca and filtro_busca.casefold() not in texto_filtro:
            return
        itens_por_dia.setdefault(dia, []).append(item)

    ensaios = Ensaio.query.filter(
        Ensaio.data_ensaio >= mes_inicio,
        Ensaio.data_ensaio < proximo_mes,
    ).all()
    for ensaio in ensaios:
        adicionar_item(
            "Ensaio", ensaio.data_ensaio, ensaio.titulo,
            ensaio.horario, ensaio.local, ensaio.status,
            url_for("main.registrar_presenca", ensaio_id=ensaio.id),
            url_for("main.sincronizar_ensaio_calendar", ensaio_id=ensaio.id),
            ensaio.id,
        )

    eventos = Evento.query.filter(
        Evento.data_evento >= mes_inicio,
        Evento.data_evento < proximo_mes,
    ).all()
    for evento in eventos:
        adicionar_item(
            "Evento", evento.data_evento, evento.nome_evento,
            None, evento.cidade, evento.status,
            url_for("main.registrar_presenca_evento", evento_id=evento.id),
            url_for("main.sincronizar_evento_calendar", evento_id=evento.id),
            evento.id,
        )

    atividades = Atividade.query.filter(
        Atividade.data_atividade >= mes_inicio,
        Atividade.data_atividade < proximo_mes,
    ).all()
    for atividade in atividades:
        horario = atividade.horario_inicio
        if atividade.horario_fim:
            horario = f"{horario or ''} - {atividade.horario_fim}".strip(" -")
        adicionar_item(
            "Atividade", atividade.data_atividade, atividade.titulo,
            horario, atividade.local, atividade.status,
            url_for("main.registrar_presenca_atividade", atividade_id=atividade.id),
            url_for("main.sincronizar_atividade_calendar", atividade_id=atividade.id),
            atividade.id,
        )

    for itens in itens_por_dia.values():
        itens.sort(key=lambda item: (item["horario"], item["tipo"], item["titulo"].casefold()))

    itens_agenda = [
        item
        for dia in sorted(itens_por_dia)
        for item in itens_por_dia[dia]
    ]
    tipos_disponiveis = sorted({item["tipo"] for item in itens_agenda})
    status_disponiveis = sorted(
        {item["status"] for item in itens_agenda if item["status"]},
        key=str.casefold,
    )
    indicadores = {
        "total": len(itens_agenda),
        "com_chamada": sum(1 for item in itens_agenda if item["total_presencas"]),
        "sem_chamada": sum(1 for item in itens_agenda if not item["total_presencas"]),
        "presentes": sum(item["presentes"] for item in itens_agenda),
    }

    mes_calendario = calendar.Calendar(firstweekday=0).monthdatescalendar(
        mes_inicio.year, mes_inicio.month
    )
    return render_template(
        "admin_calendario.html",
        mes_inicio=mes_inicio,
        mes_anterior=mes_anterior,
        mes_seguinte=mes_seguinte,
        mes_nome=MESES_CALENDARIO[mes_inicio.month - 1],
        dia_semana=DIAS_SEMANA_CALENDARIO[data_selecionada.weekday()],
        hoje=hoje,
        semanas=mes_calendario,
        itens_por_dia=itens_por_dia,
        data_selecionada=data_selecionada,
        itens_selecionados=itens_por_dia.get(data_selecionada, []),
        itens_agenda=itens_agenda,
        visualizacao=visualizacao,
        filtro_tipo=filtro_tipo,
        filtro_status=filtro_status,
        filtro_busca=filtro_busca,
        tipos_disponiveis=tipos_disponiveis,
        status_disponiveis=status_disponiveis,
        indicadores=indicadores,
    )


@main_bp.route(
    "/admin/atividade/<int:atividade_id>/calendar/sincronizar",
    methods=["POST"],
)
@login_required
@profissional_required
def sincronizar_atividade_calendar(atividade_id):
    atividade = _get_or_404(Atividade, atividade_id)
    _sincronizar_calendar("atividade", atividade)
    return redirect(url_for("main.listar_atividades"))


@main_bp.route("/admin/atividade/create", methods=["GET", "POST"])
@login_required
@profissional_required
def criar_atividade():
    tipos = ("TREINAMENTO", "APRESENTACAO", "OUTRA")
    if request.method == "POST":
        titulo = normalizar_campo_texto(request.form.get("titulo"))
        tipo = request.form.get("tipo") or "TREINAMENTO"
        try:
            data_atividade = datetime.strptime(
                request.form.get("data_atividade"), "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            flash("Informe uma data válida para a atividade.", "danger")
            return redirect(url_for("main.criar_atividade"))
        if not titulo:
            flash("Informe o título da atividade.", "danger")
            return redirect(url_for("main.criar_atividade"))
        if tipo not in tipos:
            flash("Tipo de atividade inválido.", "danger")
            return redirect(url_for("main.criar_atividade"))

        atividade = Atividade(
            tipo=tipo,
            titulo=titulo,
            data_atividade=data_atividade,
            horario_inicio=request.form.get("horario_inicio", "").strip() or None,
            horario_fim=request.form.get("horario_fim", "").strip() or None,
            local=normalizar_campo_texto(request.form.get("local")),
            area=normalizar_campo_texto(request.form.get("area")),
            responsavel=normalizar_campo_texto(request.form.get("responsavel")),
            observacoes=request.form.get("observacoes", "").strip() or None,
            criado_por_id=current_user.id,
        )
        db.session.add(atividade)
        db.session.commit()
        flash("Atividade criada. Registre a lista de presença.", "success")
        return redirect(url_for("main.registrar_presenca_atividade", atividade_id=atividade.id))

    return render_template(
        "admin_atividade_form.html",
        atividade=None,
        tipos=tipos,
        data_inicial=_data_inicial_formulario(),
    )


@main_bp.route("/admin/atividade/<int:atividade_id>/presenca", methods=["GET", "POST"])
@login_required
@profissional_required
def registrar_presenca_atividade(atividade_id):
    atividade = _get_or_404(Atividade, atividade_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == "POST":
        registros_salvos = []
        for aluno in alunos:
            status = request.form.get(f"presenca_{aluno.id}", "ausente")
            registro = Presenca.query.filter_by(
                aluno_id=aluno.id, atividade_id=atividade.id
            ).first()
            if registro is None:
                registro = Presenca(
                    aluno_id=aluno.id,
                    atividade_id=atividade.id,
                    data_presenca=atividade.data_atividade,
                )
                db.session.add(registro)
            registro.presente = status == "presente"
            registro.observacoes = "JUSTIFICADO" if status == "justificado" else None
            registro.data_presenca = atividade.data_atividade
            registro.registrado_por_id = current_user.id
            registro.registrado_at = datetime.now(timezone.utc)
            registros_salvos.append(registro)

        try:
            db.session.flush()
            for registro in registros_salvos:
                _atualizar_movimento_passe(registro)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("main.registrar_presenca_atividade", atividade_id=atividade.id))
        flash("Lista de presença da atividade salva com sucesso.", "success")
        return redirect(url_for("main.registrar_presenca_atividade", atividade_id=atividade.id))

    registros = {
        registro.aluno_id: registro
        for registro in Presenca.query.filter_by(atividade_id=atividade.id).all()
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
        atividade_titulo=atividade.titulo,
        atividade_data=atividade.data_atividade,
        atividade_horario=atividade.horario_inicio,
        atividade_local=atividade.local,
        atividade_url=url_for("main.listar_atividades"),
        grupos=sorted(grupos.items()),
        registros=registros,
    )


@main_bp.route("/admin/eventos")
@login_required
@profissional_required
def listar_eventos():
    eventos = Evento.query.order_by(Evento.data_evento.desc(), Evento.id.desc()).all()
    calendar_syncs = {
        sync.evento_id: sync
        for sync in GoogleCalendarSync.query.filter(
            GoogleCalendarSync.evento_id.isnot(None)
        ).all()
    }
    return render_template(
        "admin_eventos.html", eventos=eventos, calendar_syncs=calendar_syncs
    )


@main_bp.route("/admin/evento/<int:evento_id>/calendar/sincronizar", methods=["POST"])
@login_required
@profissional_required
def sincronizar_evento_calendar(evento_id):
    evento = _get_or_404(Evento, evento_id)
    _sincronizar_calendar("evento", evento)
    return redirect(url_for("main.listar_eventos"))


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

    return render_template(
        "admin_evento_form.html",
        evento=None,
        data_inicial=_data_inicial_formulario(),
    )


@main_bp.route("/admin/evento/<int:evento_id>/edit", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_evento(evento_id):
    evento = _get_or_404(Evento, evento_id)
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
        _sincronizar_calendar("evento", evento, somente_vinculada=True)
        flash("Evento atualizado com sucesso.", "success")
        return redirect(url_for("main.listar_eventos"))
    return render_template("admin_evento_form.html", evento=evento)


@main_bp.route("/admin/evento/<int:evento_id>/cancel", methods=["POST"])
@login_required
@profissional_required
def cancelar_evento(evento_id):
    evento = _get_or_404(Evento, evento_id)
    evento.status = "CANCELADO"
    db.session.commit()
    _sincronizar_calendar("evento", evento, somente_vinculada=True)
    flash("Evento cancelado. O histórico de presença foi preservado.", "warning")
    return redirect(url_for("main.listar_eventos"))


@main_bp.route("/admin/ensaios")
@login_required
@profissional_required
def listar_ensaios():
    ensaios = Ensaio.query.order_by(
        Ensaio.data_ensaio.desc(), Ensaio.id.desc()
    ).all()
    calendar_syncs = {
        sync.ensaio_id: sync
        for sync in GoogleCalendarSync.query.filter(
            GoogleCalendarSync.ensaio_id.isnot(None)
        ).all()
    }
    return render_template(
        "admin_ensaios.html", ensaios=ensaios, calendar_syncs=calendar_syncs
    )


@main_bp.route("/admin/ensaio/<int:ensaio_id>/calendar/sincronizar", methods=["POST"])
@login_required
@profissional_required
def sincronizar_ensaio_calendar(ensaio_id):
    ensaio = _get_or_404(Ensaio, ensaio_id)
    _sincronizar_calendar("ensaio", ensaio)
    return redirect(url_for("main.listar_ensaios"))


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

    return render_template(
        "admin_ensaio_form.html",
        ensaio=None,
        data_inicial=_data_inicial_formulario(),
    )


@main_bp.route("/admin/ensaio/<int:ensaio_id>/edit", methods=["GET", "POST"])
@login_required
@profissional_required
def editar_ensaio(ensaio_id):
    ensaio = _get_or_404(Ensaio, ensaio_id)
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
        _sincronizar_calendar("ensaio", ensaio, somente_vinculada=True)
        flash("Ensaio atualizado com sucesso.", "success")
        return redirect(url_for("main.listar_ensaios"))
    return render_template("admin_ensaio_form.html", ensaio=ensaio)


@main_bp.route("/admin/ensaio/<int:ensaio_id>/cancel", methods=["POST"])
@login_required
@profissional_required
def cancelar_ensaio(ensaio_id):
    ensaio = _get_or_404(Ensaio, ensaio_id)
    ensaio.status = "CANCELADO"
    db.session.commit()
    _sincronizar_calendar("ensaio", ensaio, somente_vinculada=True)
    flash("Ensaio cancelado. O histórico de presença foi preservado.", "warning")
    return redirect(url_for("main.listar_ensaios"))


@main_bp.route("/admin/ensaio/<int:ensaio_id>/presenca", methods=["GET", "POST"])
@login_required
@profissional_required
def registrar_presenca(ensaio_id):
    ensaio = _get_or_404(Ensaio, ensaio_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == "POST":
        registros_salvos = []
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
            registro.registrado_at = datetime.now(timezone.utc)
            registros_salvos.append(registro)

        try:
            db.session.flush()
            for registro in registros_salvos:
                _atualizar_movimento_passe(registro)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("main.registrar_presenca", ensaio_id=ensaio.id))
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
    evento = _get_or_404(Evento, evento_id)
    alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()

    if request.method == "POST":
        registros_salvos = []
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
            registro.registrado_at = datetime.now(timezone.utc)
            registros_salvos.append(registro)
        try:
            db.session.flush()
            for registro in registros_salvos:
                _atualizar_movimento_passe(registro)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("main.registrar_presenca_evento", evento_id=evento.id))
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
    evento = _get_or_404(Evento, evento_id)
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
        db.or_(
            Presenca.ensaio_id.isnot(None),
            Presenca.evento_id.isnot(None),
            Presenca.atividade_id.isnot(None),
        )
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
        data_relatorio = datetime.now(timezone.utc).date()

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
    atividades.extend(
        f"Atividade: {atividade.titulo}"
        + (f" · {atividade.local}" if atividade.local else "")
        for atividade in Atividade.query.filter_by(data_atividade=data_relatorio).all()
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


@main_bp.route("/admin/presencas/resumo")
@login_required
@profissional_required
def resumo_presencas():
    mes_param = request.args.get("mes", "")
    try:
        ano, mes = map(int, mes_param.split("-"))
    except (TypeError, ValueError):
        hoje = datetime.now(timezone.utc)
        ano, mes = hoje.year, hoje.month

    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)

    registros = (
        Presenca.query.filter(Presenca.data_presenca >= inicio, Presenca.data_presenca < fim)
        .order_by(Presenca.data_presenca.desc(), Presenca.id.desc())
        .all()
    )
    registros_ativos = [registro for registro in registros if registro.aluno and registro.aluno.ativo]

    resumo = {
        "total": len(registros_ativos),
        "presentes": sum(1 for registro in registros_ativos if registro.presente),
        "ausentes": sum(1 for registro in registros_ativos if not registro.presente and registro.observacoes != "JUSTIFICADO"),
        "justificados": sum(1 for registro in registros_ativos if registro.observacoes == "JUSTIFICADO"),
    }
    resumo["percentual_presenca"] = round((resumo["presentes"] / resumo["total"]) * 100, 1) if resumo["total"] else 0.0

    por_tipo = {
        "Ensaio": {"total": 0, "presentes": 0},
        "Evento": {"total": 0, "presentes": 0},
        "Atividade": {"total": 0, "presentes": 0},
    }
    for registro in registros_ativos:
        if registro.ensaio_id is not None:
            categoria = "Ensaio"
        elif registro.evento_id is not None:
            categoria = "Evento"
        else:
            categoria = "Atividade"
        por_tipo[categoria]["total"] += 1
        if registro.presente:
            por_tipo[categoria]["presentes"] += 1

    periodo = inicio.strftime("%B de %Y")
    return render_template(
        "admin_resumo_presencas.html",
        mes=f"{ano:04d}-{mes:02d}",
        periodo=periodo,
        resumo=resumo,
        por_tipo=sorted(por_tipo.items()),
        registros=registros_ativos,
    )


@main_bp.route("/admin/presencas/relatorio-profissional")
@login_required
@profissional_required
def relatorio_presenca_profissional():
    mes_param = request.args.get("mes", "")
    try:
        ano, mes = map(int, mes_param.split("-"))
    except (TypeError, ValueError):
        hoje = datetime.now(timezone.utc)
        ano, mes = hoje.year, hoje.month

    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)

    registros = (
        Presenca.query.filter(Presenca.data_presenca >= inicio, Presenca.data_presenca < fim)
        .order_by(Presenca.data_presenca.desc(), Presenca.id.desc())
        .all()
    )
    registros_ativos = [registro for registro in registros if registro.aluno and registro.aluno.ativo]

    resumo_por_aluno = []
    for aluno in Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all():
        dados = [registro for registro in registros_ativos if registro.aluno_id == aluno.id]
        presentes = sum(1 for registro in dados if registro.presente)
        justificados = sum(1 for registro in dados if registro.observacoes == "JUSTIFICADO")
        total = len(dados)
        resumo_por_aluno.append({
            "aluno": aluno,
            "total": total,
            "presentes": presentes,
            "justificados": justificados,
            "percentual": round((presentes / total) * 100, 1) if total else 0.0,
        })

    resumo_por_atividade = {}
    for registro in registros_ativos:
        if registro.ensaio_id is not None:
            titulo = registro.ensaio.titulo if registro.ensaio else "Ensaio sem título"
            categoria = "Ensaio"
        elif registro.evento_id is not None:
            titulo = registro.evento.nome_evento if registro.evento else "Evento sem título"
            categoria = "Evento"
        else:
            titulo = registro.atividade.titulo if registro.atividade else "Atividade sem título"
            categoria = "Atividade"
        chave = (categoria, titulo)
        resumo_por_atividade.setdefault(chave, {"total": 0, "presentes": 0})
        resumo_por_atividade[chave]["total"] += 1
        if registro.presente:
            resumo_por_atividade[chave]["presentes"] += 1

    return render_template(
        "relatorio_presenca_profissional.html",
        mes=f"{ano:04d}-{mes:02d}",
        periodo=inicio.strftime("%B de %Y"),
        registros=registros_ativos,
        resumo_por_aluno=sorted(resumo_por_aluno, key=lambda item: (-item["percentual"], item["aluno"].nome.casefold())),
        resumo_por_atividade=sorted(
            (
                {"categoria": categoria, "titulo": titulo, "total": dados["total"], "presentes": dados["presentes"], "percentual": round((dados["presentes"] / dados["total"]) * 100, 1) if dados["total"] else 0.0}
                for (categoria, titulo), dados in resumo_por_atividade.items()
            ),
            key=lambda item: (-item["percentual"], item["titulo"].casefold()),
        ),
        total_registros=len(registros_ativos),
        total_presentes=sum(1 for registro in registros_ativos if registro.presente),
        total_justificados=sum(1 for registro in registros_ativos if registro.observacoes == "JUSTIFICADO"),
        data_geracao=datetime.now(timezone.utc),
    )


@main_bp.route("/admin/comunicacoes")
@login_required
@profissional_required
@session_timeout
def listar_comunicacoes():
    bloqueio = _bloquear_central_comunicacoes()
    if bloqueio:
        return bloqueio
    update_activity()
    comunicacoes = Comunicacao.query.order_by(Comunicacao.criado_em.desc()).all()
    contatos_externos = ContatoComunicacao.query.order_by(ContatoComunicacao.nome.asc()).all()
    return render_template(
        "admin_comunicacoes.html",
        comunicacoes=comunicacoes,
        contatos_externos=contatos_externos,
    )


@main_bp.route(
    "/admin/comunicacoes/contatos/<int:contato_id>/revogar-email",
    methods=["POST"],
)
@login_required
@profissional_required
def revogar_email_contato_comunicacao(contato_id):
    contato = _get_or_404(ContatoComunicacao, contato_id)
    contato.autorizacao_email = False
    contato.email_revogado_em = datetime.now(timezone.utc)
    db.session.commit()
    flash("Autorização de e-mail revogada para este contato.", "success")
    return redirect(url_for("main.listar_comunicacoes"))


@main_bp.route("/admin/comunicacoes/nova", methods=["GET", "POST"])
@login_required
@profissional_required
def nova_comunicacao():
    bloqueio = _bloquear_central_comunicacoes()
    if bloqueio:
        return bloqueio
    ensaios = Ensaio.query.order_by(Ensaio.data_ensaio.desc()).all()
    eventos = Evento.query.order_by(Evento.data_evento.desc()).all()

    naipes = Naipe.query.order_by(Naipe.nome.asc()).all()
    contatos_externos = ContatoComunicacao.query.filter_by(ativo=True).order_by(ContatoComunicacao.nome.asc()).all()

    if request.method == "POST":
        assunto = (request.form.get("assunto") or "").strip()
        mensagem = (request.form.get("mensagem") or "").strip()
        tipo = (request.form.get("tipo") or "aviso").strip().lower()
        publico = (request.form.get("publico") or "").strip().lower()
        canal = (request.form.get("canal") or "email").strip().lower()
        evento_id = request.form.get("evento_id", type=int)
        ensaio_id = request.form.get("ensaio_id", type=int)
        naipe_id = request.form.get("naipe_id", type=int)
        contato_externo_id = request.form.get("contato_externo_id", type=int)
        contato_email = (request.form.get("contato_email") or "").strip().lower()
        destinatario_nome = (request.form.get("destinatario_nome") or "").strip()
        destinatario_email = (request.form.get("destinatario_email") or "").strip().lower()
        consentimento_email = request.form.get("consentimento_email") == "on"
        origem_consentimento_email = (
            request.form.get("origem_consentimento_email") or ""
        ).strip()

        publicos_validos = {"geral", "responsaveis", "evento", "naipe", "externo"}
        if publico not in publicos_validos:
            flash("Selecione explicitamente o público-alvo da comunicação.", "danger")
            return redirect(url_for("main.nova_comunicacao"))
        if publico != "externo" and (
            contato_externo_id
            or contato_email
            or destinatario_nome
            or destinatario_email
        ):
            flash(
                "Dados de destinatário externo só podem ser usados com o público Contatos externos. "
                "Nenhuma comunicação foi criada.",
                "danger",
            )
            return redirect(url_for("main.nova_comunicacao"))

        contato_externo = None
        if publico == "externo":
            if contato_externo_id:
                contato_externo = db.session.get(ContatoComunicacao, contato_externo_id)
                if not contato_externo or not contato_externo.ativo:
                    flash("Selecione um contato externo ativo.", "danger")
                    return redirect(url_for("main.nova_comunicacao"))
                destinatario_nome = contato_externo.nome
                destinatario_email = (contato_externo.email or "").strip().lower()
            elif contato_email:
                contato_externo = ContatoComunicacao.query.filter_by(
                    email=contato_email,
                    ativo=True,
                ).first()
                if contato_externo:
                    destinatario_nome = contato_externo.nome
                    destinatario_email = contato_externo.email.strip().lower()
                else:
                    flash("Selecione um contato cadastrado ou informe um e-mail avulso.", "danger")
                    return redirect(url_for("main.nova_comunicacao"))

            if not destinatario_email or "@" not in destinatario_email:
                flash("Informe o e-mail do destinatário externo.", "danger")
                return redirect(url_for("main.nova_comunicacao"))
            if not destinatario_nome:
                destinatario_nome = destinatario_email

            if contato_externo is None:
                contato_externo = ContatoComunicacao.query.filter_by(
                    email=destinatario_email
                ).first()
            autorizacao_valida = bool(
                contato_externo
                and contato_externo.ativo
                and contato_externo.autorizacao_email
                and contato_externo.email_revogado_em is None
            )
            if not autorizacao_valida:
                if not consentimento_email or not origem_consentimento_email:
                    flash(
                        "Confirme a autorização de e-mail e informe sua origem para este contato.",
                        "danger",
                    )
                    return redirect(url_for("main.nova_comunicacao"))
                agora = datetime.now(timezone.utc)
                if contato_externo is None:
                    contato_externo = ContatoComunicacao(
                        nome=destinatario_nome,
                        email=destinatario_email,
                        ativo=True,
                    )
                    db.session.add(contato_externo)
                contato_externo.nome = destinatario_nome
                contato_externo.email = destinatario_email
                contato_externo.ativo = True
                contato_externo.autorizacao_email = True
                contato_externo.autorizacao_email_em = agora
                contato_externo.origem_autorizacao_email = origem_consentimento_email
                contato_externo.email_revogado_em = None
                db.session.flush()

        if publico == "evento" and not db.session.get(Evento, evento_id):
            flash("Selecione um evento válido para enviar aos participantes.", "danger")
            return redirect(url_for("main.nova_comunicacao"))

        if not assunto or not mensagem:
            flash("Informe o assunto e o texto da comunicação.", "danger")
            return redirect(url_for("main.nova_comunicacao"))

        comunicacao = Comunicacao(
            assunto=assunto,
            mensagem=mensagem,
            tipo=tipo,
            publico=publico,
            canal=canal,
            status="rascunho",
            criado_por_id=current_user.id,
            evento_id=evento_id,
            ensaio_id=ensaio_id,
            naipe_id=naipe_id,
            contato_externo_id=contato_externo.id if contato_externo else None,
            destinatario_nome=destinatario_nome if publico == "externo" else None,
            destinatario_email=destinatario_email if publico == "externo" else None,
        )
        db.session.add(comunicacao)
        db.session.commit()

        pasta_anexos = os.path.join(
            current_app.config["BASE_DIR"], "instance", "uploads", "comunicacoes"
        )
        os.makedirs(pasta_anexos, exist_ok=True)
        for arquivo in request.files.getlist("anexos"):
            if not arquivo or not arquivo.filename:
                continue
            nome_original = arquivo.filename
            nome_seguro = secure_filename(nome_original)
            if not nome_seguro:
                continue
            nome_arquivo = f"{comunicacao.id}_{nome_seguro}"
            caminho = os.path.join(pasta_anexos, nome_arquivo)
            arquivo.save(caminho)
            db.session.add(ComunicacaoAnexo(
                comunicacao_id=comunicacao.id,
                nome_original=nome_original,
                nome_arquivo=nome_arquivo,
                caminho=caminho,
                tipo_mime=arquivo.mimetype,
                tamanho=os.path.getsize(caminho),
            ))
        db.session.commit()
        flash("Comunicação criada em rascunho. Revise e confirme o envio.", "success")
        return redirect(url_for("main.listar_comunicacoes"))

    return render_template(
        "admin_comunicacao_form.html",
        comunicacao=None,
        ensaios=ensaios,
        eventos=eventos,
        naipes=naipes,
        contatos_externos=contatos_externos,
    )


@main_bp.route("/admin/comunicacoes/<int:comunicacao_id>")
@login_required
@profissional_required
def detalhar_comunicacao(comunicacao_id):
    bloqueio = _bloquear_central_comunicacoes()
    if bloqueio:
        return bloqueio
    comunicacao = _get_or_404(Comunicacao, comunicacao_id)
    destinatarios = comunicacao.destinatarios.order_by(ComunicacaoDestinatario.criado_em.desc()).all()

    detalhes = []
    for destinatario in destinatarios:
        nome_destinatario = "Destinatário removido"
        if destinatario.tipo_destinatario == "integrante":
            aluno = db.session.get(Aluno, destinatario.destinatario_id)
            if aluno:
                nome_destinatario = aluno.nome
        elif destinatario.tipo_destinatario == "contato_externo":
            nome_destinatario = destinatario.destinatario_nome or "Destinatário externo"
            if destinatario.destinatario_email:
                nome_destinatario += f" ({destinatario.destinatario_email})"
        detalhes.append({
            "destinatario": destinatario,
            "nome": nome_destinatario,
        })

    return render_template(
        "admin_comunicacao_detail.html",
        comunicacao=comunicacao,
        detalhes=detalhes,
        destinatarios=destinatarios,
    )


@main_bp.route("/admin/comunicacoes/<int:comunicacao_id>/excluir", methods=["POST"])
@login_required
@profissional_required
def excluir_comunicacao(comunicacao_id):
    comunicacao = _get_or_404(Comunicacao, comunicacao_id)
    if comunicacao.status != "rascunho":
        flash("Somente comunicações em rascunho podem ser excluídas.", "warning")
        return redirect(url_for("main.listar_comunicacoes"))

    db.session.delete(comunicacao)
    for anexo in comunicacao.anexos:
        try:
            os.remove(anexo.caminho)
        except FileNotFoundError:
            pass
    db.session.commit()
    flash("Rascunho excluído.", "success")
    return redirect(url_for("main.listar_comunicacoes"))


@main_bp.route("/admin/comunicacoes/<int:comunicacao_id>/enviar", methods=["POST"])
@login_required
@profissional_required
def enviar_comunicacao(comunicacao_id):
    comunicacao = _get_or_404(Comunicacao, comunicacao_id)
    if comunicacao.publico == "externo":
        contato_externo = db.session.get(
            ContatoComunicacao, comunicacao.contato_externo_id
        ) if comunicacao.contato_externo_id else None
        if not (
            contato_externo
            and contato_externo.ativo
            and contato_externo.autorizacao_email
            and contato_externo.email_revogado_em is None
        ):
            flash(
                "Envio bloqueado: o contato não possui autorização de e-mail vigente.",
                "warning",
            )
            return redirect(url_for("main.listar_comunicacoes"))
    google_status = google_workspace_status(
        obter_configuracao("communication_sender_email")
    )
    if not google_status["available"]:
        flash(
            f"Central de comunicação desativada: {google_status['reason']}",
            "warning",
        )
        return redirect(url_for("main.listar_comunicacoes"))

    destinatarios_criados = 0
    novos_destinatarios = []

    if comunicacao.publico == "geral":
        alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
        for aluno in alunos:
            if not aluno.email:
                continue
            existente = ComunicacaoDestinatario.query.filter_by(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
            ).first()
            if existente:
                continue
            destinatario = ComunicacaoDestinatario(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
                destinatario_nome=aluno.nome,
                destinatario_email=aluno.email,
                canal="email",
                status="pendente",
            )
            db.session.add(destinatario)
            novos_destinatarios.append(destinatario)
            destinatarios_criados += 1
    elif comunicacao.publico == "responsaveis":
        alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
        for aluno in alunos:
            responsavel = Responsavel.query.filter_by(aluno_id=aluno.id).order_by(Responsavel.id.asc()).first()
            if not responsavel or not responsavel.email:
                continue
            existente = ComunicacaoDestinatario.query.filter_by(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="responsavel",
                destinatario_id=responsavel.id,
            ).first()
            if existente:
                continue
            destinatario = ComunicacaoDestinatario(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="responsavel",
                destinatario_id=responsavel.id,
                destinatario_nome=responsavel.nome_pai or responsavel.nome_mae or "Responsável",
                destinatario_email=responsavel.email,
                canal="email",
                status="pendente",
            )
            db.session.add(destinatario)
            novos_destinatarios.append(destinatario)
            destinatarios_criados += 1
    elif comunicacao.publico == "evento":
        if not comunicacao.evento_id:
            flash("Este rascunho não possui um evento definido.", "warning")
            return redirect(url_for("main.listar_comunicacoes"))
        alunos = (
            Aluno.query.join(
                AutorizacaoViagem,
                AutorizacaoViagem.aluno_id == Aluno.id,
            )
            .filter(
                AutorizacaoViagem.evento_id == comunicacao.evento_id,
                AutorizacaoViagem.autorizado.is_(True),
                Aluno.ativo.is_(True),
                Aluno.email.isnot(None),
                Aluno.email != "",
            )
            .distinct()
            .order_by(Aluno.nome)
            .all()
        )
        for aluno in alunos:
            existente = ComunicacaoDestinatario.query.filter_by(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
            ).first()
            if existente:
                continue
            destinatario = ComunicacaoDestinatario(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
                destinatario_nome=aluno.nome,
                destinatario_email=aluno.email,
                canal="email",
                status="pendente",
            )
            db.session.add(destinatario)
            novos_destinatarios.append(destinatario)
            destinatarios_criados += 1
    elif comunicacao.publico == "naipe":
        if not comunicacao.naipe_id:
            flash("Selecione um naipe para enviar a este público.", "warning")
            return redirect(url_for("main.listar_comunicacoes"))
        alunos = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
        for aluno in alunos:
            instrumentos = [assoc.instrumento for assoc in aluno.instrumentos if assoc.instrumento and assoc.instrumento.naipe_id == comunicacao.naipe_id]
            if not instrumentos:
                continue
            if not aluno.email:
                continue
            existente = ComunicacaoDestinatario.query.filter_by(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
            ).first()
            if existente:
                continue
            destinatario = ComunicacaoDestinatario(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="integrante",
                destinatario_id=aluno.id,
                destinatario_nome=aluno.nome,
                destinatario_email=aluno.email,
                canal="email",
                status="pendente",
            )
            db.session.add(destinatario)
            novos_destinatarios.append(destinatario)
            destinatarios_criados += 1
    elif comunicacao.publico == "externo":
        contato_externo = db.session.get(
            ContatoComunicacao, comunicacao.contato_externo_id
        ) if comunicacao.contato_externo_id else None
        if not contato_externo or not contato_externo.email:
            flash("Este rascunho não possui um contato externo selecionado.", "warning")
            return redirect(url_for("main.listar_comunicacoes"))

        existente = ComunicacaoDestinatario.query.filter_by(
            comunicacao_id=comunicacao.id,
            tipo_destinatario="contato_externo",
            destinatario_id=contato_externo.id,
        ).first()
        if not existente:
            destinatario = ComunicacaoDestinatario(
                comunicacao_id=comunicacao.id,
                tipo_destinatario="contato_externo",
                destinatario_id=contato_externo.id,
                destinatario_nome=contato_externo.nome,
                destinatario_email=contato_externo.email.strip().lower(),
                canal="email",
                status="pendente",
            )
            db.session.add(destinatario)
            novos_destinatarios.append(destinatario)
            destinatarios_criados += 1
    else:
        flash("Este público ainda não está configurado.", "info")

    envios_sucesso = 0
    envios_falha = 0
    db.session.flush()
    for destinatario in novos_destinatarios:
        if current_app.testing:
            destinatario.status = "enviado"
            destinatario.enviado_em = datetime.now(timezone.utc)
            envios_sucesso += 1
            continue
        try:
            enviar_email_gmail(
                destinatario.destinatario_email,
                comunicacao.assunto,
                comunicacao.mensagem,
                comunicacao.anexos,
            )
            destinatario.status = "enviado"
            destinatario.enviado_em = datetime.now(timezone.utc)
            envios_sucesso += 1
        except Exception as exc:
            destinatario.status = "erro"
            destinatario.ultimo_erro = str(exc)[:2000]
            envios_falha += 1

    if envios_sucesso > 0 and envios_falha == 0:
        comunicacao.status = "enviado"
    elif envios_sucesso > 0:
        comunicacao.status = "parcial"
    elif envios_falha > 0:
        comunicacao.status = "erro"
    elif comunicacao.destinatarios.count() > 0:
        comunicacao.status = "parcial"
    else:
        comunicacao.status = "rascunho"

    comunicacao.enviado_em = datetime.now(timezone.utc)
    db.session.commit()

    if envios_falha:
        flash("A comunicação foi processada com falhas. Consulte o histórico.", "warning")
    else:
        flash("Envio confirmado para os destinatários elegíveis do público selecionado.", "success")
    return redirect(url_for("main.listar_comunicacoes"))


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
    usuario = _get_or_404(User, user_id)
    
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
    usuario = _get_or_404(User, user_id)
    
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
    user = _get_or_404(User, user_id)
    
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
    user = _get_or_404(User, user_id)
    
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


@main_bp.route("/admin/passes", methods=["GET", "POST"])
@login_required
@admin_required
def gerenciar_passes():
    """Cadastra e consulta cotas mensais de passes por integrante com cartão."""
    mes_parametro = request.values.get("mes_referencia", "")
    try:
        mes_referencia = datetime.strptime(mes_parametro, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        mes_referencia = datetime.now(timezone.utc).date().replace(day=1)

    if request.method == "POST":
        aluno_id = request.form.get("aluno_id", type=int)
        quantidade_texto = request.form.get("quantidade_disponibilizada", "").strip()
        try:
            quantidade = int(quantidade_texto)
        except (TypeError, ValueError):
            quantidade = -1

        aluno = _get_or_404(Aluno, aluno_id)
        if not aluno.cartao_passe or not aluno.cartao_passe.ativo:
            flash("Somente integrantes com cartão de passe ativo podem receber uma cota.", "danger")
            return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))
        if quantidade < 0:
            flash("Informe uma quantidade de passes igual ou maior que zero.", "danger")
            return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))

        cota = CotaMensalPasse.query.filter_by(
            aluno_id=aluno.id,
            mes_referencia=mes_referencia,
        ).first()
        if cota is None:
            cota = CotaMensalPasse(
                aluno_id=aluno.id,
                mes_referencia=mes_referencia,
            )
            db.session.add(cota)
            db.session.flush()
        cota.quantidade_disponibilizada = quantidade
        movimento_inicial = MovimentoPasse.query.filter_by(
            cota_id=cota.id,
            tipo="DISPONIBILIZACAO",
        ).first()
        if movimento_inicial is None:
            db.session.add(MovimentoPasse(
                cota_id=cota.id,
                quantidade=quantidade,
                tipo="DISPONIBILIZACAO",
                motivo="Disponibilização inicial da cota mensal.",
                registrado_por_id=current_user.id,
            ))
        else:
            movimento_inicial.quantidade = quantidade
            movimento_inicial.registrado_por_id = current_user.id
        db.session.commit()
        flash("Cota mensal de passes salva com sucesso.", "success")
        return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))

    integrantes = Aluno.query.filter_by(ativo=True).order_by(Aluno.nome).all()
    alunos_com_cartao = [
        aluno for aluno in integrantes
        if aluno.cartao_passe and aluno.cartao_passe.ativo
    ]
    cotas = {
        cota.aluno_id: cota
        for cota in CotaMensalPasse.query.filter_by(mes_referencia=mes_referencia).all()
    }
    return render_template(
        "admin_passes.html",
        integrantes=integrantes,
        alunos=alunos_com_cartao,
        cotas=cotas,
        saldos={aluno_id: _saldo_cota_passe(cota) for aluno_id, cota in cotas.items()},
        recargas={
            aluno_id: MovimentoPasse.query.filter_by(
                cota_id=cota.id,
                tipo="RECARGA",
            ).first()
            for aluno_id, cota in cotas.items()
        },
        mes_referencia=mes_referencia,
    )


@main_bp.route("/admin/passes/recarga", methods=["POST"])
@login_required
@admin_required
def adicionar_recarga_passe():
    """Registra a única recarga extra mensal, com justificativa administrativa."""
    aluno_id = request.form.get("aluno_id", type=int)
    mes_parametro = request.form.get("mes_referencia", "")
    motivo = request.form.get("motivo", "").strip()
    quantidade_texto = request.form.get("quantidade", "").strip()
    try:
        mes_referencia = datetime.strptime(mes_parametro, "%Y-%m").date().replace(day=1)
        quantidade = int(quantidade_texto)
    except (TypeError, ValueError):
        flash("Informe mês e quantidade válidos para a recarga.", "danger")
        return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_parametro))

    aluno = _get_or_404(Aluno, aluno_id)
    cota = CotaMensalPasse.query.filter_by(
        aluno_id=aluno.id,
        mes_referencia=mes_referencia,
    ).first()
    if not aluno.cartao_passe or not aluno.cartao_passe.ativo:
        flash("Somente integrantes com cartão de passe ativo podem receber recarga.", "danger")
    elif cota is None:
        flash("Cadastre a cota mensal antes de registrar uma recarga extra.", "danger")
    elif quantidade <= 0:
        flash("A recarga extra deve ser maior que zero.", "danger")
    elif not motivo:
        flash("Informe o motivo administrativo da recarga extra.", "danger")
    elif MovimentoPasse.query.filter_by(cota_id=cota.id, tipo="RECARGA").first():
        flash("A recarga extra deste integrante já foi utilizada neste mês.", "danger")
    else:
        db.session.add(MovimentoPasse(
            cota_id=cota.id,
            quantidade=quantidade,
            tipo="RECARGA",
            motivo=motivo,
            registrado_por_id=current_user.id,
        ))
        db.session.commit()
        flash("Recarga extra registrada com sucesso.", "success")
    return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))


@main_bp.route("/admin/passes/lancamento", methods=["POST"])
@login_required
@admin_required
def lancar_passes():
    """Lança a cota mensal ou uma disponibilização avulsa auditada."""
    aluno_id = request.form.get("aluno_id", type=int)
    mes_parametro = request.form.get("mes_referencia", "")
    modo = request.form.get("modo_lancamento", "mensal")
    motivo = request.form.get("motivo", "").strip()
    try:
        mes_referencia = datetime.strptime(mes_parametro, "%Y-%m").date().replace(day=1)
        quantidade = int(request.form.get("quantidade", ""))
    except (TypeError, ValueError):
        flash("Informe mês e quantidade válidos para o lançamento.", "danger")
        return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_parametro))

    aluno = _get_or_404(Aluno, aluno_id)
    if not aluno.cartao_passe or not aluno.cartao_passe.ativo:
        flash("Somente integrantes com cartão de passe ativo podem receber passes.", "danger")
    elif modo not in {"mensal", "avulso"}:
        flash("Selecione o tipo de lançamento.", "danger")
    elif quantidade < 0 or (modo == "avulso" and quantidade == 0):
        flash("A quantidade mensal não pode ser negativa; o avulso deve ser maior que zero.", "danger")
    elif modo == "avulso" and not motivo:
        flash("Informe o motivo do lançamento avulso.", "danger")
    else:
        cota = CotaMensalPasse.query.filter_by(
            aluno_id=aluno.id,
            mes_referencia=mes_referencia,
        ).first()
        if cota is None:
            cota = CotaMensalPasse(
                aluno_id=aluno.id,
                mes_referencia=mes_referencia,
            )
            db.session.add(cota)
            db.session.flush()

        if modo == "mensal":
            cota.quantidade_disponibilizada = quantidade
            movimento = MovimentoPasse.query.filter_by(
                cota_id=cota.id,
                tipo="DISPONIBILIZACAO",
            ).first()
            if movimento is None:
                movimento = MovimentoPasse(
                    cota_id=cota.id,
                    quantidade=quantidade,
                    tipo="DISPONIBILIZACAO",
                    motivo="Lançamento mensal da cota.",
                    registrado_por_id=current_user.id,
                )
                db.session.add(movimento)
            else:
                movimento.quantidade = quantidade
                movimento.registrado_por_id = current_user.id
            flash("Lançamento mensal de passes salvo.", "success")
        elif MovimentoPasse.query.filter_by(cota_id=cota.id, tipo="RECARGA").first():
            flash("O lançamento avulso deste integrante já foi utilizado neste mês.", "danger")
            db.session.rollback()
            return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))
        else:
            db.session.add(MovimentoPasse(
                cota_id=cota.id,
                quantidade=quantidade,
                tipo="RECARGA",
                motivo=motivo,
                registrado_por_id=current_user.id,
            ))
            flash("Lançamento avulso de passes registrado.", "success")
        db.session.commit()

    return redirect(url_for("main.gerenciar_passes", mes_referencia=mes_referencia.strftime("%Y-%m")))


@main_bp.route("/admin/passes/historico")
@login_required
@admin_required
def historico_passes():
    """Consulta administrativa dos movimentos e saldos de passes."""
    mes_parametro = request.args.get("mes_referencia", "")
    try:
        mes_referencia = datetime.strptime(mes_parametro, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        mes_referencia = datetime.now(timezone.utc).date().replace(day=1)

    aluno_id = request.args.get("aluno_id", type=int)
    query = MovimentoPasse.query.join(CotaMensalPasse).filter(
        CotaMensalPasse.mes_referencia == mes_referencia
    )
    if aluno_id:
        query = query.filter(CotaMensalPasse.aluno_id == aluno_id)
    movimentos = query.order_by(MovimentoPasse.data_hora.desc(), MovimentoPasse.id.desc()).all()
    cotas = CotaMensalPasse.query.filter_by(mes_referencia=mes_referencia).order_by(
        CotaMensalPasse.aluno_id
    ).all()
    if aluno_id:
        cotas = [cota for cota in cotas if cota.aluno_id == aluno_id]

    alunos = Aluno.query.order_by(Aluno.nome).all()
    saldos = {cota.id: _saldo_cota_passe(cota) for cota in cotas}
    return render_template(
        "admin_passes_historico.html",
        alunos=alunos,
        aluno_id=aluno_id,
        cotas=cotas,
        movimentos=movimentos,
        saldos=saldos,
        mes_referencia=mes_referencia,
    )


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
        numero_cartao_passe = request.form.get("numero_cartao_passe", "").strip() or None
        
        if not nome:
            flash("Nome é obrigatório.")
            return redirect(url_for("main.criar_aluno"))
        
        if cin_rg and Aluno.query.filter_by(cin_rg=cin_rg).first():
            flash("RG já cadastrado.")
            return redirect(url_for("main.criar_aluno"))

        if numero_cartao_passe and CartaoPasse.query.filter_by(
            numero_controle=numero_cartao_passe
        ).first():
            flash("Número de controle do cartão de passe já cadastrado.")
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

        if numero_cartao_passe:
            db.session.add(CartaoPasse(
                aluno_id=novo_aluno.id,
                numero_controle=numero_cartao_passe,
            ))

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
    aluno = _get_or_404(Aluno, aluno_id)
    
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
        numero_cartao_passe = request.form.get("numero_cartao_passe", "").strip() or None
        
        if not nome:
            flash("Nome é obrigatório.")
            return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))
        
        if cin_rg:
            aluno_existente = Aluno.query.filter_by(cin_rg=cin_rg).first()
            if aluno_existente and aluno_existente.id != aluno_id:
                flash("RG já cadastrado para outro aluno.")
                return redirect(url_for("main.editar_aluno", aluno_id=aluno_id))

        cartao_existente = CartaoPasse.query.filter_by(
            numero_controle=numero_cartao_passe
        ).first() if numero_cartao_passe else None
        if cartao_existente and cartao_existente.aluno_id != aluno.id:
            flash("Número de controle do cartão de passe já cadastrado para outro integrante.")
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

        if aluno.cartao_passe:
            if numero_cartao_passe:
                aluno.cartao_passe.numero_controle = numero_cartao_passe
                aluno.cartao_passe.ativo = True
            else:
                db.session.delete(aluno.cartao_passe)
        elif numero_cartao_passe:
            aluno.cartao_passe = CartaoPasse(numero_controle=numero_cartao_passe)

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
            instrumento_atual.data_devolucao = datetime.now(timezone.utc).date()

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
    aluno = _get_or_404(Aluno, aluno_id)
    
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
    aluno = _get_or_404(Aluno, aluno_id)
    
    aluno.ativo = False
    db.session.commit()
    
    flash("Aluno inativado com sucesso! (Dados preservados)")
    return redirect(url_for("main.listar_alunos"))


@main_bp.route("/admin/aluno/hard-delete/<int:aluno_id>", methods=["POST"])
@login_required
@admin_required
def hard_delete_aluno(aluno_id):
    aluno = _get_or_404(Aluno, aluno_id)

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
    escola = _get_or_404(Escola, escola_id)
    
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
    inst = _get_or_404(Instrumento, instrumento_id)
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
    inst = _get_or_404(Instrumento, instrumento_id)
    inst.ativo = not inst.ativo
    db.session.commit()
    flash(f"Instrumento {'ativado' if inst.ativo else 'inativado'}")
    return redirect(url_for("main.listar_instrumentos"))


@main_bp.route("/admin/instrumento/delete/<int:instrumento_id>", methods=["POST"])
@login_required
@profissional_required
def excluir_instrumento(instrumento_id):
    inst = _get_or_404(Instrumento, instrumento_id)
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
    tipo = _get_or_404(TipoInstrumento, tipo_id)
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
    tipo = _get_or_404(TipoInstrumento, tipo_id)
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
    naipe = _get_or_404(Naipe, naipe_id)
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
    naipe = _get_or_404(Naipe, naipe_id)
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
    escola = _get_or_404(Escola, escola_id)
    
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

        # Verificação real do conteúdo (magic bytes): rejeita um .txt renomeado
        # para .png ou qualquer arquivo que não seja uma imagem de verdade.
        if not _eh_imagem_valida(foto_file):
            return None

        filename = f"aluno_{aluno_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"

        upload_folder = os.path.join('static', 'uploads', 'alunos')
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        foto_file.save(filepath)

        return os.path.join('uploads', 'alunos', filename)

    return None


def _eh_imagem_valida(foto_file):
    """Confirma que os primeiros bytes do arquivo correspondem a uma imagem real."""
    try:
        cabecera = foto_file.read(12)
        foto_file.seek(0)
    except Exception:
        return False
    return (
        cabecera.startswith(b'\xff\xd8\xff')            # JPEG
        or cabecera.startswith(b'\x89PNG\r\n\x1a\n')     # PNG
        or cabecera.startswith(b'GIF87a')
        or cabecera.startswith(b'GIF89a')
        or (cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP')  # WebP
    )


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
    try:
        google_drive_authorized = has_scope(GOOGLE_DRIVE_FILE_SCOPE)
    except RuntimeError:
        google_drive_authorized = False
    google_drive_backups = []
    google_drive_error = None
    if google_drive_authorized:
        try:
            google_drive_backups = listar_backups_drive()
        except (RuntimeError, ValueError, requests.RequestException):
            current_app.logger.exception("Falha ao listar backups no Google Drive")
            google_drive_error = "Não foi possível consultar o Google Drive. Tente novamente."
    return render_template(
        "admin_backup.html",
        backups=backups,
        db_existe=db_existe,
        db_tamanho=db_tamanho,
        google_drive_authorized=google_drive_authorized,
        google_drive_backups=google_drive_backups,
        google_drive_error=google_drive_error,
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
        current_app.logger.exception("Erro ao criar backup")
        flash("Não foi possível criar o backup. Tente novamente.", "error")
    return redirect(url_for("main.painel_backup"))


@main_bp.route("/admin/backup/enviar-drive", methods=["POST"])
@login_required
@admin_required
def enviar_backup_drive():
    nome_backup = request.form.get("nome_backup")
    caminho_backup = obter_caminho_backup(nome_backup)
    if not caminho_backup:
        flash("Arquivo de backup local não encontrado.", "danger")
        return redirect(url_for("main.painel_backup"))

    try:
        backup_drive = enviar_backup_para_drive(caminho_backup)
        flash(f"Backup enviado ao Google Drive: {backup_drive['name']}.", "success")
    except ValueError as exc:
        flash(str(exc), "warning")
    except (RuntimeError, OSError, requests.RequestException):
        current_app.logger.exception("Falha ao enviar backup para o Google Drive")
        flash(
            "O backup local foi preservado, mas não foi possível enviá-lo ao Google Drive. Verifique a autorização e tente novamente.",
            "warning",
        )
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
        current_app.logger.exception("Erro ao restaurar backup")
        flash("Não foi possível restaurar o backup. Tente novamente.", "error")

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


@main_bp.route("/admin/configuracoes/backup-password/revelar", methods=["POST"])
@login_required
@admin_required
def revelar_senha_backup():
    erro = _reautenticar_admin_para_senha_backup(
        request.form.get("admin_password")
    )
    if erro:
        return _resposta_senha_backup({"error": erro[0]}, erro[1])

    try:
        senha_backup = obter_senha_backup(criar=False)
    except (RuntimeError, ValueError):
        current_app.logger.exception("Falha ao ler a senha de criptografia dos backups")
        return _resposta_senha_backup(
            {"error": "Não foi possível ler a configuração da senha de backup."}, 500
        )
    if not senha_backup:
        return _resposta_senha_backup(
            {"error": "A senha será criada ao gerar o primeiro backup ou pode ser definida abaixo."},
            404,
        )
    return _resposta_senha_backup({"backup_password": senha_backup})


@main_bp.route("/admin/configuracoes/backup-password/registrar", methods=["POST"])
@login_required
@admin_required
def registrar_senha_backup():
    erro = _reautenticar_admin_para_senha_backup(
        request.form.get("admin_password")
    )
    if erro:
        return _resposta_senha_backup({"error": erro[0]}, erro[1])

    senha = request.form.get("backup_password", "")
    confirmacao = request.form.get("backup_password_confirm", "")
    if len(senha) < 16:
        return _resposta_senha_backup(
            {"error": "Use uma senha com pelo menos 16 caracteres."}, 400
        )
    if not hmac.compare_digest(senha, confirmacao):
        return _resposta_senha_backup(
            {"error": "A confirmação da senha não coincide."}, 400
        )

    try:
        senha_atual = obter_senha_backup(criar=False)
        if senha_atual and not hmac.compare_digest(senha, senha_atual):
            return _resposta_senha_backup(
                {
                    "error": "Já existe uma senha que protege backups anteriores. Revele e registre a mesma senha; trocá-la exige recriar os backups existentes."
                },
                409,
            )
        local_password_path = (
            Path(current_app.config["BASE_DIR"]) / "instance" / ".backup_password"
        )
        if local_password_path.is_file():
            senha_local = local_password_path.read_text(encoding="utf-8").strip()
            if not hmac.compare_digest(senha, senha_local):
                return _resposta_senha_backup(
                    {
                        "error": "Esta instalação já usa outra chave local. Registre exatamente a chave atual para preservar os backups."
                    },
                    409,
                )
        if not senha_atual and any(
            arquivo.get("criptografado") for arquivo in listar_backups()
        ):
            return _resposta_senha_backup(
                {
                    "error": "Há backups criptografados, mas a chave atual não está disponível. Não é seguro substituí-la."
                },
                409,
            )

        env_path = Path(current_app.config["BASE_DIR"]) / ".env"
        sucesso, _, _ = set_key(
            str(env_path),
            "BACKUP_PASSWORD",
            senha,
            quote_mode="always",
            encoding="utf-8",
        )
        if not sucesso:
            raise OSError("Não foi possível atualizar o arquivo .env.")
        os.chmod(env_path, 0o600)
        current_app.config["BACKUP_PASSWORD"] = senha
        if senha_atual and local_password_path.is_file():
            local_password_path.unlink()
    except (OSError, RuntimeError, ValueError):
        current_app.logger.exception("Falha ao registrar a senha de backup")
        return _resposta_senha_backup(
            {"error": "Não foi possível registrar a senha no .env."}, 500
        )

    return _resposta_senha_backup(
        {"message": "Senha de backup registrada no .env com segurança."}
    )


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
        if "email-remetente-comunicacao" in request.form:
            remetente = request.form.get(
                "email-remetente-comunicacao", ""
            ).strip().lower()
            if remetente and not is_gmail_sender(remetente):
                flash("O remetente deve utilizar um endereço @gmail.com.", "warning")
                return redirect(url_for("main.configuracoes"))
            valores["communication_sender_email"] = remetente
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

    try:
        gmail_authorized = has_scope(GMAIL_SEND_SCOPE)
        calendar_authorized = has_scope(GOOGLE_CALENDAR_EVENTS_SCOPE)
        google_drive_authorized = has_scope(GOOGLE_DRIVE_FILE_SCOPE)
    except RuntimeError:
        gmail_authorized = False
        calendar_authorized = False
        google_drive_authorized = False

    return render_template(
        "admin_configuracoes.html",
        google_oauth_configured=gmail_authorized,
        google_calendar_authorized=calendar_authorized,
        google_drive_authorized=google_drive_authorized,
        backup_password_env_set=bool(current_app.config.get("BACKUP_PASSWORD")),
        backup_password_local_exists=os.path.isfile(
            os.path.join(current_app.config["BASE_DIR"], "instance", ".backup_password")
        ),
        google_workspace_status=google_workspace_status(
            obter_configuracao("communication_sender_email")
        ),
    )


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
    except Exception:
        current_app.logger.exception("Erro ao limpar cache")
        flash("Não foi possível limpar o cache. Tente novamente.", "danger")

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

    except Exception:
        current_app.logger.exception("Erro na verificação de integridade")
        flash("Não foi possível verificar a integridade do banco. Tente novamente.", "danger")

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

    except Exception:
        current_app.logger.exception("Erro na reindexação")
        flash("Não foi possível reindexar o banco. Tente novamente.", "danger")

    return redirect(url_for("main.configuracoes"))

