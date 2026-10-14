"""Gateway de pagamento SIMULADO (ator externo do diagrama de casos de uso).

Não há cobrança real. Regras da simulação, documentadas no README:
- PIX: gera um código copia-e-cola; o botão "Simular pagamento" confirma.
- Cartão: número precisa passar no algoritmo de Luhn; cartões terminados em 0002
  são sempre RECUSADOS (para testar o curso alternativo de pagamento recusado).
Os dados do cartão nunca são gravados (RNF01).
"""
import uuid

from .validadores import luhn_valido, somente_digitos

CARTAO_RECUSADO_FINAL = "0002"


class RespostaGateway:
    def __init__(self, aprovado, codigo=None, motivo=None):
        self.aprovado = aprovado
        self.codigo = codigo
        self.motivo = motivo


def gerar_pix(pedido):
    chave = f"cupcakestore{pedido.id:06d}"
    valor = f"{pedido.valor_total:.2f}"
    return f"00020126580014BR.GOV.BCB.PIX0136{chave}5204000053039865406{valor}5802BR6009SAOPAULO"


def autorizar_pix(_pedido):
    return RespostaGateway(True, codigo="PIX-" + uuid.uuid4().hex[:16].upper())


def autorizar_cartao(numero, validade, cvv):
    numero = somente_digitos(numero)
    if not luhn_valido(numero):
        return RespostaGateway(False, motivo="Número de cartão inválido.")
    if len(somente_digitos(cvv)) not in (3, 4):
        return RespostaGateway(False, motivo="CVV inválido.")
    if not _validade_ok(validade):
        return RespostaGateway(False, motivo="Cartão vencido ou validade inválida.")
    if numero.endswith(CARTAO_RECUSADO_FINAL):
        return RespostaGateway(False, motivo="Pagamento recusado pela operadora.")
    return RespostaGateway(True, codigo="CRD-" + uuid.uuid4().hex[:16].upper())


def _validade_ok(validade):
    from datetime import date
    d = somente_digitos(validade)
    if len(d) != 4:
        return False
    mes, ano = int(d[:2]), 2000 + int(d[2:])
    if not 1 <= mes <= 12:
        return False
    hoje = date.today()
    return (ano, mes) >= (hoje.year, hoje.month)
