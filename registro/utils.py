import re

# Função de validação de CPF
def validar_cpf(cpf):
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)  # Outra forma de remover não numéricos

    # Verifica se o CPF tem 11 dígitos
    if len(cpf) != 11:
            return False

    # Verifica se todos os dígitos são iguais (caso especial)
    if cpf == cpf[0] * 11:
        return False

    # Cálculo do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 0 if soma % 11 < 2 else 11 - (soma % 11)

    # Cálculo do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 0 if soma % 11 < 2 else 11 - (soma % 11)

    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2