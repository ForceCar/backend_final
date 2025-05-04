"""
Aplicação principal do backend Forsecar
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import proposta
from app.config import APP_NAME, APP_VERSION, APP_DESCRIPTION, API_PREFIX
from app.services.logger_service import logger

# Inicialização da aplicação FastAPI
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para origens específicas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão das rotas
app.include_router(proposta.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    """Rota de verificação básica da API"""
    return {
        "message": "Forsecar API está funcionando!",
        "version": APP_VERSION,
        "documentacao": "/docs"
    }


@app.get("/health")
async def health_check():
    """Endpoint para health check da aplicação"""
    return {"status": "healthy"}


if __name__ == "__main__":
    logger.info(f"Iniciando {APP_NAME} v{APP_VERSION}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
