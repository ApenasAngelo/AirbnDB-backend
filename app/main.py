"""Aplicação principal FastAPI para o backend AirbnbRJ."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database.connection import init_connection_pool, close_connection_pool
from app.routers import listings, stats, heatmap


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicializa o pool de conexões na startup e fecha no shutdown.
    """
    # Startup
    print("🚀 Iniciando aplicação...")
    try:
        init_connection_pool()
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao inicializar pool de conexões: {e}")
        print("⚠️ A API iniciará, mas endpoints de banco de dados não funcionarão.")
    yield
    # Shutdown
    print("🛑 Encerrando aplicação...")
    close_connection_pool()


# Criar instância da aplicação FastAPI
app = FastAPI(
    title="AirbnbRJ API",
    description="API Backend para o projeto AirbnbRJ - Trabalho de Banco de Dados",
    version="1.0.0",
    lifespan=lifespan,
)


# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registrar routers
app.include_router(listings.router)
app.include_router(stats.router)
app.include_router(heatmap.router)


# Rota raiz
@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "AirbnbRJ API - Backend para visualização de dados Airbnb do Rio de Janeiro",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


# Rota de health check
@app.get("/health", tags=["Root"])
async def health_check():
    """Verifica se a API está funcionando."""
    return {"status": "healthy", "database": "connected"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
