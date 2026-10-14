from app.models import Pedido, Produto, StatusPedido, Usuario

from .conftest import login


def test_catalogo_publico(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Cupcake de Chocolate".encode() in r.data


def test_produto_inativo_some_do_catalogo(admin, app):
    p = Produto.query.filter_by(nome="Red Velvet").one()
    admin.post(f"/admin/produtos/{p.id}/alternar")
    assert not p.ativo
    admin.get("/")  # consome a mensagem flash "Red Velvet desativado."
    assert f'href="/produto/{p.id}"'.encode() not in admin.get("/").data
    assert admin.get(f"/produto/{p.id}").status_code == 404


def test_cadastro_uc01(client, app):
    dados = {"nome": "Maria Silva", "email": "maria@teste.com", "cpf": "390.533.447-05",
             "telefone": "", "senha": "segredo123", "confirmar": "segredo123", "aceite": "y"}
    r = client.post("/cadastro", data=dados, follow_redirects=True)
    assert "Bem-vindo(a), Maria".encode() in r.data
    u = Usuario.query.filter_by(email="maria@teste.com").one()
    assert u.senha_hash != "segredo123"  # RNF01


def test_cadastro_cpf_invalido(client):
    dados = {"nome": "Ana", "email": "ana@teste.com", "cpf": "111.111.111-11",
             "senha": "segredo123", "confirmar": "segredo123", "aceite": "y"}
    r = client.post("/cadastro", data=dados)
    assert "CPF inválido".encode() in r.data


def test_login_invalido(client):
    r = login(client, "cliente@cupcake.com", "errada")
    assert "E-mail ou senha incorretos".encode() in r.data


def test_cliente_nao_acessa_admin(cliente):
    assert cliente.get("/admin/").status_code == 403


def test_fluxo_completo_cartao(cliente, app):
    """UC04 → UC05 → UC06 (recusa e aprovação) → UC10 → UC08."""
    p = Produto.query.filter_by(nome="Cupcake de Chocolate").one()
    cliente.post(f"/carrinho/adicionar/{p.id}", data={"quantidade": 3})
    end_id = Usuario.query.filter_by(email="cliente@cupcake.com").one().enderecos[0].id

    r = cliente.post("/checkout", data={"endereco_id": end_id, "cupom": "DOCE20",
                                        "forma": "CARTAO_CREDITO", "acao": "confirmar"})
    assert r.status_code == 302
    pedido = Pedido.query.one()
    assert pedido.desconto > 0

    cartao = {"titular": "CLIENTE TESTE", "validade": "12/39", "cvv": "123"}
    r = cliente.post(f"/pedido/{pedido.id}/pagamento",
                     data={**cartao, "numero": "4000 0000 0000 0002"}, follow_redirects=True)
    assert "recusado".encode() in r.data
    assert pedido.status == StatusPedido.AGUARDANDO_PAGAMENTO

    r = cliente.post(f"/pedido/{pedido.id}/pagamento",
                     data={**cartao, "numero": "4111 1111 1111 1111"}, follow_redirects=True)
    assert "Pagamento aprovado".encode() in r.data
    assert pedido.status == StatusPedido.PAGO

    # avaliação só depois de entregue
    cliente.post(f"/pedido/{pedido.id}/avaliar", data={"nota": 5})
    assert pedido.avaliacao is None

    cliente.post("/logout")
    login(cliente, "admin@cupcake.com", "admin12345")
    cliente.post(f"/admin/pedidos/{pedido.id}", data={"status": "ENTREGUE", "entregador_id": 0})
    assert pedido.status == StatusPedido.ENTREGUE

    cliente.post("/logout")
    login(cliente, "cliente@cupcake.com", "cliente12345")
    cliente.post(f"/pedido/{pedido.id}/avaliar", data={"nota": 5, "comentario": "Ótimo!"})
    assert pedido.avaliacao.nota == 5


def test_relatorio(admin):
    assert admin.get("/admin/relatorio").status_code == 200
