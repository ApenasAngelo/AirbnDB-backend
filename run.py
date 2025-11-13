"""Script para iniciar o servidor de desenvolvimento."""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    print("🚀 Iniciando servidor FastAPI...")
    print(f"📍 Host: {settings.API_HOST}")
    print(f"🔌 Porta: {settings.API_PORT}")
    print(f"📚 Documentação: http://localhost:{settings.API_PORT}/docs")
    print(f"🔄 Reload: {settings.API_RELOAD}")
    print()

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
