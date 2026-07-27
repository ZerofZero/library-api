# config.py
import os

class Settings:
    api_keys: str = os.environ.get("API_KEYS", "")
    librarian_keys: str = os.environ.get("LIBRARIAN_KEYS", "")
    cors_origins: str = os.environ.get("CORS_ORIGINS", "*")

    @property
    def api_keys_list(self) -> set[str]:
        return set(self.api_keys.split(",")) if self.api_keys else set()

    @property
    def librarian_keys_list(self) -> set[str]:
        return set(self.librarian_keys.split(",")) if self.librarian_keys else set()

    @property
    def cors_origins_list(self) -> list[str]:
        return self.cors_origins.split(",")

settings = Settings()