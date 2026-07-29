from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .utils import session_timeout, update_activity, validar_senha_complexidade
from datetime import datetime, timedelta
from .models import User
from . import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Usuário ou senha inválidos.")
            return redirect(url_for("auth.login"))

        # Verifica bloqueio
        if user.blocked_until and user.blocked_until > datetime.utcnow():
            flash("Usuário bloqueado por 12 horas.")
            return redirect(url_for("auth.login"))

        if user.check_password(password):
            user.login_attempts = 0
            user.blocked_until = None
            db.session.commit()

            login_user(user, remember=False)
            update_activity()

            if user.must_change_password:
                return redirect(url_for("auth.change_password"))

            return redirect(url_for("main.dashboard"))

        else:
            user.login_attempts += 1
            limite_tentativas = current_app.config.get("LOGIN_ATTEMPTS_LIMIT", 3)
            try:
                limite_tentativas = int(limite_tentativas)
            except (TypeError, ValueError):
                limite_tentativas = 3
            if limite_tentativas <= 0:
                limite_tentativas = 3

            if user.login_attempts >= limite_tentativas:
                user.blocked_until = datetime.utcnow() + timedelta(hours=12)
                user.login_attempts = 0
                flash("Usuário bloqueado por 12 horas.")
            else:
                flash("Usuário ou senha inválidos.")

            db.session.commit()
            return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
@session_timeout
def logout():
    update_activity()
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
@session_timeout
def change_password():
    update_activity()
    if request.method == "POST":
        senha_atual = request.form.get("current_password")
        nova_senha = request.form.get("new_password")
        confirmar_senha = request.form.get("confirm_password")

        if not current_user.check_password(senha_atual):
            flash("Senha atual incorreta.")
            return redirect(url_for("auth.change_password"))

        if nova_senha != confirmar_senha:
            flash("As senhas não coincidem.")
            return redirect(url_for("auth.change_password"))

        valida, mensagem = validar_senha_complexidade(nova_senha)
        if not valida:
            flash(mensagem)
            return redirect(url_for("auth.change_password"))

        current_user.set_password(nova_senha)
        current_user.must_change_password = False
        db.session.commit()

        flash("Senha alterada com sucesso.")
        return redirect(url_for("main.dashboard"))

    return render_template("change_password.html")
