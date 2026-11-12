class AppError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message
        super().__init__(code)


def missing() -> AppError:
    return AppError(404, "not_found", "Объект не найден")


def unauthorized() -> AppError:
    return AppError(401, "unauthorized", "Требуется вход")

