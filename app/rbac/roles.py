from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERADOR = "moderador"
    PARTICIPANTE = "participante"


# Ordem de hierarquia: super_admin > admin > moderador > participante
ROLE_HIERARCHY: dict[Role, int] = {
    Role.SUPER_ADMIN: 3,
    Role.ADMIN: 2,
    Role.MODERADOR: 1,
    Role.PARTICIPANTE: 0,
}

DEFAULT_ROLE = Role.PARTICIPANTE


def role_at_least(role: Role, minimum: Role) -> bool:
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minimum]
