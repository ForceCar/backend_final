"""
Serviço de logging da aplicação
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

# Configuração do logger
LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "app.log"

# Função para formatar o timestamp no padrão brasileiro
def format_time_brazil(record):
    dt = datetime.fromtimestamp(record["time"].timestamp())
    formatted = dt.strftime("%d/%m/%Y %H:%M:%S")
    record["time_brazil"] = formatted
    return record

# Configuração do formato de log personalizado
LOG_FORMAT = "<green>{time_brazil}</green> | <level>{level: <8}</level> | <level>{message}</level>"

# Configurar o logger
logger.remove()  # Remove o handler padrão

# Adiciona handler para console
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level="INFO",
    colorize=True,
    filter=format_time_brazil
)

# Adiciona handler para arquivo de log
logger.add(
    LOG_FILE,
    format="{time_brazil} | {level: <8} | {message}",
    level="INFO",
    rotation="10 MB",  # Rotação quando o arquivo atingir 10MB
    retention="30 days",  # Mantém logs por 30 dias
    filter=format_time_brazil
)


def log_raw_request_body(raw_body):
    """Registra o corpo bruto da requisição sem modificações"""
    try:
        # Decodifica o corpo bruto para string
        raw_body_str = raw_body.decode('utf-8')
        logger.info(f"RAW REQUEST BODY (UNMODIFIED): {raw_body_str}")
    except Exception as e:
        logger.error(f"Erro ao decodificar corpo bruto da requisição: {e}")

def log_request(request_data, client_info=None):
    """Registra informações sobre a requisição recebida"""
    # Log completo dos dados brutos recebidos
    logger.info(f"Raw Request Data: {json.dumps(request_data, indent=2)}")
    
    # Log de informações do cliente
    if client_info:
        logger.info(f"Client Info: {client_info}")
    
    # Extrai informações básicas do payload para o log
    nome_cliente = request_data.get("nome_cliente", "N/A")
    tipo_blindagem = request_data.get("tipo_blindagem", "N/A")
    
    # Log de início do processo
    logger.info(f"=== INICIANDO PROCESSAMENTO DE NOVA REQUISIÇÃO ====")
    logger.info(
        f"Requisição recebida - Cliente: {nome_cliente} | Tipo blindagem: {tipo_blindagem}"
    )
    
    if client_info:
        logger.debug(f"Info do cliente: {client_info}")
        
    return {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nome_cliente": nome_cliente,
        "tipo_blindagem": tipo_blindagem
    }


def log_saving_data(request_data):
    """Registra que os dados estão sendo salvos"""
    nome_cliente = request_data.get("nome_cliente", "N/A")
    logger.info(f"Salvando dados da proposta - Cliente: {nome_cliente}...")


def log_data_saved(request_data):
    """Registra que os dados foram salvos com sucesso, mostrando exatamente os campos recebidos"""
    
    # Registra que os dados foram salvos
    if "nome_cliente" in request_data:
        nome_cliente = request_data["nome_cliente"]
        logger.info(f"Dados da proposta salvos com sucesso - Cliente: {nome_cliente}")
    else:
        logger.info(f"Dados da proposta salvos com sucesso")
    
    # Log dos dados exatamente como recebidos, sem adicionar campos padrão
    logger.info(f"DADOS BRUTOS RECEBIDOS NA REQUISIÇÃO:")
    logger.info(f"{json.dumps(request_data, indent=2, sort_keys=True, ensure_ascii=False)}")
    
    # Informar quais campos estão presentes na requisição
    logger.info(f"CAMPOS PRESENTES NA REQUISIÇÃO: {', '.join(request_data.keys())}")
    
    # Criar e registrar informações estruturadas da proposta
    try:
        # Preparar dados base da proposta para logging
        proposal_data = {
            "nome": request_data.get("nome_cliente"),
            "telefone": request_data.get("telefone_cliente"),
            "email": request_data.get("email_cliente"),
            "nome_vendedor": request_data.get("nome_vendedor"),
            "marca_carro": request_data.get("marca_veiculo"),
            "modelo_carro": request_data.get("modelo_veiculo"),
            "marca_vidro_10_anos": request_data.get("marca_vidro_10_anos"),
            "marca_vidro_5_anos": request_data.get("marca_vidro_5_anos"),
            "teto_solar": request_data.get("teto_solar"),
            "origem_cliente": request_data.get("origem_cliente"),
            "pacote_revisao": request_data.get("pacote_revisao"),
            "documentacao_exercito": request_data.get("tipo_documentacao"),
            "porta_malas": request_data.get("abertura_porta_malas"),
            "desconto": request_data.get("desconto_aplicado"),
            "tipo_blindagem": request_data.get("tipo_blindagem"),
            "observacoes": request_data.get("observacoes")
        }
        
        # Adicionar dados específicos com base no tipo de blindagem escolhido
        tipo_blindagem = request_data.get("tipo_blindagem")
        logger.info(f"Tipo de blindagem: {tipo_blindagem}")
        
        if tipo_blindagem == "Nenhuma":
            # Para 'Nenhuma', registramos os valores de todas as opções de blindagem
            proposal_data["comfort_10_anos_sub_total"] = request_data.get("comfort10YearsSubTotal", 0)
            proposal_data["comfort_10_anos_desconto"] = request_data.get("comfort10YearsDiscount", 0)
            proposal_data["comfort_18mm_sub_total"] = request_data.get("comfort18mmSubTotal", 0)
            proposal_data["comfort_18mm_desconto"] = request_data.get("comfort18mmDiscount", 0)
            proposal_data["ultralight_sub_total"] = request_data.get("ultralightSubTotal", 0)
            proposal_data["ultralight_desconto"] = request_data.get("ultralightDiscount", 0)
            
            # Registrar informações de comparação das blindagens
            logger.info("COMPARAÇÃO DE BLINDAGENS:")
            logger.info(f"  - Comfort 10 anos: R$ {proposal_data['comfort_10_anos_sub_total']:,.2f} (Desconto: R$ {proposal_data['comfort_10_anos_desconto']:,.2f})")
            logger.info(f"  - Comfort 18 mm: R$ {proposal_data['comfort_18mm_sub_total']:,.2f} (Desconto: R$ {proposal_data['comfort_18mm_desconto']:,.2f})")
            logger.info(f"  - Ultralight: R$ {proposal_data['ultralight_sub_total']:,.2f} (Desconto: R$ {proposal_data['ultralight_desconto']:,.2f})")
            
        elif tipo_blindagem == "Comfort 10 anos":
            # Para 'Comfort 10 anos', registramos apenas os valores dessa opção
            proposal_data["sub_total_blindagem"] = request_data.get("comfort10YearsSubTotal", 0)
            proposal_data["desconto_blindagem"] = request_data.get("comfort10YearsDiscount", 0)
            logger.info(f"DETALHES DE BLINDAGEM COMFORT 10 ANOS:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
            
        elif tipo_blindagem == "Comfort 18 mm":
            # Para 'Comfort 18 mm', registramos apenas os valores dessa opção
            proposal_data["sub_total_blindagem"] = request_data.get("comfort18mmSubTotal", 0)
            proposal_data["desconto_blindagem"] = request_data.get("comfort18mmDiscount", 0)
            logger.info(f"DETALHES DE BLINDAGEM COMFORT 18MM:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
            
        elif tipo_blindagem == "Ultralight":
            # Para 'Ultralight', registramos apenas os valores dessa opção
            proposal_data["sub_total_blindagem"] = request_data.get("ultralightSubTotal", 0)
            proposal_data["desconto_blindagem"] = request_data.get("ultralightDiscount", 0)
            logger.info(f"DETALHES DE BLINDAGEM ULTRALIGHT:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
        
        # Log dos dados processados da proposta
        logger.info("DADOS PROCESSADOS DA PROPOSTA:")
        logger.info(f"{json.dumps(proposal_data, indent=2, sort_keys=True, ensure_ascii=False)}")
    
    except Exception as e:
        logger.error(f"Erro ao processar dados da proposta para logging: {str(e)}")
    
    # Separar os logs para facilitar a leitura
    logger.info("-" * 80)


def log_calculating(tipo_calculo):
    """Registra que os cálculos estão sendo realizados"""
    logger.info(f"Calculando {tipo_calculo}...")


def log_success(request_data, result=None):
    """Registra sucesso no processamento da requisição"""
    nome_cliente = request_data.get("nome_cliente", "N/A")
    logger.success(f"Proposta processada com sucesso - Cliente: {nome_cliente}")
    
    if result:
        logger.info(f"Resultado: {result}")
    
    logger.info(f"=== FINALIZADO PROCESSAMENTO DA REQUISIÇÃO ====")


def log_info(message):
    """Registra uma mensagem informativa"""
    logger.info(message)


def log_warning(message):
    """Registra uma mensagem de aviso"""
    logger.warning(message)


def log_error(error, request_data=None):
    """Registra erro no processamento da requisição"""
    if request_data:
        nome_cliente = request_data.get("nome_cliente", "N/A")
        logger.error(f"Erro ao processar proposta - Cliente: {nome_cliente} | Erro: {error}")
    else:
        logger.error(f"Erro na aplicação: {error}")
    
    logger.error(f"=== PROCESSAMENTO INTERROMPIDO COM ERRO ====")
