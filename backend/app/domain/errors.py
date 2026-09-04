class DomainError(Exception):
    def __init__(self, code: str, title: str, detail: str, status: int = 409) -> None:
        super().__init__(detail)
        self.code = code
        self.title = title
        self.detail = detail
        self.status = status


class ConflictError(DomainError):
    def __init__(self, code: str, title: str, detail: str) -> None:
        super().__init__(code, title, detail, status=409)


class NotFoundError(DomainError):
    def __init__(self, title: str, detail: str) -> None:
        super().__init__("not-found", title, detail, status=404)


class ForbiddenError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__("forbidden", "Forbidden", detail, status=403)
