from datetime import date, datetime
from decimal import Decimal

from ..extensions import db
from .enums import FormaPagamento, StatusEntrega, StatusPagamento, StatusPedido


class Carrinho(db.Model):
    __tablename__ = "carrinho"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), unique=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", back_populates="carrinho")
    itens = db.relationship("ItemCarrinho", back_populates="carrinho", cascade="all, delete-orphan")

    def adicionar_item(self, produto, qtd=1):
        item = next((i for i in self.itens if i.produto_id == produto.id), None)
        if item:
            item.quantidade += qtd
        else:
            self.itens.append(ItemCarrinho(produto=produto, quantidade=qtd,
                                           preco_unitario=produto.preco))

    def remover_item(self, produto):
        self.itens = [i for i in self.itens if i.produto_id != produto.id]

    def calcular_total(self):
        return sum((i.subtotal() for i in self.itens), Decimal("0"))

    def limpar(self):
        self.itens = []


class ItemCarrinho(db.Model):
    __tablename__ = "item_carrinho"

    id = db.Column(db.Integer, primary_key=True)
    carrinho_id = db.Column(db.Integer, db.ForeignKey("carrinho.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    carrinho = db.relationship("Carrinho", back_populates="itens")
    produto = db.relationship("Produto")

    def subtotal(self):
        return Decimal(self.produto.preco) * self.quantidade


class Cupom(db.Model):
    __tablename__ = "cupom"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False)
    percentual = db.Column(db.Numeric(5, 2), nullable=False)
    validade = db.Column(db.Date, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def validar(self, hoje=None):
        return self.ativo and (hoje or date.today()) <= self.validade


class Pedido(db.Model):
    __tablename__ = "pedido"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    endereco_id = db.Column(db.Integer, db.ForeignKey("endereco.id"), nullable=False)
    cupom_id = db.Column(db.Integer, db.ForeignKey("cupom.id"))
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    desconto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    taxa_entrega = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum(StatusPedido), nullable=False, default=StatusPedido.AGUARDANDO_PAGAMENTO)

    cliente = db.relationship("Cliente", back_populates="pedidos")
    endereco = db.relationship("Endereco")
    cupom = db.relationship("Cupom")
    itens = db.relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    pagamento = db.relationship("Pagamento", back_populates="pedido", uselist=False,
                                cascade="all, delete-orphan")
    entrega = db.relationship("Entrega", back_populates="pedido", uselist=False,
                              cascade="all, delete-orphan")
    avaliacao = db.relationship("Avaliacao", back_populates="pedido", uselist=False,
                                cascade="all, delete-orphan")

    def calcular_total(self):
        return self.subtotal - self.desconto + self.taxa_entrega  # RN03

    def cancelar(self):
        self.status = StatusPedido.CANCELADO


class ItemPedido(db.Model):
    __tablename__ = "item_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    pedido = db.relationship("Pedido", back_populates="itens")
    produto = db.relationship("Produto", back_populates="itens_pedido")

    def subtotal(self):
        return Decimal(self.preco_unitario) * self.quantidade


class Pagamento(db.Model):
    __tablename__ = "pagamento"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), unique=True, nullable=False)
    forma = db.Column(db.Enum(FormaPagamento), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum(StatusPagamento), nullable=False, default=StatusPagamento.PENDENTE)
    codigo_transacao = db.Column(db.String(64))
    tentativas = db.Column(db.Integer, nullable=False, default=0)
    data_pagamento = db.Column(db.DateTime)

    pedido = db.relationship("Pedido", back_populates="pagamento")


class Entrega(db.Model):
    __tablename__ = "entrega"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), unique=True, nullable=False)
    entregador_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    status = db.Column(db.Enum(StatusEntrega), nullable=False, default=StatusEntrega.AGUARDANDO)
    previsao = db.Column(db.DateTime)
    data_entrega = db.Column(db.DateTime)

    pedido = db.relationship("Pedido", back_populates="entrega")
    entregador = db.relationship("Entregador", back_populates="entregas")


class Avaliacao(db.Model):
    __tablename__ = "avaliacao"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedido.id"), unique=True, nullable=False)
    nota = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.String(500))
    data = db.Column(db.DateTime, default=datetime.utcnow)

    pedido = db.relationship("Pedido", back_populates="avaliacao")
