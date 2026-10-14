"""Validações das regras RN07 (produto) e RN09 (cadastro)."""
import re


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf):
    """RN09 – valida os dígitos verificadores do CPF."""
    cpf = somente_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def cep_valido(cep):
    return len(somente_digitos(cep)) == 8


def imagem_url_valida(url):
    """RN07 – imagem do produto deve ser JPG ou PNG (opcional)."""
    if not url:
        return True
    return bool(re.match(r"^https?://\S+\.(jpe?g|png)(\?\S*)?$", url, re.IGNORECASE))


def luhn_valido(numero):
    """Validação do número do cartão (algoritmo de Luhn)."""
    numero = somente_digitos(numero)
    if not 13 <= len(numero) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(numero)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
