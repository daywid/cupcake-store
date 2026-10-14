import re

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


def test_login_apos_adicionar_sem_login_nao_da_405(client, app):
    """Testes com usuários (casos 2 e 4): visitante clica em adicionar, faz login e recebia 405."""
    p = Produto.query.filter_by(nome="Red Velvet").one()
    r = client.post(f"/carrinho/adicionar/{p.id}", headers={"Referer": "http://localhost/?categoria=1"})
    assert r.status_code == 302
    assert "/carrinho/adicionar" not in r.headers["Location"]
    r = client.get(r.headers["Location"])
    assert "Faça login para adicionar ao carrinho".encode() in r.data
    r = login(client, "cliente@cupcake.com", "cliente12345")
    assert r.status_code == 200
    assert "Cupcake de Chocolate".encode() in r.data


def test_login_ignora_next_que_so_aceita_post(client):
    r = client.post("/login?next=/carrinho/adicionar/1",
                    data={"email": "cliente@cupcake.com", "senha": "cliente12345"})
    assert r.headers["Location"] == "/"


def test_login_ignora_next_externo(client):
    r = client.post("/login?next=//exemplo.com",
                    data={"email": "cliente@cupcake.com", "senha": "cliente12345"})
    assert r.headers["Location"] == "/"


ENDERECO_CURITIBA = {"cep": "82520-700", "logradouro": "Rua Teste", "numero": "100",
                     "bairro": "Bacacheri", "cidade": "Curitiba", "uf": "PR"}


def test_cardapio_informa_area_de_entrega(client):
    """Teste com usuário (caso 1): a área atendida aparece antes de montar o carrinho."""
    assert "01000-000 a 09999-999".encode() in client.get("/").data


def test_endereco_fora_da_area_nao_e_salvo(cliente, app):
    """Teste com usuário (caso 1): RN04 já no cadastro do endereço."""
    r = cliente.post("/enderecos/novo", data=ENDERECO_CURITIBA)
    assert r.status_code == 200
    assert "Ainda não entregamos neste CEP".encode() in r.data
    assert len(Usuario.query.filter_by(email="cliente@cupcake.com").one().enderecos) == 1


def test_checkout_seleciona_endereco_atendido(cliente, app):
    """Teste com usuário (caso 1): endereço antigo fora da área não vem marcado."""
    from app.extensions import db
    from app.models import Endereco
    c = Usuario.query.filter_by(email="cliente@cupcake.com").one()
    db.session.add(Endereco(cliente=c, **{**ENDERECO_CURITIBA, "cep": "82520700"}))
    db.session.commit()
    p = Produto.query.filter_by(nome="Banana Fit").one()
    cliente.post(f"/carrinho/adicionar/{p.id}")
    r = cliente.get("/checkout")
    assert "Infelizmente".encode() not in r.data
    marcado = re.search(rb'<input[^>]*checked[^>]*name="endereco_id"[^>]*value="(\d+)"', r.data)
    assert int(marcado.group(1)) == c.enderecos[0].id


def test_adicionar_volta_para_o_produto(cliente):
    """Melhoria de usabilidade: a página volta ao card do produto, não ao topo."""
    p = Produto.query.filter_by(nome="Banana Fit").one()
    r = cliente.post(f"/carrinho/adicionar/{p.id}", headers={"Referer": "http://localhost/?categoria=2"})
    assert r.headers["Location"].endswith(f"/?categoria=2#produto-{p.id}")


def test_carrinho_esvazia_ao_criar_pedido_e_volta_ao_cancelar(cliente, app):
    """Melhoria de usabilidade: o contador do carrinho não mostra itens já pedidos."""
    c = Usuario.query.filter_by(email="cliente@cupcake.com").one()
    p = Produto.query.filter_by(nome="Banana Fit").one()
    cliente.post(f"/carrinho/adicionar/{p.id}", data={"quantidade": 2})
    cliente.post("/checkout", data={"endereco_id": c.enderecos[0].id, "forma": "PIX",
                                    "acao": "confirmar"})
    pedido = Pedido.query.one()
    assert c.carrinho.itens == []
    cliente.post(f"/pedido/{pedido.id}/cancelar")
    assert pedido.status == StatusPedido.CANCELADO
    assert [(i.produto.nome, i.quantidade) for i in c.carrinho.itens] == [("Banana Fit", 2)]


def test_meus_pedidos_sem_botao_novo_endereco(cliente):
    assert "Novo endereço".encode() not in cliente.get("/pedidos").data
