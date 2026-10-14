from app.services.validadores import cpf_valido, imagem_url_valida, luhn_valido


def test_cpf_valido():
    assert cpf_valido("529.982.247-25")
    assert not cpf_valido("529.982.247-24")
    assert not cpf_valido("111.111.111-11")
    assert not cpf_valido("123")


def test_luhn():
    assert luhn_valido("4111 1111 1111 1111")
    assert luhn_valido("4000 0000 0000 0002")
    assert not luhn_valido("4111 1111 1111 1112")


def test_imagem_url_rn07():
    assert imagem_url_valida("")
    assert imagem_url_valida("https://exemplo.com/foto.JPG")
    assert not imagem_url_valida("https://exemplo.com/foto.gif")
    assert not imagem_url_valida("ftp://exemplo.com/foto.png")


def test_produto_preco_zero_e_estoque_zero(app):
    from app.forms import ProdutoForm
    with app.test_request_context(method="POST", data={"nome": "X", "categoria_id": 1,
                                                       "preco": "0", "estoque": "0"}):
        form = ProdutoForm()
        form.categoria_id.choices = [(1, "C")]
        assert not form.validate()
        assert form.preco.errors == ["O preço deve ser maior que zero."]
        assert not form.estoque.errors  # estoque 0 é válido (produto esgotado)
