import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_url():
    url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'cupcake.db')}")
    # Render entrega "postgres://" ou "postgresql://"; fixamos o driver psycopg2 explicitamente
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg2://" + url[len(prefixo):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-troque-esta-chave")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # Regras de negócio parametrizáveis
    PRAZO_PAGAMENTO_MIN = 30          # RN05 / RN06
    MAX_TENTATIVAS_PAGAMENTO = 3      # RN05
    TAXA_ENTREGA_BASE = 5.00          # RN02 – região próxima
    TAXA_ENTREGA_ESTENDIDA = 9.90     # RN02 – região estendida
    CEP_FAIXA_PROXIMA = ("01000000", "05999999")   # RN02
    CEP_AREA_ATENDIDA = ("01000000", "09999999")   # RN04


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "teste"
