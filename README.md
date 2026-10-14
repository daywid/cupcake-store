# 🧁 Cupcake Store

Loja virtual de cupcakes com vitrine, carrinho, pedido, pagamento e acompanhamento de entrega.
Projeto do **Projeto Integrador Transdisciplinar em Sistemas de Informação II** (Cruzeiro do Sul Virtual),
desenvolvido a partir da modelagem UML feita no PIT I.

- **Aplicação online:** _(link do Render após o deploy)_
- **Manual de uso:** [docs/manual_de_uso.md](docs/manual_de_uso.md)
- **Banco de dados:** [database/schema_mysql.sql](database/schema_mysql.sql) · [modelo conceitual](docs/diagramas/modelo_conceitual.png) · [modelo lógico](docs/diagramas/modelo_logico.png)

![Catálogo](docs/prints/01_catalogo.png)

## Usuários de teste

| Perfil | E-mail | Senha |
|---|---|---|
| Cliente | `cliente@cupcake.com` | `cliente12345` |
| Administrador | `admin@cupcake.com` | `admin12345` |

Cupons: `BEMVINDO10` (10%), `DOCE20` (20%), `EXPIRADO` (para testar cupom inválido).

Os pagamentos são **simulados**, sem nenhuma cobrança real:

| Forma | Como testar |
|---|---|
| PIX | botão "Simular pagamento PIX" |
| Cartão aprovado | `4111 1111 1111 1111`, validade futura, CVV `123` |
| Cartão recusado | `4000 0000 0000 0002` (3 recusas cancelam o pedido) |

## Funcionalidades (casos de uso do PIT I)

| Caso de uso | Onde |
|---|---|
| UC01 Cadastrar-se / UC02 Fazer Login | `/cadastro`, `/login` |
| UC03 Consultar Catálogo (busca e filtro por categoria) | `/` |
| UC04 Gerenciar Carrinho | `/carrinho/` |
| UC05 Realizar Pedido (endereço, cupom, taxa de entrega) | `/checkout` |
| UC06 Efetuar Pagamento (PIX ou cartão) | `/pedido/<id>/pagamento` |
| UC07 Acompanhar Pedido / UC08 Avaliar | `/pedidos`, `/pedido/<id>` |
| UC09 Gerenciar Produtos (exclusão lógica) | `/admin/produtos` |
| UC10 Gerenciar Pedidos / UC11 Status da entrega | `/admin/pedidos` |
| UC12 Relatório de Vendas | `/admin/relatorio` |

Regras de negócio implementadas em [`app/services/regras.py`](app/services/regras.py):
RN01 estoque · RN02 taxa de entrega por faixa de CEP · RN03 cálculo do total · RN04 área de entrega
(CEP 01000-000 a 09999-999) · RN05 cancelamento após 30 min ou 3 recusas · RN07 validação de produto ·
RN08 exclusão lógica · RN09 validação de cadastro (CPF) · RNF01 senha com hash e dados de cartão não armazenados.

## Arquitetura (MVC)

```
app/
├── models/        MODEL       – classes do diagrama de classes (SQLAlchemy)
├── templates/     VIEW        – telas em HTML (Jinja2 + Bootstrap 5)
├── static/                    – CSS e JavaScript (máscaras, ViaCEP, copiar PIX)
├── controllers/   CONTROLLER  – rotas (Flask Blueprints) por caso de uso
├── services/                  – regras de negócio e gateway de pagamento simulado
└── forms.py                   – validação dos formulários (Flask-WTF, com CSRF)
```

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3 + HTML, CSS, JavaScript |
| Framework | Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-WTF |
| Banco | MySQL (projeto físico) · PostgreSQL em produção · SQLite em desenvolvimento |
| Hospedagem | Render (plano gratuito) |
| Testes | pytest |

## Como rodar localmente

```bash
git clone https://github.com/daywid/cupcake-store.git
cd cupcake-store
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi seed          # cria o banco SQLite com dados de demonstração
flask --app wsgi run           # http://localhost:5000
```

Testes automatizados:

```bash
pytest -q
```

Para usar MySQL: `pip install pymysql`, crie o banco com `database/schema_mysql.sql` e defina
`DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/cupcake_store` no arquivo `.env`.

## Deploy no Render

O arquivo [`render.yaml`](render.yaml) cria o serviço web e o PostgreSQL gratuito.
No Render: **New → Blueprint →** selecione este repositório → **Apply**. Na primeira subida
o comando `flask seed --se-vazio` cria as tabelas e os dados de demonstração.

## Licença

MIT – veja [LICENSE](LICENSE).
