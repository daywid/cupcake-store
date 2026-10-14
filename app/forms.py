from flask_wtf import FlaskForm
from wtforms import (BooleanField, DecimalField, IntegerField, PasswordField, RadioField,
                     SelectField, StringField, TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, InputRequired, Length, NumberRange,
                                Optional, ValidationError)

from .models import FormaPagamento
from .services.validadores import cep_valido, cpf_valido, imagem_url_valida, somente_digitos

OBR = "Campo obrigatório."


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(OBR), Email("E-mail inválido.")])
    senha = PasswordField("Senha", validators=[DataRequired(OBR)])
    lembrar = BooleanField("Manter conectado")


class CadastroForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(OBR), Length(3, 120)])
    email = StringField("E-mail", validators=[DataRequired(OBR), Email("E-mail inválido.")])
    cpf = StringField("CPF", validators=[DataRequired(OBR)])
    telefone = StringField("Telefone", validators=[Optional(), Length(max=20)])
    senha = PasswordField("Senha", validators=[
        DataRequired(OBR), Length(min=8, message="A senha deve ter no mínimo 8 caracteres.")])
    confirmar = PasswordField("Confirmar senha", validators=[
        DataRequired(OBR), EqualTo("senha", "As senhas não conferem.")])
    aceite = BooleanField("Li e aceito os termos de uso e a política de privacidade (LGPD)",
                          validators=[DataRequired("É preciso aceitar os termos.")])

    def validate_cpf(self, field):
        if not cpf_valido(field.data):
            raise ValidationError("CPF inválido.")


class EnderecoForm(FlaskForm):
    cep = StringField("CEP", validators=[DataRequired(OBR)])
    logradouro = StringField("Rua / Avenida", validators=[DataRequired(OBR), Length(max=150)])
    numero = StringField("Número", validators=[DataRequired(OBR), Length(max=10)])
    complemento = StringField("Complemento", validators=[Optional(), Length(max=60)])
    bairro = StringField("Bairro", validators=[DataRequired(OBR), Length(max=80)])
    cidade = StringField("Cidade", validators=[DataRequired(OBR), Length(max=80)])
    uf = StringField("UF", validators=[DataRequired(OBR), Length(2, 2, "Use a sigla (ex.: SP).")])

    def validate_cep(self, field):
        if not cep_valido(field.data):
            raise ValidationError("CEP deve ter 8 dígitos.")
        field.data = somente_digitos(field.data)


class CheckoutForm(FlaskForm):
    endereco_id = RadioField("Endereço de entrega", coerce=int,
                             validators=[DataRequired("Selecione um endereço.")])
    cupom = StringField("Cupom de desconto", validators=[Optional(), Length(max=30)])
    forma = RadioField("Forma de pagamento",
                       choices=[(f.name, f.value) for f in FormaPagamento],
                       default=FormaPagamento.PIX.name,
                       validators=[DataRequired("Escolha a forma de pagamento.")])


class CartaoForm(FlaskForm):
    titular = StringField("Nome impresso no cartão", validators=[DataRequired(OBR)])
    numero = StringField("Número do cartão", validators=[DataRequired(OBR)])
    validade = StringField("Validade (MM/AA)", validators=[DataRequired(OBR)])
    cvv = StringField("CVV", validators=[DataRequired(OBR), Length(3, 4)])


class AvaliacaoForm(FlaskForm):
    nota = SelectField("Nota", coerce=int, choices=[(n, "★" * n) for n in range(5, 0, -1)])
    comentario = TextAreaField("Comentário", validators=[Optional(), Length(max=500)])


class ProdutoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(OBR), Length(max=100)])
    categoria_id = SelectField("Categoria", coerce=int, validators=[DataRequired(OBR)])
    sabor = StringField("Sabor", validators=[Optional(), Length(max=60)])
    descricao = TextAreaField("Descrição", validators=[Optional()])
    # InputRequired (e não DataRequired) para que 0 seja validado pelo NumberRange
    preco = DecimalField("Preço (R$)", places=2, validators=[
        InputRequired(OBR), NumberRange(min=0.01, message="O preço deve ser maior que zero.")])
    estoque = IntegerField("Estoque", validators=[
        InputRequired(OBR), NumberRange(min=0, message="O estoque não pode ser negativo.")])
    imagem_url = StringField("URL da imagem (JPG/PNG)", validators=[Optional(), Length(max=255)])
    ativo = BooleanField("Produto ativo (visível no catálogo)", default=True)

    def validate_imagem_url(self, field):
        if not imagem_url_valida(field.data):
            raise ValidationError("Informe uma URL http(s) terminando em .jpg, .jpeg ou .png.")


class StatusPedidoForm(FlaskForm):
    status = SelectField("Status do pedido")
    entregador_id = SelectField("Entregador", coerce=int)
