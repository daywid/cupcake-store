import enum


class StatusPedido(enum.Enum):
    AGUARDANDO_PAGAMENTO = "Aguardando pagamento"
    PAGO = "Pago"
    EM_PREPARO = "Em preparo"
    SAIU_PARA_ENTREGA = "Saiu para entrega"
    ENTREGUE = "Entregue"
    CANCELADO = "Cancelado"


class FormaPagamento(enum.Enum):
    PIX = "PIX"
    CARTAO_CREDITO = "Cartão de crédito"
    CARTAO_DEBITO = "Cartão de débito"


class StatusPagamento(enum.Enum):
    PENDENTE = "Pendente"
    APROVADO = "Aprovado"
    RECUSADO = "Recusado"


class StatusEntrega(enum.Enum):
    AGUARDANDO = "Aguardando"
    EM_ROTA = "Em rota"
    ENTREGUE = "Entregue"
