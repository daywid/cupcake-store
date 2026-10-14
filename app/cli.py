"""Comandos de linha de comando: `flask --app wsgi init-db` e `flask --app wsgi seed`."""
from datetime import date, timedelta
from decimal import Decimal

import click

from .extensions import db
from .models import Administrador, Carrinho, Categoria, Cliente, Cupom, Endereco, Entregador, Produto

CATEGORIAS = {
    "Clássicos": "Os sabores que todo mundo ama.",
    "Gourmet": "Receitas especiais com ingredientes selecionados.",
    "Fit & Veganos": "Sem lactose, sem açúcar refinado ou 100% vegetais.",
    "Datas Especiais": "Edições limitadas para presentear.",
}

PRODUTOS = [
    # nome, categoria, sabor, preço, estoque, descrição
    ("Cupcake de Chocolate", "Clássicos", "Chocolate", "9.90", 40,
     "Massa fofinha de cacau com cobertura de ganache meio amargo."),
    ("Cupcake de Baunilha", "Clássicos", "Baunilha", "8.90", 40,
     "Massa de baunilha com buttercream suave e confeitos coloridos."),
    ("Red Velvet", "Clássicos", "Red velvet", "11.90", 30,
     "Massa aveludada vermelha com frosting de cream cheese."),
    ("Cenoura com Brigadeiro", "Clássicos", "Cenoura", "9.90", 30,
     "O clássico bolo de cenoura em versão cupcake, com brigadeiro cremoso."),
    ("Pistache Siciliano", "Gourmet", "Pistache", "14.90", 20,
     "Massa amanteigada com creme de pistache e pistache triturado."),
    ("Nutella com Morango", "Gourmet", "Avelã e morango", "13.90", 25,
     "Recheio de creme de avelã, cobertura de chantilly e morango fresco."),
    ("Doce de Leite com Flor de Sal", "Gourmet", "Doce de leite", "12.90", 25,
     "Recheio de doce de leite argentino e toque de flor de sal."),
    ("Limão Siciliano", "Gourmet", "Limão", "11.90", 4,
     "Massa cítrica com curd de limão e merengue maçaricado."),
    ("Banana Fit", "Fit & Veganos", "Banana e canela", "10.90", 20,
     "Sem açúcar refinado, adoçado com tâmaras. Sem lactose."),
    ("Chocolate Vegano", "Fit & Veganos", "Cacau 70%", "12.90", 15,
     "100% vegetal: massa de cacau e cobertura de ganache de coco."),
    ("Coração de Morango", "Datas Especiais", "Morango", "13.90", 10,
     "Edição Dia dos Namorados com cobertura rosa e coração de chocolate."),
    ("Caixa Surpresa (6 un.)", "Datas Especiais", "Sortidos", "59.90", 8,
     "Seis cupcakes sortidos escolhidos pela confeiteira, em caixa presente."),
]


def popular():
    cats = {}
    for nome, desc in CATEGORIAS.items():
        cats[nome] = Categoria(nome=nome, descricao=desc)
        db.session.add(cats[nome])
    for nome, cat, sabor, preco, estoque, desc in PRODUTOS:
        db.session.add(Produto(nome=nome, categoria=cats[cat], sabor=sabor, preco=Decimal(preco),
                               estoque=estoque, descricao=desc))

    admin = Administrador(nome="Administrador da Loja", email="admin@cupcake.com", nivel_acesso=1)
    admin.definir_senha("admin12345")
    entregador = Entregador(nome="Carlos Entregador", email="entregador@cupcake.com",
                            cnh="12345678900", veiculo="Moto Honda CG 160")
    entregador.definir_senha("entrega12345")
    cliente = Cliente(nome="Cliente Teste", email="cliente@cupcake.com", cpf="52998224725",
                      telefone="(11) 99999-0000", carrinho=Carrinho())
    cliente.definir_senha("cliente12345")
    cliente.enderecos.append(Endereco(logradouro="Avenida Paulista", numero="1000",
                                      bairro="Bela Vista", cidade="São Paulo", uf="SP",
                                      cep="01310100"))
    db.session.add_all([admin, entregador, cliente])
    db.session.add_all([
        Cupom(codigo="BEMVINDO10", percentual=Decimal("10"), validade=date.today() + timedelta(days=365)),
        Cupom(codigo="DOCE20", percentual=Decimal("20"), validade=date.today() + timedelta(days=365)),
        Cupom(codigo="EXPIRADO", percentual=Decimal("50"), validade=date.today() - timedelta(days=1)),
    ])
    db.session.commit()


def register_cli(app):
    @app.cli.command("init-db")
    @click.option("--reset", is_flag=True, help="Apaga todas as tabelas antes de criar.")
    def init_db(reset):
        """Cria as tabelas do banco a partir dos models."""
        if reset:
            db.drop_all()
        db.create_all()
        click.echo("Tabelas criadas.")

    @app.cli.command("seed")
    @click.option("--se-vazio", is_flag=True, help="Só popula se o banco estiver vazio.")
    def seed(se_vazio):
        """Cria as tabelas e insere dados de demonstração."""
        db.create_all()
        if Categoria.query.first():
            if se_vazio:
                click.echo("Banco já populado – nada a fazer.")
                return
            raise click.ClickException("O banco já tem dados. Use `init-db --reset` antes.")
        popular()
        click.echo("Dados de demonstração inseridos.")
