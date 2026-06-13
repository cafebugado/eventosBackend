from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERADOR = "moderador"


# Ordem de hierarquia: super_admin > admin > moderador
ROLE_HIERARCHY: dict[Role, int] = {
    Role.SUPER_ADMIN: 3,
    Role.ADMIN: 2,
    Role.MODERADOR: 1,
}

DEFAULT_ROLE = Role.MODERADOR


def role_at_least(role: Role, minimum: Role) -> bool:
    return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minimum]
