"""Regras de negócio do PIT I (RN01–RN05, RN08) usadas pelos controllers."""
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from flask import current_app

from ..extensions import db
from ..models import (Cupom, Entrega, ItemPedido, Pagamento, Pedido, StatusPagamento,
                      StatusPedido)
from .validadores import somente_digitos


class RegraNegocioError(Exception):
    """Erro de regra de negócio com mensagem pronta para o usuário."""


def _dinheiro(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validar_estoque(itens):
    """RN01 – retorna a lista de itens sem estoque suficiente (ou inativos)."""
    return [i for i in itens if not i.produto.ativo or i.quantidade > i.produto.estoque]


def cep_atendido(cep):
    """RN04 – entregamos apenas dentro da faixa de CEP atendida."""
    ini, fim = current_app.config["CEP_AREA_ATENDIDA"]
    return ini <= somente_digitos(cep) <= fim


def calcular_taxa_entrega(cep):
    """RN02 – taxa fixa na região próxima, taxa estendida no restante da área atendida."""
    if not cep_atendido(cep):
        raise RegraNegocioError("Infelizmente ainda não entregamos neste CEP.")
    ini, fim = current_app.config["CEP_FAIXA_PROXIMA"]
    cfg = "TAXA_ENTREGA_BASE" if ini <= somente_digitos(cep) <= fim else "TAXA_ENTREGA_ESTENDIDA"
    return _dinheiro(current_app.config[cfg])


def buscar_cupom(codigo):
    """Retorna o cupom válido ou levanta RegraNegocioError (curso alternativo Gama do UC05)."""
    if not codigo:
        return None
    cupom = Cupom.query.filter(db.func.upper(Cupom.codigo) == codigo.strip().upper()).first()
    if not cupom or not cupom.validar():
        raise RegraNegocioError("Cupom inválido ou expirado.")
    return cupom


def calcular_valores(subtotal, cupom, taxa):
    """RN03 – total = subtotal − desconto + taxa de entrega."""
    subtotal = _dinheiro(subtotal)
    desconto = _dinheiro(subtotal * Decimal(cupom.percentual) / 100) if cupom else Decimal("0.00")
    total = subtotal - desconto + _dinheiro(taxa)
    return {"subtotal": subtotal, "desconto": desconto, "taxa": _dinheiro(taxa), "total": total}


def criar_pedido(cliente, endereco, forma, cupom=None):
    """UC05 passos 2–9: valida estoque, calcula valores e registra o pedido AGUARDANDO_PAGAMENTO."""
    itens = cliente.carrinho.itens if cliente.carrinho else []
    if not itens:
        raise RegraNegocioError("Seu carrinho está vazio.")
    faltando = validar_estoque(itens)
    if faltando:
        nomes = ", ".join(i.produto.nome for i in faltando)
        raise RegraNegocioError(f"Estoque insuficiente para: {nomes}. Ajuste o carrinho.")

    taxa = calcular_taxa_entrega(endereco.cep)
    v = calcular_valores(cliente.carrinho.calcular_total(), cupom, taxa)

    pedido = Pedido(cliente=cliente, endereco=endereco, cupom=cupom, subtotal=v["subtotal"],
                    desconto=v["desconto"], taxa_entrega=v["taxa"], valor_total=v["total"],
                    status=StatusPedido.AGUARDANDO_PAGAMENTO)
    for i in itens:
        pedido.itens.append(ItemPedido(produto=i.produto, quantidade=i.quantidade,
                                       preco_unitario=i.produto.preco))
    pedido.pagamento = Pagamento(forma=forma, valor=v["total"], status=StatusPagamento.PENDENTE)
    db.session.add(pedido)
    db.session.commit()
    return pedido


def confirmar_pagamento(pedido, codigo_transacao):
    """UC05 passo 11: pagamento aprovado → baixa estoque, limpa carrinho, cria entrega."""
    for item in pedido.itens:
        item.produto.baixar_estoque(item.quantidade)
    pag = pedido.pagamento
    pag.status = StatusPagamento.APROVADO
    pag.codigo_transacao = codigo_transacao
    pag.data_pagamento = datetime.utcnow()
    pedido.status = StatusPedido.PAGO
    pedido.entrega = Entrega(previsao=datetime.utcnow() + timedelta(minutes=90))
    if pedido.cliente.carrinho:
        pedido.cliente.carrinho.limpar()
    db.session.commit()


def registrar_recusa(pedido):
    """Curso alternativo Delta do UC05 / RN05: após N recusas o pedido é cancelado."""
    pag = pedido.pagamento
    pag.status = StatusPagamento.RECUSADO
    pag.tentativas += 1
    if pag.tentativas >= current_app.config["MAX_TENTATIVAS_PAGAMENTO"]:
        pedido.cancelar()
    db.session.commit()


def prazo_pagamento_expirado(pedido, agora=None):
    limite = pedido.data_pedido + timedelta(minutes=current_app.config["PRAZO_PAGAMENTO_MIN"])
    return (agora or datetime.utcnow()) > limite


def cancelar_pedidos_expirados(agora=None):
    """RN05 – cancela pedidos não pagos após o prazo. Chamado ao listar pedidos."""
    pendentes = Pedido.query.filter_by(status=StatusPedido.AGUARDANDO_PAGAMENTO).all()
    cancelados = 0
    for p in pendentes:
        if prazo_pagamento_expirado(p, agora):
            p.cancelar()
            cancelados += 1
    if cancelados:
        db.session.commit()
    return cancelados
