from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager


class Usuario(UserMixin, db.Model):
    """Classe abstrata do diagrama. Herança mapeada em tabela única (coluna 'tipo')."""
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(20))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Cliente
    cpf = db.Column(db.String(11), unique=True)
    data_nascimento = db.Column(db.Date)
    # Administrador
    nivel_acesso = db.Column(db.Integer)
    # Entregador
    cnh = db.Column(db.String(20))
    veiculo = db.Column(db.String(60))

    __mapper_args__ = {"polymorphic_on": tipo, "polymorphic_identity": "usuario"}

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)  # RNF01 – senha com hash

    def autenticar(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.tipo == "administrador"


class Cliente(Usuario):
    __mapper_args__ = {"polymorphic_identity": "cliente"}

    enderecos = db.relationship("Endereco", back_populates="cliente", cascade="all, delete-orphan")
    carrinho = db.relationship("Carrinho", back_populates="cliente", uselist=False,
                               cascade="all, delete-orphan")
    pedidos = db.relationship("Pedido", back_populates="cliente", order_by="Pedido.data_pedido.desc()")


class Administrador(Usuario):
    __mapper_args__ = {"polymorphic_identity": "administrador"}


class Entregador(Usuario):
    __mapper_args__ = {"polymorphic_identity": "entregador"}

    entregas = db.relationship("Entrega", back_populates="entregador")


@login_manager.user_loader
def carregar_usuario(user_id):
    return db.session.get(Usuario, int(user_id))
