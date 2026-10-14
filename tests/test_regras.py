from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Cliente, FormaPagamento, Produto, StatusPedido
from app.services import regras
from app.services.regras import RegraNegocioError


def _cliente_com_itens(*itens):
    c = Cliente.query.filter_by(email="cliente@cupcake.com").one()
    for nome, qtd in itens:
        c.carrinho.adicionar_item(Produto.query.filter_by(nome=nome).one(), qtd)
    db.session.commit()
    return c


def test_taxa_entrega_rn02_rn04(app):
    assert regras.calcular_taxa_entrega("01310-100") == Decimal("5.00")
    assert regras.calcular_taxa_entrega("08000-000") == Decimal("9.90")
    with pytest.raises(RegraNegocioError):
        regras.calcular_taxa_entrega("20000-000")  # Rio de Janeiro: fora da área


def test_total_com_cupom_rn03(app):
    cupom = regras.buscar_cupom("bemvindo10")
    v = regras.calcular_valores(Decimal("100.00"), cupom, Decimal("5.00"))
    assert v["desconto"] == Decimal("10.00")
    assert v["total"] == Decimal("95.00")


def test_cupom_expirado(app):
    with pytest.raises(RegraNegocioError):
        regras.buscar_cupom("EXPIRADO")
    with pytest.raises(RegraNegocioError):
        regras.buscar_cupom("NAOEXISTE")


def test_estoque_insuficiente_rn01(app):
    c = _cliente_com_itens(("Limão Siciliano", 10))  # estoque 4
    with pytest.raises(RegraNegocioError, match="Estoque insuficiente"):
        regras.criar_pedido(c, c.enderecos[0], FormaPagamento.PIX)


def test_pagamento_aprovado_baixa_estoque(app):
    c = _cliente_com_itens(("Red Velvet", 2))
    produto = Produto.query.filter_by(nome="Red Velvet").one()
    antes = produto.estoque
    pedido = regras.criar_pedido(c, c.enderecos[0], FormaPagamento.PIX)
    assert pedido.status == StatusPedido.AGUARDANDO_PAGAMENTO
    assert pedido.valor_total == Decimal("2") * Decimal("11.90") + Decimal("5.00")
    regras.confirmar_pagamento(pedido, "PIX-TESTE")
    assert pedido.status == StatusPedido.PAGO
    assert produto.estoque == antes - 2
    assert c.carrinho.itens == []
    assert pedido.entrega is not None


def test_tres_recusas_cancelam_rn05(app):
    c = _cliente_com_itens(("Red Velvet", 1))
    pedido = regras.criar_pedido(c, c.enderecos[0], FormaPagamento.CARTAO_CREDITO)
    for _ in range(3):
        regras.registrar_recusa(pedido)
    assert pedido.status == StatusPedido.CANCELADO


def test_cancelamento_por_prazo_rn05(app):
    c = _cliente_com_itens(("Red Velvet", 1))
    pedido = regras.criar_pedido(c, c.enderecos[0], FormaPagamento.PIX)
    assert regras.cancelar_pedidos_expirados(agora=datetime.utcnow() + timedelta(minutes=31)) == 1
    assert pedido.status == StatusPedido.CANCELADO
