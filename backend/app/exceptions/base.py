class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Not found"):
        super().__init__(404, detail)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(400, detail)
