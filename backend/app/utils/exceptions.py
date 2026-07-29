from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error: str,
        detail: str | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error = error


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource", detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error=f"{resource} not found",
            detail=detail,
        )


class UnauthorizedException(AppException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="Unauthorized",
            detail=detail,
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error="Forbidden",
            detail=detail,
        )


class ConflictException(AppException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error="Conflict",
            detail=detail,
        )


class ValidationException(AppException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="Validation Error",
            detail=detail,
        )


class RateLimitException(AppException):
    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="Rate limit exceeded",
            detail=detail,
        )
