"""
Serviço para envio de mensagens e arquivos via WhatsApp usando Z-API
"""
import json
from typing import Dict, Any, Optional
import httpx
from app.services import logger_service

# Credenciais da Z-API
Z_API_INSTANCE_ID = "3E0A52D8D2564017044E4AEA87B09735"
Z_API_TOKEN = "32953E1D85E2BD497B9D2FDB"

# URLs base da API
Z_API_BASE_URL = "https://api.z-api.io/instances/{instance}/token/{token}"
Z_API_TEXT_ENDPOINT = "send-text"
Z_API_FILE_ENDPOINT = "send-file-url"


def formatar_numero_whatsapp(telefone: str) -> str:
    """
    Formata um número de telefone para o formato esperado pelo WhatsApp (apenas dígitos)
    
    Args:
        telefone: Número de telefone no formato recebido
        
    Returns:
        Número formatado para WhatsApp
    """
    # Remove caracteres não numéricos
    apenas_digitos = ''.join(filter(str.isdigit, telefone))
    
    # Certifica-se de que tem o código do país (55 para Brasil)
    if len(apenas_digitos) <= 11:  # Sem código de país
        apenas_digitos = "55" + apenas_digitos
        
    logger_service.log_info(f"Número formatado para WhatsApp: {apenas_digitos}")
    return apenas_digitos


async def enviar_mensagem_whatsapp(telefone: str, mensagem: str) -> Dict[str, Any]:
    """
    Envia uma mensagem de texto via WhatsApp usando Z-API
    
    Args:
        telefone: Número de telefone do destinatário
        mensagem: Texto da mensagem a ser enviada
        
    Returns:
        Resposta da API
    """
    logger_service.log_info(f"Enviando mensagem via WhatsApp para: {telefone}")
    
    # Formatar o número de telefone
    numero_whatsapp = formatar_numero_whatsapp(telefone)
    
    # URL da API
    url = Z_API_BASE_URL.format(
        instance=Z_API_INSTANCE_ID,
        token=Z_API_TOKEN
    ) + "/" + Z_API_TEXT_ENDPOINT
    
    # Dados da requisição
    payload = {
        "phone": numero_whatsapp,
        "message": mensagem
    }
    
    # Enviar a requisição
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status") == "success":
                logger_service.log_info("Mensagem enviada com sucesso")
            else:
                logger_service.log_error(f"Erro ao enviar mensagem. Status: {response.status_code}, Resposta: {response.text}")
            
            return response_data
            
        except Exception as e:
            erro = f"Exceção ao enviar mensagem via WhatsApp: {str(e)}"
            logger_service.log_error(erro)
            raise Exception(erro)


async def enviar_pdf_whatsapp(telefone: str, url_pdf: str, mensagem: str) -> Dict[str, Any]:
    """
    Envia um PDF via WhatsApp usando Z-API
    
    Args:
        telefone: Número de telefone do destinatário
        url_pdf: URL pública do arquivo PDF
        mensagem: Texto da mensagem que acompanha o arquivo
        
    Returns:
        Resposta da API
    """
    logger_service.log_info(f"Enviando PDF via WhatsApp para: {telefone}")
    
    # Formatar o número de telefone
    numero_whatsapp = formatar_numero_whatsapp(telefone)
    
    # URL da API
    url = Z_API_BASE_URL.format(
        instance=Z_API_INSTANCE_ID,
        token=Z_API_TOKEN
    ) + "/" + Z_API_FILE_ENDPOINT
    
    # Dados da requisição
    payload = {
        "phone": numero_whatsapp,
        "url": url_pdf,
        "caption": mensagem,  # Legenda/mensagem que acompanha o arquivo
        "fileName": "Proposta_ForceCarBlindagens.pdf"
    }
    
    # Enviar a requisição
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status") == "success":
                logger_service.log_info("PDF enviado com sucesso via WhatsApp")
            else:
                logger_service.log_error(f"Erro ao enviar PDF. Status: {response.status_code}, Resposta: {response.text}")
            
            return response_data
            
        except Exception as e:
            erro = f"Exceção ao enviar PDF via WhatsApp: {str(e)}"
            logger_service.log_error(erro)
            raise Exception(erro)
