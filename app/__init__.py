from flask import Flask, render_template

from config import Config
from .extensions import csrf, db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registra as tabelas)
    from .controllers.admin import bp as admin_bp
    from .controllers.auth import bp as auth_bp
    from .controllers.carrinho import bp as carrinho_bp
    from .controllers.catalogo import bp as catalogo_bp
    from .controllers.pedido import bp as pedido_bp

    for bp in (catalogo_bp, auth_bp, carrinho_bp, pedido_bp, admin_bp):
        app.register_blueprint(bp)

    from .cli import register_cli
    register_cli(app)

    from .utils import register_template_helpers
    register_template_helpers(app)

    @app.errorhandler(404)
    def nao_encontrado(_):
        return render_template("erro.html", codigo=404, mensagem="Página não encontrada."), 404

    @app.errorhandler(403)
    def proibido(_):
        return render_template("erro.html", codigo=403, mensagem="Acesso restrito ao administrador."), 403

    return app
