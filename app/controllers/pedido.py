"""CONTROLLER – UC05 Realizar Pedido, UC06 Efetuar Pagamento, UC07 Acompanhar e UC08 Avaliar."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..forms import AvaliacaoForm, CartaoForm, CheckoutForm, EnderecoForm
from ..models import (Avaliacao, Endereco, FormaPagamento, Pedido, StatusPagamento,
                      StatusPedido)
from ..services import pagamento as gateway
from ..services import regras
from ..services.regras import RegraNegocioError
from ..utils import area_atendida
from .carrinho import cliente_required

bp = Blueprint("pedido", __name__)


def _pedido_do_cliente(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido or pedido.cliente_id != current_user.id:
        abort(404)
    return pedido


# ------------------------------------------------------------------ endereços
@bp.route("/enderecos/novo", methods=["GET", "POST"])
@cliente_required
def novo_endereco():
    form = EnderecoForm()
    if form.validate_on_submit():
        if not regras.cep_atendido(form.cep.data):  # RN04 – curso alternativo Beta do UC05
            form.cep.errors.append(f"Ainda não entregamos neste CEP. Atendemos a {area_atendida()}.")
            return render_template("loja/endereco_form.html", form=form)
        end = Endereco(cliente=current_user, uf=form.uf.data.upper(),
                       **{k: getattr(form, k).data for k in
                          ("cep", "logradouro", "numero", "complemento", "bairro", "cidade")})
        db.session.add(end)
        db.session.commit()
        flash("Endereço cadastrado.", "success")
        if request.args.get("voltar") == "checkout":
            return redirect(url_for("pedido.checkout"))
        return redirect(url_for("pedido.meus_pedidos"))
    return render_template("loja/endereco_form.html", form=form)


# ------------------------------------------------------------------ checkout (UC05)
@bp.route("/checkout", methods=["GET", "POST"])
@cliente_required
def checkout():
    carrinho = current_user.carrinho
    if not carrinho.itens:
        flash("Seu carrinho está vazio.", "info")
        return redirect(url_for("catalogo.index"))

    faltando = regras.validar_estoque(carrinho.itens)  # RN01 – curso alternativo Alfa
    if faltando:
        for i in faltando:
            flash(f"{i.produto.nome}: estoque disponível {i.produto.estoque}. Ajuste a quantidade.",
                  "warning")
        return redirect(url_for("carrinho.ver"))

    enderecos = current_user.enderecos
    if not enderecos:
        flash("Cadastre um endereço de entrega para continuar.", "info")
        return redirect(url_for("pedido.novo_endereco", voltar="checkout"))

    form = CheckoutForm()
    form.endereco_id.choices = [(e.id, str(e)) for e in enderecos]
    # Padrão: o endereço mais recente dentro da área atendida (RN04)
    padrao = next((e for e in reversed(enderecos) if regras.cep_atendido(e.cep)), enderecos[-1])
    if request.method == "GET":
        form.endereco_id.data = padrao.id

    endereco = next((e for e in enderecos if e.id == form.endereco_id.data), padrao)
    cupom, erro_taxa = None, None
    try:
        cupom = regras.buscar_cupom(form.cupom.data)
    except RegraNegocioError as e:
        form.cupom.errors = [str(e)]
    try:
        taxa = regras.calcular_taxa_entrega(endereco.cep)
    except RegraNegocioError as e:
        erro_taxa, taxa = str(e), 0
    valores = regras.calcular_valores(carrinho.calcular_total(), cupom, taxa)

    if request.method == "POST" and request.form.get("acao") == "confirmar" and form.validate():
        if erro_taxa:
            flash(erro_taxa, "danger")
        elif form.cupom.errors:
            flash("Corrija o cupom ou deixe o campo em branco.", "danger")
        else:
            try:
                pedido = regras.criar_pedido(current_user, endereco,
                                             FormaPagamento[form.forma.data], cupom)
            except RegraNegocioError as e:
                flash(str(e), "danger")
                return redirect(url_for("carrinho.ver"))
            return redirect(url_for("pedido.pagamento", pedido_id=pedido.id))
    elif request.method == "POST" and cupom:
        flash(f"Cupom {cupom.codigo} aplicado: {cupom.percentual:.0f}% de desconto.", "success")

    return render_template("loja/checkout.html", form=form, carrinho=carrinho, valores=valores,
                           erro_taxa=erro_taxa, cupom=cupom)


# ------------------------------------------------------------------ pagamento (UC06)
@bp.route("/pedido/<int:pedido_id>/pagamento", methods=["GET", "POST"])
@cliente_required
def pagamento(pedido_id):
    pedido = _pedido_do_cliente(pedido_id)
    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        return redirect(url_for("pedido.detalhe", pedido_id=pedido.id))
    if regras.prazo_pagamento_expirado(pedido):  # RN05 / RN06
        pedido.cancelar()
        db.session.commit()
        flash("O prazo para pagamento expirou e o pedido foi cancelado.", "warning")
        return redirect(url_for("pedido.detalhe", pedido_id=pedido.id))

    forma = pedido.pagamento.forma
    form = CartaoForm()
    if request.method == "POST":
        if forma == FormaPagamento.PIX:
            resposta = gateway.autorizar_pix(pedido)
        elif form.validate():
            resposta = gateway.autorizar_cartao(form.numero.data, form.validade.data, form.cvv.data)
        else:
            resposta = None

        if resposta and resposta.aprovado:
            regras.confirmar_pagamento(pedido, resposta.codigo)
            flash(f"Pagamento aprovado! Pedido nº {pedido.id} confirmado.", "success")
            return redirect(url_for("pedido.detalhe", pedido_id=pedido.id, novo=1))
        if resposta:
            regras.registrar_recusa(pedido)
            if pedido.status == StatusPedido.CANCELADO:
                flash("Pagamento recusado 3 vezes. O pedido foi cancelado.", "danger")
                return redirect(url_for("pedido.detalhe", pedido_id=pedido.id))
            flash(f"{resposta.motivo} Tente novamente ou use outra forma de pagamento.", "danger")

    return render_template("loja/pagamento.html", pedido=pedido, form=form,
                           pix=gateway.gerar_pix(pedido) if forma == FormaPagamento.PIX else None,
                           formas=FormaPagamento)


@bp.route("/pedido/<int:pedido_id>/forma-pagamento", methods=["POST"])
@cliente_required
def trocar_forma(pedido_id):
    pedido = _pedido_do_cliente(pedido_id)
    if pedido.status == StatusPedido.AGUARDANDO_PAGAMENTO:
        try:
            pedido.pagamento.forma = FormaPagamento[request.form.get("forma", "")]
            pedido.pagamento.status = StatusPagamento.PENDENTE
            db.session.commit()
        except KeyError:
            abort(400)
    return redirect(url_for("pedido.pagamento", pedido_id=pedido.id))


# ------------------------------------------------------------------ acompanhar (UC07) / avaliar (UC08)
@bp.route("/pedidos")
@cliente_required
def meus_pedidos():
    regras.cancelar_pedidos_expirados()
    return render_template("loja/pedidos.html", pedidos=current_user.pedidos)


@bp.route("/pedido/<int:pedido_id>")
@cliente_required
def detalhe(pedido_id):
    pedido = _pedido_do_cliente(pedido_id)
    return render_template("loja/pedido_detalhe.html", pedido=pedido, form=AvaliacaoForm(),
                           etapas=[StatusPedido.PAGO, StatusPedido.EM_PREPARO,
                                   StatusPedido.SAIU_PARA_ENTREGA, StatusPedido.ENTREGUE])


@bp.route("/pedido/<int:pedido_id>/cancelar", methods=["POST"])
@cliente_required
def cancelar(pedido_id):
    pedido = _pedido_do_cliente(pedido_id)
    if pedido.status == StatusPedido.AGUARDANDO_PAGAMENTO:
        pedido.cancelar()
        regras.devolver_ao_carrinho(pedido)
        db.session.commit()
        flash("Pedido cancelado. Os itens voltaram para o seu carrinho.", "info")
    else:
        flash("Somente pedidos aguardando pagamento podem ser cancelados.", "warning")
    return redirect(url_for("pedido.detalhe", pedido_id=pedido.id))


@bp.route("/pedido/<int:pedido_id>/avaliar", methods=["POST"])
@cliente_required
def avaliar(pedido_id):
    pedido = _pedido_do_cliente(pedido_id)
    form = AvaliacaoForm()
    if pedido.status != StatusPedido.ENTREGUE:
        flash("Você poderá avaliar depois que o pedido for entregue.", "warning")
    elif pedido.avaliacao:
        flash("Este pedido já foi avaliado.", "info")
    elif form.validate_on_submit():
        pedido.avaliacao = Avaliacao(nota=form.nota.data, comentario=form.comentario.data)
        db.session.commit()
        flash("Obrigado pela avaliação!", "success")
    return redirect(url_for("pedido.detalhe", pedido_id=pedido.id))
