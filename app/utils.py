import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app
from flask_login import current_user


def brl(valor):
    """Formata número como moeda brasileira: 1234.5 -> R$ 1.234,50"""
    s = f"{float(valor or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


FUSO = ZoneInfo("America/Sao_Paulo")


def hora_local(dt, fmt="%d/%m/%Y %H:%M"):
    """Datas são gravadas em UTC; exibimos no horário de Brasília."""
    if not dt:
        return ""
    return dt.replace(tzinfo=timezone.utc).astimezone(FUSO).strftime(fmt)


def inicio_do_dia_utc():
    """Meia-noite de hoje (Brasília) convertida para UTC sem fuso, para filtrar no banco."""
    agora = datetime.now(FUSO)
    meia_noite = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    return meia_noite.astimezone(timezone.utc).replace(tzinfo=None)


def formatar_cep(cep):
    d = "".join(c for c in str(cep or "") if c.isdigit())
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else cep


def area_atendida():
    """RN04 em texto para o cliente: Grande São Paulo (CEP 01000-000 a 09999-999)."""
    ini, fim = current_app.config["CEP_AREA_ATENDIDA"]
    return f"Grande São Paulo (CEP {formatar_cep(ini)} a {formatar_cep(fim)})"


PALETA = ["#f48fb1", "#ce93d8", "#90caf9", "#a5d6a7", "#ffe082", "#ffab91", "#bcaaa4", "#80cbc4"]


def cor_produto(nome):
    """Cor estável para a ilustração do cupcake quando o produto não tem imagem."""
    h = int(hashlib.md5((nome or "").encode()).hexdigest(), 16)
    return PALETA[h % len(PALETA)]


def register_template_helpers(app):
    app.jinja_env.filters["brl"] = brl
    app.jinja_env.filters["local"] = hora_local
    app.jinja_env.globals["cor_produto"] = cor_produto
    app.jinja_env.globals["area_atendida"] = area_atendida

    @app.context_processor
    def carrinho_badge():
        qtd = 0
        if current_user.is_authenticated and getattr(current_user, "carrinho", None):
            qtd = sum(i.quantidade for i in current_user.carrinho.itens)
        return {"qtd_carrinho": qtd}
