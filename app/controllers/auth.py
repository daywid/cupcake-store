"""CONTROLLER – UC01 Cadastrar-se e UC02 Fazer Login."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import CadastroForm, LoginForm
from ..models import Carrinho, Cliente, Usuario
from ..services.validadores import somente_digitos

bp = Blueprint("auth", __name__)


def _destino_seguro(nxt):
    return nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else None


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("catalogo.index"))
    form = CadastroForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        cpf = somente_digitos(form.cpf.data)
        # Curso alternativo Beta do UC01
        if Usuario.query.filter((Usuario.email == email) | (Usuario.cpf == cpf)).first():
            flash("Já existe uma conta com este e-mail ou CPF. Faça login.", "warning")
            return redirect(url_for("auth.login"))
        cliente = Cliente(nome=form.nome.data.strip(), email=email, cpf=cpf,
                          telefone=form.telefone.data)
        cliente.definir_senha(form.senha.data)
        cliente.carrinho = Carrinho()
        db.session.add(cliente)
        db.session.commit()
        login_user(cliente)
        flash(f"Bem-vindo(a), {cliente.nome.split()[0]}! Sua conta foi criada.", "success")
        return redirect(url_for("catalogo.index"))
    return render_template("auth/cadastro.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("catalogo.index"))
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.strip().lower()).first()
        if usuario and usuario.autenticar(form.senha.data):
            login_user(usuario, remember=form.lembrar.data)
            flash(f"Olá, {usuario.nome.split()[0]}!", "success")
            padrao = url_for("admin.dashboard") if usuario.is_admin else url_for("catalogo.index")
            return redirect(_destino_seguro(request.args.get("next")) or padrao)
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("catalogo.index"))
