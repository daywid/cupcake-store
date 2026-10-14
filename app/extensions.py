from urllib.parse import urlsplit

from flask import flash, redirect, request, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para continuar."
login_manager.login_message_category = "warning"


@login_manager.unauthorized_handler
def _pedir_login():
    """Manda o visitante ao login e, depois dele, de volta a uma página que se abre com GET.

    Uma ação POST (ex.: adicionar ao carrinho) não pode ser o destino do redirect pós-login:
    o navegador repetiria a URL com GET e a rota responderia 405 (testes com usuários, casos 2 e 4).
    """
    if request.method == "GET":
        destino = request.full_path.rstrip("?")
        flash(login_manager.login_message, login_manager.login_message_category)
    else:
        origem = urlsplit(request.referrer or "")
        mesmo_site = origem.netloc in ("", request.host)
        destino = (origem.path + (f"?{origem.query}" if origem.query else "")) if mesmo_site and origem.path else "/"
        if request.endpoint == "carrinho.adicionar":
            flash("Faça login para adicionar ao carrinho.", "warning")
        else:
            flash(login_manager.login_message, login_manager.login_message_category)
    return redirect(url_for(login_manager.login_view, next=destino))
