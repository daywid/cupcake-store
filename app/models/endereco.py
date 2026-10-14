from ..extensions import db


class Endereco(db.Model):
    __tablename__ = "endereco"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    logradouro = db.Column(db.String(150), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(60))
    bairro = db.Column(db.String(80), nullable=False)
    cidade = db.Column(db.String(80), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(8), nullable=False)

    cliente = db.relationship("Cliente", back_populates="enderecos")

    def __str__(self):
        comp = f" – {self.complemento}" if self.complemento else ""
        return (f"{self.logradouro}, {self.numero}{comp} – {self.bairro}, "
                f"{self.cidade}/{self.uf} – CEP {self.cep[:5]}-{self.cep[5:]}")
