class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(code)


def missing():
    return AppError(404, "not_found", "Объект не найден")


def unauthorized():
    return AppError(401, "unauthorized", "Требуется вход")

