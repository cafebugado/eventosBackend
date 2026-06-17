import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception for application-level errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso nao encontrado"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflito de dados"):
        super().__init__(message, status.HTTP_409_CONFLICT)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Nao autorizado"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Dados invalidos"):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno do servidor. Tente novamente."},
        )
