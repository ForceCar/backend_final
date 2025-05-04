"""
Configurações da aplicação
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"

# Verifica se o diretório de logs existe
if not LOGS_DIR.exists():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Constantes da aplicação
APP_NAME = "Forsecar Backend API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "API para geração automatizada de propostas da Forsecar"

# Variáveis de ambiente (configuráveis via .env)
ENV = os.getenv("ENVIRONMENT", "development")
API_PREFIX = os.getenv("API_PREFIX", "/api")

# URLs da API - permite fácil migração de localhost para produção
API_HOST = os.getenv("API_HOST", "http://localhost:8000")
if ENV == "production":
    API_HOST = "https://api.forcecar.org"

# Caminho para o endpoint principal (sem o prefixo, que é adicionado no router)
PROPOSTA_ENDPOINT = "/gerar_proposta_rodrigo"
