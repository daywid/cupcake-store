"""CONTROLLER – UC04 Gerenciar Carrinho."""
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Carrinho, ItemCarrinho, Produto

bp = Blueprint("carrinho", __name__, url_prefix="/carrinho")


def cliente_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.tipo != "cliente":
            flash("Esta área é exclusiva para clientes.", "warning")
            return redirect(url_for("catalogo.index"))
        if current_user.carrinho is None:
            current_user.carrinho = Carrinho()
            db.session.commit()
        return view(*args, **kwargs)
    return wrapper


@bp.route("/")
@cliente_required
def ver():
    return render_template("loja/carrinho.html", carrinho=current_user.carrinho)


@bp.route("/adicionar/<int:produto_id>", methods=["POST"])
@cliente_required
def adicionar(produto_id):
    produto = db.session.get(Produto, produto_id)
    if not produto or not produto.ativo:
        abort(404)
    qtd = max(1, request.form.get("quantidade", 1, type=int))
    atual = next((i.quantidade for i in current_user.carrinho.itens if i.produto_id == produto.id), 0)
    if atual + qtd > produto.estoque:  # RN01 já no carrinho
        flash(f"Só temos {produto.estoque} unidade(s) de {produto.nome} em estoque.", "warning")
    else:
        current_user.carrinho.adicionar_item(produto, qtd)
        db.session.commit()
        flash(f"{produto.nome} adicionado ao carrinho.", "success")
    return redirect(request.referrer or url_for("catalogo.index"))


def _item_do_cliente(item_id):
    item = db.session.get(ItemCarrinho, item_id)
    if not item or item.carrinho_id != current_user.carrinho.id:
        abort(404)
    return item


@bp.route("/atualizar/<int:item_id>", methods=["POST"])
@cliente_required
def atualizar(item_id):
    item = _item_do_cliente(item_id)
    qtd = request.form.get("quantidade", type=int) or 0
    if qtd <= 0:
        db.session.delete(item)
        flash("Item removido do carrinho.", "info")
    elif qtd > item.produto.estoque:
        flash(f"Só temos {item.produto.estoque} unidade(s) de {item.produto.nome}.", "warning")
    else:
        item.quantidade = qtd
    db.session.commit()
    return redirect(url_for("carrinho.ver"))


@bp.route("/remover/<int:item_id>", methods=["POST"])
@cliente_required
def remover(item_id):
    db.session.delete(_item_do_cliente(item_id))
    db.session.commit()
    flash("Item removido do carrinho.", "info")
    return redirect(url_for("carrinho.ver"))
