from datetime import date


def validar_idade_minima(data_nascimento: date | None, minima: int = 18) -> date | None:
    if data_nascimento is None:
        return data_nascimento

    hoje = date.today()
    idade = hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )
    if idade < minima:
        raise ValueError(f"É necessário ter no mínimo {minima} anos")
    return data_nascimento
