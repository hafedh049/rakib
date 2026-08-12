"""One AppError hierarchy, mapped to RFC 7807 `application/problem+json`."""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 400
    error_type: str = "about:blank"
    title: str = "Erreur"

    def __init__(self, detail: str | None = None, **extra: object) -> None:
        self.detail = detail or self.title
        self.extra = extra
        super().__init__(self.detail)

    def to_problem(self, instance: str | None = None) -> dict[str, object]:
        problem: dict[str, object] = {
            "type": self.error_type,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
        }
        if instance:
            problem["instance"] = instance
        problem.update(self.extra)
        return problem


class ValidationError(AppError):
    status_code = 422
    error_type = "/errors/validation"
    title = "Donnees invalides"


class AuthenticationError(AppError):
    status_code = 401
    error_type = "/errors/authentication"
    title = "Authentification requise"


class InvalidCredentials(AuthenticationError):
    error_type = "/errors/invalid-credentials"
    title = "Identifiants invalides"


class TokenError(AuthenticationError):
    error_type = "/errors/token"
    title = "Jeton invalide ou expire"


class PermissionDenied(AppError):
    status_code = 403
    error_type = "/errors/forbidden"
    title = "Acces refuse"


class NotFound(AppError):
    status_code = 404
    error_type = "/errors/not-found"
    title = "Ressource introuvable"


class Conflict(AppError):
    status_code = 409
    error_type = "/errors/conflict"
    title = "Conflit"


class RateLimited(AppError):
    status_code = 429
    error_type = "/errors/rate-limited"
    title = "Trop de requetes"


class ServiceUnavailable(AppError):
    status_code = 503
    error_type = "/errors/unavailable"
    title = "Service indisponible"


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_problem(instance=str(request.url.path)),
        media_type="application/problem+json",
    )
