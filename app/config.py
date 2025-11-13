"""Configurações da aplicação usando variáveis de ambiente."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do arquivo .env"""

    # Banco de Dados
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "airbnb"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Converte a string CORS_ORIGINS em uma lista."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instância global de configurações
settings = Settings()
