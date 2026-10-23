class RegistryError(Exception):
    def __init__(self, status: int, code: str, retry_after: int | None = None):
        self.status, self.code, self.retry_after = status, code, retry_after
        super().__init__(code)
