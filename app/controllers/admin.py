"""CONTROLLER – UC09 Gerenciar Produtos, UC10 Gerenciar Pedidos, UC11 Entrega, UC12 Relatório."""
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..forms import ProdutoForm, StatusPedidoForm
from ..models import (Categoria, Entregador, ItemPedido, Pedido, Produto, StatusEntrega,
                      StatusPedido)
from ..services import regras
from ..utils import inicio_do_dia_utc

bp = Blueprint("admin", __name__, url_prefix="/admin")

VENDIDOS = (StatusPedido.PAGO, StatusPedido.EM_PREPARO, StatusPedido.SAIU_PARA_ENTREGA,
            StatusPedido.ENTREGUE)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@bp.route("/")
@admin_required
def dashboard():
    regras.cancelar_pedidos_expirados()
    hoje = inicio_do_dia_utc()
    resumo = {
        "pedidos_hoje": Pedido.query.filter(Pedido.data_pedido >= hoje).count(),
        "faturamento_hoje": db.session.query(func.coalesce(func.sum(Pedido.valor_total), 0))
        .filter(Pedido.data_pedido >= hoje, Pedido.status.in_(VENDIDOS)).scalar(),
        "em_andamento": Pedido.query.filter(Pedido.status.in_(
            [StatusPedido.PAGO, StatusPedido.EM_PREPARO, StatusPedido.SAIU_PARA_ENTREGA])).count(),
        "estoque_baixo": Produto.query.filter(Produto.ativo.is_(True), Produto.estoque < 5).all(),
    }
    ultimos = Pedido.query.order_by(Pedido.data_pedido.desc()).limit(8).all()
    return render_template("admin/dashboard.html", r=resumo, ultimos=ultimos)


# ------------------------------------------------------------------ produtos (UC09)
@bp.route("/produtos")
@admin_required
def produtos():
    lista = Produto.query.order_by(Produto.ativo.desc(), Produto.nome).all()
    return render_template("admin/produtos.html", produtos=lista)


def _form_produto(produto=None):
    form = ProdutoForm(obj=produto)
    form.categoria_id.choices = [(c.id, c.nome) for c in Categoria.query.order_by(Categoria.nome)]
    return form


@bp.route("/produtos/novo", methods=["GET", "POST"])
@bp.route("/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
@admin_required
def produto_form(produto_id=None):
    produto = db.session.get(Produto, produto_id) if produto_id else None
    if produto_id and not produto:
        abort(404)
    form = _form_produto(produto)
    if form.validate_on_submit():  # RN07 validada pelo formulário
        produto = produto or Produto()
        form.populate_obj(produto)
        db.session.add(produto)
        db.session.commit()
        flash("Produto salvo com sucesso.", "success")
        return redirect(url_for("admin.produtos"))
    return render_template("admin/produto_form.html", form=form, produto=produto)


@bp.route("/produtos/<int:produto_id>/alternar", methods=["POST"])
@admin_required
def produto_alternar(produto_id):
    produto = db.session.get(Produto, produto_id) or abort(404)
    produto.ativo = not produto.ativo  # RN08 – exclusão lógica
    db.session.commit()
    flash(f"{produto.nome} {'ativado' if produto.ativo else 'desativado'}.", "info")
    return redirect(url_for("admin.produtos"))


# ------------------------------------------------------------------ pedidos (UC10 / UC11)
@bp.route("/pedidos")
@admin_required
def pedidos():
    regras.cancelar_pedidos_expirados()
    filtro = request.args.get("status")
    consulta = Pedido.query
    if filtro in StatusPedido.__members__:
        consulta = consulta.filter_by(status=StatusPedido[filtro])
    lista = consulta.order_by(Pedido.data_pedido.desc()).all()
    return render_template("admin/pedidos.html", pedidos=lista, filtro=filtro, status=StatusPedido)


@bp.route("/pedidos/<int:pedido_id>", methods=["GET", "POST"])
@admin_required
def pedido(pedido_id):
    p = db.session.get(Pedido, pedido_id) or abort(404)
    form = StatusPedidoForm()
    permitidos = [s for s in StatusPedido if s != StatusPedido.AGUARDANDO_PAGAMENTO]
    form.status.choices = [(s.name, s.value) for s in permitidos]
    form.entregador_id.choices = [(0, "— sem entregador —")] + [
        (e.id, e.nome) for e in Entregador.query.order_by(Entregador.nome)]
    if request.method == "GET":
        form.status.data = p.status.name
        form.entregador_id.data = p.entrega.entregador_id if p.entrega and p.entrega.entregador_id else 0

    if form.validate_on_submit():
        if p.status in (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO):
            flash("Pedidos não pagos ou cancelados não podem mudar de status.", "warning")
        else:
            novo = StatusPedido[form.status.data]
            p.status = novo
            if p.entrega:
                p.entrega.entregador_id = form.entregador_id.data or None
                if novo == StatusPedido.SAIU_PARA_ENTREGA:
                    p.entrega.status = StatusEntrega.EM_ROTA
                elif novo == StatusPedido.ENTREGUE:
                    p.entrega.status = StatusEntrega.ENTREGUE
                    p.entrega.data_entrega = datetime.utcnow()
            db.session.commit()
            flash(f"Pedido nº {p.id} atualizado para \"{novo.value}\".", "success")
        return redirect(url_for("admin.pedido", pedido_id=p.id))
    return render_template("admin/pedido.html", p=p, form=form)


# ------------------------------------------------------------------ relatório (UC12)
@bp.route("/relatorio")
@admin_required
def relatorio():
    try:
        fim = date.fromisoformat(request.args.get("fim", ""))
    except ValueError:
        fim = date.today()
    try:
        inicio = date.fromisoformat(request.args.get("inicio", ""))
    except ValueError:
        inicio = fim - timedelta(days=30)
    dt_ini = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    base = Pedido.query.filter(Pedido.data_pedido.between(dt_ini, dt_fim),
                               Pedido.status.in_(VENDIDOS))
    pedidos = base.order_by(Pedido.data_pedido).all()
    total = sum((p.valor_total for p in pedidos), 0)
    ranking = (db.session.query(Produto.nome, func.sum(ItemPedido.quantidade).label("qtd"),
                                func.sum(ItemPedido.quantidade * ItemPedido.preco_unitario).label("receita"))
               .join(ItemPedido.produto).join(ItemPedido.pedido)
               .filter(Pedido.data_pedido.between(dt_ini, dt_fim), Pedido.status.in_(VENDIDOS))
               .group_by(Produto.nome).order_by(func.sum(ItemPedido.quantidade).desc()).all())
    return render_template("admin/relatorio.html", inicio=inicio, fim=fim, pedidos=pedidos,
                           total=total, ranking=ranking,
                           ticket=(total / len(pedidos)) if pedidos else 0)
