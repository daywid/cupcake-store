from ..extensions import db


class Categoria(db.Model):
    __tablename__ = "categoria"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60), unique=True, nullable=False)
    descricao = db.Column(db.String(255))

    produtos = db.relationship("Produto", back_populates="categoria")


class Produto(db.Model):
    __tablename__ = "produto"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categoria.id"), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    sabor = db.Column(db.String(60))
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    estoque = db.Column(db.Integer, nullable=False, default=0)
    imagem_url = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, nullable=False, default=True)  # RN08 – exclusão lógica

    categoria = db.relationship("Categoria", back_populates="produtos")
    itens_pedido = db.relationship("ItemPedido", back_populates="produto")

    def baixar_estoque(self, qtd):
        if qtd > self.estoque:
            raise ValueError(f"Estoque insuficiente para {self.nome}")
        self.estoque -= qtd
