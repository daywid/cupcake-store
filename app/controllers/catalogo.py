"""CONTROLLER – UC03 Consultar Catálogo (aberto a visitantes)."""
from flask import Blueprint, abort, render_template, request

from ..extensions import db
from ..models import Categoria, Produto

bp = Blueprint("catalogo", __name__)


@bp.route("/")
def index():
    categoria_id = request.args.get("categoria", type=int)
    busca = (request.args.get("q") or "").strip()
    consulta = Produto.query.filter_by(ativo=True)
    if categoria_id:
        consulta = consulta.filter_by(categoria_id=categoria_id)
    if busca:
        termo = f"%{busca}%"
        consulta = consulta.filter(Produto.nome.ilike(termo) | Produto.sabor.ilike(termo))
    produtos = consulta.order_by(Produto.nome).all()
    categorias = Categoria.query.order_by(Categoria.nome).all()
    return render_template("loja/index.html", produtos=produtos, categorias=categorias,
                           categoria_id=categoria_id, busca=busca)


@bp.route("/produto/<int:produto_id>")
def produto(produto_id):
    p = db.session.get(Produto, produto_id)
    if not p or not p.ativo:
        abort(404)
    return render_template("loja/produto.html", p=p)
