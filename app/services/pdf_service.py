"""
Serviço para geração de PDFs de proposta
"""
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any
from app.services import logger_service
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# URLs dos templates de PDF no Supabase
PDF_COM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-com-desconto//proposta-forcecar-com-desconto.pdf"
PDF_SEM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-sem-desconto//proposta-forcecar-sem-desconto.pdf"

# Credenciais Supabase
SUPABASE_URL = "https://ahvryabvarxisvfdnmye.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFodnJ5YWJ2YXJ4aXN2ZmRubXllIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MzYxMjk0NiwiZXhwIjoyMDU5MTg4OTQ2fQ.BPoLMoBvXZ-_7uQVDO1OuTHmP3mNyxT6ZclYSQEoFlc"

# Constantes para identificar os templates
TEMPLATE_COM_DESCONTO = "com_desconto"
TEMPLATE_SEM_DESCONTO = "sem_desconto"

# Bucket onde os PDFs gerados serão armazenados
PDF_BUCKET_NAME = "propostas-geradas"


async def selecionar_template(desconto: float) -> tuple[str, str]:
    """
    Seleciona o URL do template apropriado com base no valor do desconto
    
    Args:
        desconto: Valor do desconto aplicado
        
    Returns:
        Tupla contendo (URL do template, tipo de template)
    """
    logger_service.log_info(f"Selecionando template de PDF: desconto={desconto}")
    if desconto > 0:
        logger_service.log_info("Template COM desconto selecionado")
        return (PDF_COM_DESCONTO_URL, TEMPLATE_COM_DESCONTO)
    else:
        logger_service.log_info("Template SEM desconto selecionado")
        return (PDF_SEM_DESCONTO_URL, TEMPLATE_SEM_DESCONTO)


async def baixar_template(url: str) -> bytes:
    """
    Baixa o template de PDF da URL especificada
    
    Args:
        url: URL do template de PDF
        
    Returns:
        Conteúdo binário do template
    """
    logger_service.log_info(f"Baixando template PDF: {url}")
    try:
        # Usando um timeout maior (60 segundos) para garantir que arquivos maiores sejam baixados
        timeout = httpx.Timeout(60.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger_service.log_info("Iniciando download do template...")
            response = await client.get(url)
            
            if response.status_code != 200:
                erro = f"Falha ao baixar template PDF. Status: {response.status_code}"
                logger_service.log_error(erro)
                raise Exception(erro)
            
            logger_service.log_info(f"Template PDF baixado com sucesso. Tamanho: {len(response.content)} bytes")
            return response.content
    except httpx.TimeoutException as e:
        erro = f"Timeout ao baixar o template PDF: {str(e)}"
        logger_service.log_error(erro)
        raise Exception(erro)
    except Exception as e:
        erro = f"Erro ao baixar o template PDF: {str(e)}"
        logger_service.log_error(erro)
        raise Exception(erro)


async def mapear_dados_para_formulario(dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapeia os dados da proposta para os campos do formulário PDF
    
    Args:
        dados: Dados da proposta
        
    Returns:
        Dicionário com valores mapeados para os campos do formulário
    """
    logger_service.log_info("Mapeando dados para formulário PDF")
    campos: Dict[str, Any] = {}
    # Campos básicos do cliente e veículo
    campos["nome_cliente"] = dados.get("nome_cliente", "")
    campos["telefone_cliente"] = dados.get("telefone_cliente", "")
    campos["email_cliente"] = dados.get("email_cliente", "")
    campos["marca_carro"] = dados.get("marca_veiculo", "")
    campos["modelo_carro"] = dados.get("modelo_veiculo", "")
    campos["teto_solar"] = dados.get("teto_solar", "")
    campos["porta-malas"] = dados.get("abertura_porta_malas", "")
    campos["tipo_documentacao"] = dados.get("tipo_documentacao", "")
    campos["pacote_revisao"] = dados.get("pacote_revisao", "")
    
    # Obtém valores dos vidros
    vidro_10_anos_valor = dados.get("vidro_10_anos", "")
    vidro_5_anos_valor = dados.get("vidro_5_anos", "")
    
    # Preenche todos os campos de vidros com os mesmos valores
    campos["vidro_10_anos"] = vidro_10_anos_valor
    campos["vidro_5_anos"] = vidro_5_anos_valor
    campos["vidro_5_anos_18mm"] = vidro_5_anos_valor
    campos["vidro_5_anos_ultralight"] = vidro_5_anos_valor
    # Desconto aplicado
    desconto_val = dados.get("desconto_aplicado", 0)
    campos["desconto"] = f"R$ {desconto_val:.2f}" if desconto_val else ""
    # Cenários e condições de pagamento
    cenarios = dados.get("cenarios", {})
    suffix_map = {"Comfort 10 anos": "10_anos", "Comfort 18 mm": "18mm", "Ultralight": "ultralight"}
    for nome_c, sufixo in suffix_map.items():
        cenario = cenarios.get(nome_c)
        if not cenario:
            continue
        
        cond_pagto = cenario.get("condicoes_pagamento", {})
        
        # À vista
        a_v = cond_pagto.get("a_vista", {})
        campos[f"a_vista_{sufixo}"] = f"R$ {a_v.get('valor_total', 0):.2f}"
        campos[f"total_{sufixo}"] = f"R$ {a_v.get('valor_total', 0):.2f}"
        
        # 2x sem juros
        duas = cond_pagto.get("duas_vezes", {})
        parcelas2 = duas.get("parcelas", [])
        if len(parcelas2) >= 2:
            campos[f"primeira_parcela_2x_{sufixo}"] = f"R$ {parcelas2[0]['valor']:.2f}"
            campos[f"segunda_parcela_2x_{sufixo}"] = f"R$ {parcelas2[1]['valor']:.2f}"
        campos[f"total_2x_{sufixo}"] = f"R$ {duas.get('valor_total', 0):.2f}"
        
        # 3x
        tres = cond_pagto.get("tres_vezes", {})
        parcelas3 = tres.get("parcelas", [])
        if len(parcelas3) >= 1:
            campos[f"sinal_50_3x_{sufixo}"] = f"R$ {parcelas3[0]['valor']:.2f}"
        if len(parcelas3) >= 2:
            campos[f"primeira_parcela_3x_{sufixo}"] = f"R$ {parcelas3[1]['valor']:.2f}"
        if len(parcelas3) >= 3:
            campos[f"segunda_parcela_3x_{sufixo}"] = f"R$ {parcelas3[2]['valor']:.2f}"
        campos[f"total_3x_{sufixo}"] = f"R$ {tres.get('valor_total', 0):.2f}"
        
        # 4x
        quatro = cond_pagto.get("quatro_vezes", {})
        parcelas4 = quatro.get("parcelas", [])
        if len(parcelas4) >= 1:
            campos[f"sinal_60_4x_{sufixo}"] = f"R$ {parcelas4[0]['valor']:.2f}"
        if len(parcelas4) >= 2:
            campos[f"primeira_parcela_4x_{sufixo}"] = f"R$ {parcelas4[1]['valor']:.2f}"
        if len(parcelas4) >= 3:
            campos[f"segunda_parcela_4x_{sufixo}"] = f"R$ {parcelas4[2]['valor']:.2f}"
        if len(parcelas4) >= 4:
            campos[f"terceira_parcela_4x_{sufixo}"] = f"R$ {parcelas4[3]['valor']:.2f}"
        campos[f"total_4x_{sufixo}"] = f"R$ {quatro.get('valor_total', 0):.2f}"
        
        # Cartão de crédito
        cartao = cond_pagto.get("cartao", {})
        for n in range(4, 11):
            opc = cartao.get(f"{n}x", {})
            campos[f"cartao_{n}_parcelas_{sufixo}"] = f"R$ {opc.get('valor_parcela', 0):.2f}"
    
    # Contagem de campos preenchidos para log
    campos_preenchidos = len([k for k, v in campos.items() if v])
    logger_service.log_info(f"Dados mapeados para formulário PDF: {campos_preenchidos} campos preenchidos")
    
    return campos


# Mapeamento de coordenadas para preenchimento de campos no PDF
# Formato: (page, left, right, width, bottom, top, height)
# Coordenadas para a página 11 no template COM DESCONTO
COORDINATE_MAP_COM_DESCONTO_PAGE_11: Dict[str, Dict[str, Any]] = {
    # Informações básicas página 11 - COM DESCONTO
    "nome_cliente": {"page": 11, "left": 157.44, "right": 576.0, "width": 418.56, "bottom": 611.37, "top": 632.25, "height": 20.88, "alignment": "left"},
    "telefone_cliente": {"page": 11, "left": 157.9, "right": 576.46, "width": 418.56, "bottom": 586.41, "top": 607.29, "height": 20.88, "alignment": "left"},
    "email_cliente": {"page": 11, "left": 157.16, "right": 575.72, "width": 418.56, "bottom": 561.34, "top": 582.22, "height": 20.88, "alignment": "left"},
    "marca_carro": {"page": 11, "left": 158.9, "right": 577.46, "width": 418.56, "bottom": 535.44, "top": 556.32, "height": 20.88, "alignment": "left"},
    "modelo_carro": {"page": 11, "left": 158.9, "right": 577.46, "width": 418.56, "bottom": 509.54, "top": 530.42, "height": 20.88, "alignment": "left"},
    "teto_solar": {"page": 11, "left": 158.25, "right": 576.81, "width": 418.56, "bottom": 484.67, "top": 505.55, "height": 20.88, "alignment": "left"},
    "porta-malas": {"page": 11, "left": 158.45, "right": 577.01, "width": 418.56, "bottom": 458.85, "top": 479.73, "height": 20.88, "alignment": "left"},
    "tipo_documentacao": {"page": 11, "left": 158.46, "right": 577.02, "width": 418.56, "bottom": 433.12, "top": 454.0, "height": 20.88, "alignment": "left"},
    "desconto": {"page": 11, "left": 157.44, "right": 576.0, "width": 418.56, "bottom": 378.25, "top": 399.13, "height": 20.88, "alignment": "left"},
    "vidro_10_anos": {"page": 11, "left": 186.0, "right": 313.92, "width": 127.92, "bottom": 242.89, "top": 263.53, "height": 20.64, "alignment": "left"},
    "vidro_5_anos_18mm": {"page": 11, "left": 315.36, "right": 444.48, "width": 129.12, "bottom": 220.81, "top": 241.93, "height": 21.12, "alignment": "left"},
    "vidro_5_anos_ultralight": {"page": 11, "left": 445.92, "right": 573.6, "width": 127.68, "bottom": 220.81, "top": 241.93, "height": 21.12, "alignment": "left"},
    "pacote_revisao": {"page": 11, "left": 19.92, "right": 184.56, "width": 164.64, "bottom": 199.21, "top": 219.85, "height": 20.64, "alignment": "left"},
    "total_10_anos": {"page": 11, "left": 186.21, "right": 317.25, "width": 131.04, "bottom": 708.32, "top": 729.44, "height": 21.12, "alignment": "left"},
    "total_18mm": {"page": 11, "left": 318.46, "right": 438.77, "width": 120.31, "bottom": 708.32, "top": 729.44, "height": 21.12, "alignment": "left"},
    "total_ultralight": {"page": 11, "left": 439.98, "right": 574.72, "width": 134.74, "bottom": 708.69, "top": 729.81, "height": 21.12, "alignment": "left"},
}

# Coordenadas para a página 11 no template SEM DESCONTO
COORDINATE_MAP_SEM_DESCONTO_PAGE_11: Dict[str, Dict[str, Any]] = {
    # Informações básicas página 11 - SEM DESCONTO (coordenadas diferentes)
    "nome_cliente": {"page": 11, "left": 157.44, "right": 576.0, "width": 418.56, "bottom": 611.37, "top": 632.25, "height": 20.88, "alignment": "left"},
    "telefone_cliente": {"page": 11, "left": 157.9, "right": 576.46, "width": 418.56, "bottom": 586.41, "top": 607.29, "height": 20.88, "alignment": "left"},
    "email_cliente": {"page": 11, "left": 157.16, "right": 575.72, "width": 418.56, "bottom": 561.34, "top": 582.22, "height": 20.88, "alignment": "left"},
    "marca_carro": {"page": 11, "left": 158.9, "right": 577.46, "width": 418.56, "bottom": 535.44, "top": 556.32, "height": 20.88, "alignment": "left"},
    "modelo_carro": {"page": 11, "left": 158.9, "right": 577.46, "width": 418.56, "bottom": 509.54, "top": 530.42, "height": 20.88, "alignment": "left"},
    "teto_solar": {"page": 11, "left": 158.25, "right": 576.81, "width": 418.56, "bottom": 484.67, "top": 505.55, "height": 20.88, "alignment": "left"},
    "porta-malas": {"page": 11, "left": 158.45, "right": 577.01, "width": 418.56, "bottom": 458.85, "top": 479.73, "height": 20.88, "alignment": "left"},
    "tipo_documentacao": {"page": 11, "left": 158.46, "right": 577.02, "width": 418.56, "bottom": 433.12, "top": 454.0, "height": 20.88, "alignment": "left"},
    "vidro_10_anos": {"page": 11, "left": 186.0, "right": 313.92, "width": 127.92, "bottom": 242.89, "top": 263.53, "height": 20.64, "alignment": "left"},
    "vidro_5_anos": {"page": 11, "left": 315.36, "right": 444.48, "width": 129.12, "bottom": 220.81, "top": 241.93, "height": 21.12, "alignment": "left"},
    "vidro_5_anos_18mm": {"page": 11, "left": 315.36, "right": 444.48, "width": 129.12, "bottom": 220.81, "top": 241.93, "height": 21.12, "alignment": "left"},
    "vidro_5_anos_ultralight": {"page": 11, "left": 445.92, "right": 573.6, "width": 127.68, "bottom": 220.81, "top": 241.93, "height": 21.12, "alignment": "left"},
    "pacote_revisao": {"page": 11, "left": 19.92, "right": 184.56, "width": 164.64, "bottom": 199.21, "top": 219.85, "height": 20.64, "alignment": "left"},
    "total_10_anos": {"page": 11, "left": 186.21, "right": 317.25, "width": 131.04, "bottom": 708.32, "top": 729.44, "height": 21.12, "alignment": "left"},
    "total_18mm": {"page": 11, "left": 318.46, "right": 438.77, "width": 120.31, "bottom": 708.32, "top": 729.44, "height": 21.12, "alignment": "left"},
    "total_ultralight": {"page": 11, "left": 439.98, "right": 574.72, "width": 134.74, "bottom": 708.69, "top": 729.81, "height": 21.12, "alignment": "left"},
}

# Coordenadas para a página 12 (comum a ambos os templates)
COORDINATE_MAP_PAGE_12: Dict[str, Dict[str, Any]] = {

    # Condições pagamento página 12 - Comfort 10 Anos
    "a_vista_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 700, "top": 720, "height": 20, "alignment": "left"},
    "total_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 700, "top": 720, "height": 20, "alignment": "left"},
    "primeira_parcela_2x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 680, "top": 700, "height": 20, "alignment": "left"},
    "segunda_parcela_2x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 680, "top": 700, "height": 20, "alignment": "left"},
    "total_2x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 660, "top": 680, "height": 20, "alignment": "left"},
    "sinal_50_3x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 640, "top": 660, "height": 20, "alignment": "left"},
    "primeira_parcela_3x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 640, "top": 660, "height": 20, "alignment": "left"},
    "segunda_parcela_3x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 620, "top": 640, "height": 20, "alignment": "left"},
    "terceira_parcela_3x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 620, "top": 640, "height": 20, "alignment": "left"},
    "total_3x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 600, "top": 620, "height": 20, "alignment": "left"},
    "sinal_60_4x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 580, "top": 600, "height": 20, "alignment": "left"},
    "primeira_parcela_4x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 580, "top": 600, "height": 20, "alignment": "left"},
    "segunda_parcela_4x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 560, "top": 580, "height": 20, "alignment": "left"},
    "terceira_parcela_4x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 560, "top": 580, "height": 20, "alignment": "left"},
    "quarta_parcela_4x_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 540, "top": 560, "height": 20, "alignment": "left"},
    "total_4x_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 540, "top": 560, "height": 20, "alignment": "left"},
    "cartao_4_parcelas_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 520, "top": 540, "height": 20, "alignment": "left"},
    "cartao_5_parcelas_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 520, "top": 540, "height": 20, "alignment": "left"},
    "cartao_6_parcelas_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 500, "top": 520, "height": 20, "alignment": "left"},
    "cartao_7_parcelas_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 500, "top": 520, "height": 20, "alignment": "left"},
    "cartao_8_parcelas_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 480, "top": 500, "height": 20, "alignment": "left"},
    "cartao_9_parcelas_10_anos": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 480, "top": 500, "height": 20, "alignment": "left"},
    "cartao_10_parcelas_10_anos": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 460, "top": 480, "height": 20, "alignment": "left"},
    # Condições pagamento página 12 - Comfort 18 mm
    "a_vista_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 440, "top": 460, "height": 20, "alignment": "left"},
    "total_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 440, "top": 460, "height": 20, "alignment": "left"},
    "primeira_parcela_2x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 420, "top": 440, "height": 20, "alignment": "left"},
    "segunda_parcela_2x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 420, "top": 440, "height": 20, "alignment": "left"},
    "total_2x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 400, "top": 420, "height": 20, "alignment": "left"},
    "sinal_50_3x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 380, "top": 400, "height": 20, "alignment": "left"},
    "primeira_parcela_3x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 380, "top": 400, "height": 20, "alignment": "left"},
    "segunda_parcela_3x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 360, "top": 380, "height": 20, "alignment": "left"},
    "terceira_parcela_3x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 360, "top": 380, "height": 20, "alignment": "left"},
    "total_3x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 340, "top": 360, "height": 20, "alignment": "left"},
    "sinal_60_4x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 320, "top": 340, "height": 20, "alignment": "left"},
    "primeira_parcela_4x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 320, "top": 340, "height": 20, "alignment": "left"},
    "segunda_parcela_4x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 300, "top": 320, "height": 20, "alignment": "left"},
    "terceira_parcela_4x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 300, "top": 320, "height": 20, "alignment": "left"},
    "quarta_parcela_4x_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 280, "top": 300, "height": 20, "alignment": "left"},
    "total_4x_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 280, "top": 300, "height": 20, "alignment": "left"},
    "cartao_4_parcelas_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 260, "top": 280, "height": 20, "alignment": "left"},
    "cartao_5_parcelas_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 260, "top": 280, "height": 20, "alignment": "left"},
    "cartao_6_parcelas_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 240, "top": 260, "height": 20, "alignment": "left"},
    "cartao_7_parcelas_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 240, "top": 260, "height": 20, "alignment": "left"},
    "cartao_8_parcelas_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 220, "top": 240, "height": 20, "alignment": "left"},
    "cartao_9_parcelas_18mm": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 220, "top": 240, "height": 20, "alignment": "left"},
    "cartao_10_parcelas_18mm": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 200, "top": 220, "height": 20, "alignment": "left"},
    # Condições pagamento página 12 - Ultralight
    "a_vista_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 180, "top": 200, "height": 20, "alignment": "left"},
    "total_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 180, "top": 200, "height": 20, "alignment": "left"},
    "primeira_parcela_2x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 160, "top": 180, "height": 20, "alignment": "left"},
    "segunda_parcela_2x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 160, "top": 180, "height": 20, "alignment": "left"},
    "total_2x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 140, "top": 160, "height": 20, "alignment": "left"},
    "sinal_50_3x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 120, "top": 140, "height": 20, "alignment": "left"},
    "primeira_parcela_3x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 120, "top": 140, "height": 20, "alignment": "left"},
    "segunda_parcela_3x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 100, "top": 120, "height": 20, "alignment": "left"},
    "terceira_parcela_3x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 100, "top": 120, "height": 20, "alignment": "left"},
    "total_3x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 80, "top": 100, "height": 20, "alignment": "left"},
    "sinal_60_4x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 60, "top": 80, "height": 20, "alignment": "left"},
    "primeira_parcela_4x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 60, "top": 80, "height": 20, "alignment": "left"},
    "segunda_parcela_4x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 40, "top": 60, "height": 20, "alignment": "left"},
    "terceira_parcela_4x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 40, "top": 60, "height": 20, "alignment": "left"},
    "quarta_parcela_4x_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 20, "top": 40, "height": 20, "alignment": "left"},
    "total_4x_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 20, "top": 40, "height": 20, "alignment": "left"},
    "cartao_4_parcelas_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": 0, "top": 20, "height": 20, "alignment": "left"},
    "cartao_5_parcelas_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": 0, "top": 20, "height": 20, "alignment": "left"},
    "cartao_6_parcelas_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": -20, "top": 0, "height": 20, "alignment": "left"},
    "cartao_7_parcelas_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": -20, "top": 0, "height": 20, "alignment": "left"},
    "cartao_8_parcelas_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": -40, "top": -20, "height": 20, "alignment": "left"},
    "cartao_9_parcelas_ultralight": {"page": 12, "left": 300, "right": 500, "width": 200, "bottom": -40, "top": -20, "height": 20, "alignment": "left"},
    "cartao_10_parcelas_ultralight": {"page": 12, "left": 100, "right": 300, "width": 200, "bottom": -60, "top": -40, "height": 20, "alignment": "left"},
}


# Função auxiliar para obter o mapa de coordenadas apropriado com base no template
def obter_coordinate_map(template_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Retorna o mapa de coordenadas apropriado com base no tipo de template
    
    Args:
        template_type: Tipo do template (com_desconto ou sem_desconto)
        
    Returns:
        Mapa de coordenadas para o template especificado
    """
    # Inicializar com as coordenadas da página 12 (comuns a ambos os templates)
    coordinate_map = COORDINATE_MAP_PAGE_12.copy()
    
    # Adicionar as coordenadas da página 11 de acordo com o template
    if template_type == TEMPLATE_COM_DESCONTO:
        coordinate_map.update(COORDINATE_MAP_COM_DESCONTO_PAGE_11)
    else:  # template_type == TEMPLATE_SEM_DESCONTO
        coordinate_map.update(COORDINATE_MAP_SEM_DESCONTO_PAGE_11)
    
    return coordinate_map


async def preencher_formulario_pdf(template_bytes: bytes, campos: Dict[str, Any], template_type: str) -> bytes:
    """
    Preenche os campos do formulário no PDF usando coordenadas.
    IMPORTANTE: Usa uma abordagem que preserva o PDF original.
    """
    logger_service.log_info("Preenchendo formulário PDF via coordenadas - Abordagem preservadora")
    if not template_bytes or len(template_bytes) < 100:
        erro = f"Template de PDF inválido ou vazio: {len(template_bytes) if template_bytes else 0} bytes"
        logger_service.log_error(erro)
        raise Exception(erro)
    
    try:
        # Abordagem: não modificar o PDF original, mas criar páginas separadas
        # e depois juntar com o original
        
        # 1. Ler o PDF original
        logger_service.log_info("Lendo PDF original")
        reader = PdfReader(io.BytesIO(template_bytes))
        total_pages = len(reader.pages)
        logger_service.log_info(f"PDF original possui {total_pages} páginas")
        
        # 2. Separar campos por página
        campos_por_pagina = {}
        for field, value in campos.items():
            if not value:  # Ignorar campos vazios
                continue
                
            # Obter o mapa de coordenadas apropriado para o template
            coordinate_map = obter_coordinate_map(template_type)
            coord = coordinate_map.get(field)
            if not coord:
                continue
                
            page_num = coord.get("page")
            if page_num not in campos_por_pagina:
                campos_por_pagina[page_num] = []
                
            campos_por_pagina[page_num].append((field, value, coord))
        
        # 3. Criar novo PDF resultado
        writer = PdfWriter()
        
        # 4. Adicionar cada página do original e modificar se necessário
        for i in range(total_pages):
            page_num = i + 1  # Páginas são numeradas a partir de 1
            
            # Copiar a página original
            original_page = reader.pages[i]
            
            # Se esta página tem campos a preencher, criar um overlay
            if page_num in campos_por_pagina and campos_por_pagina[page_num]:
                logger_service.log_info(f"Processando página {page_num} com {len(campos_por_pagina[page_num])} campos")
                
                # Criar uma página em branco com as mesmas dimensões para o overlay
                # Em vez de alterar a original, faremos uma sobreposição separada
                page_width = float(original_page.mediabox.width)
                page_height = float(original_page.mediabox.height)
                
                # Criar overlay como página separada
                packet = io.BytesIO()
                overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))
                overlay_canvas.setFont("Helvetica-Bold", 14)
                
                # Adicionar cada campo ao overlay
                for field, value, coord in campos_por_pagina[page_num]:
                    # Verificar se estamos usando o formato antigo ou novo
                    if "left" in coord:
                        # Novo formato (left, right, width, bottom, top, height)
                        left = float(coord.get("left"))
                        bottom = float(coord.get("bottom"))
                        width = float(coord.get("width"))
                        height = float(coord.get("height"))
                        # Em PDF, a origem Y (0,0) é no canto inferior esquerdo
                        # bottom é a coordenada Y do texto (da base do texto)
                    else:
                        # Formato antigo (x, y, width, height) - para compatibilidade
                        left = float(coord.get("x", 0))
                        bottom = float(coord.get("y", 0))
                        width = float(coord.get("width", 400))  # Valor padrão caso não exista
                        height = float(coord.get("height", 20))  # Valor padrão caso não exista
                    
                    alignment = coord.get("alignment", "left")  # Valor padrão caso não exista
                    
                    # Configurar alinhamento do texto
                    text = str(value)
                    if alignment == "center":
                        overlay_canvas.setFillColorRGB(0, 0, 0)  # Preto
                        # Centralizar o texto na largura disponível
                        text_width = overlay_canvas.stringWidth(text, "Helvetica-Bold", 14)
                        text_x = left + (width - text_width) / 2
                        overlay_canvas.drawString(text_x, bottom, text)
                    elif alignment == "right":
                        overlay_canvas.setFillColorRGB(0, 0, 0)  # Preto
                        # Alinhar à direita na largura disponível
                        text_width = overlay_canvas.stringWidth(text, "Helvetica-Bold", 14)
                        text_x = left + width - text_width
                        overlay_canvas.drawString(text_x, bottom, text)
                    else:  # left (padrão)
                        overlay_canvas.setFillColorRGB(0, 0, 0)  # Preto
                        overlay_canvas.drawString(left, bottom, text)
                    
                    logger_service.log_info(f"Campo '{field}': '{value}' - position: left={left}, bottom={bottom}, width={width}, height={height}, alinhamento: {alignment}, página: {page_num}")
                
                # Finalizar o overlay
                overlay_canvas.save()
                packet.seek(0)
                
                # Criar uma cópia da página original para não modificá-la diretamente
                page_copy = PdfWriter()
                page_copy.add_page(original_page)
                page_copy_bytes = io.BytesIO()
                page_copy.write(page_copy_bytes)
                page_copy_bytes.seek(0)
                page_reader = PdfReader(page_copy_bytes)
                page_to_modify = page_reader.pages[0]
                
                try:
                    # Aplicar o overlay à cópia
                    overlay_reader = PdfReader(packet)
                    if overlay_reader.pages:
                        page_to_modify.merge_page(overlay_reader.pages[0])
                        writer.add_page(page_to_modify)
                        logger_service.log_info(f"Overlay aplicado com sucesso na página {page_num}")
                    else:
                        # Se falhou, adicionar a página original
                        writer.add_page(original_page)
                        logger_service.log_warning(f"Overlay sem páginas para a página {page_num}")
                except Exception as e:
                    # Se houver erro no merge, adicionar a página original
                    writer.add_page(original_page)
                    logger_service.log_error(f"Erro ao aplicar overlay na página {page_num}: {e}")
            else:
                # Se não há campos para esta página, adicionar a original sem modificação
                writer.add_page(original_page)
                
        # 5. Salvar o resultado final
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        result = output.read()
        
        if len(result) < len(template_bytes) / 2:
            logger_service.log_error("PDF gerado muito pequeno, possível corrupção!")
            return template_bytes
            
        logger_service.log_info(f"PDF finalizado com sucesso: {len(result)} bytes")
        return result
        
    except Exception as e:
        logger_service.log_error(f"Erro crítico ao processar PDF: {str(e)}")
        # Em caso de erro, retornar o PDF original para preservar a integridade
        return template_bytes


async def upload_pdf_para_supabase(pdf_bytes: bytes, nome_arquivo: str) -> str:
    """
    Faz o upload do PDF gerado para o bucket do Supabase
    
    Args:
        pdf_bytes: Conteúdo binário do PDF
        nome_arquivo: Nome do arquivo a ser salvo
    
    Returns:
        URL pública do PDF salvo
    """
    logger_service.log_info(f"Fazendo upload do PDF: {nome_arquivo}")
    
    # Endpoint para upload
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{PDF_BUCKET_NAME}/{nome_arquivo}"
    
    # Headers para autenticação
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/pdf"
    }
    
    # Fazer o upload
    async with httpx.AsyncClient() as client:
        response = await client.post(
            upload_url,
            headers=headers,
            content=pdf_bytes
        )
        
        if response.status_code not in (200, 201):
            erro = f"Falha ao fazer upload do PDF. Status: {response.status_code}, Resposta: {response.text}"
            logger_service.log_error(erro)
            raise Exception(erro)
    
    # URL pública do PDF salvo
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{PDF_BUCKET_NAME}/{nome_arquivo}"
    logger_service.log_info(f"Upload concluído com sucesso. URL: {public_url}")
    
    return public_url


async def gerar_pdf_proposta(dados: Dict[str, Any]) -> str:
    """
    Gera um PDF de proposta com base nos dados fornecidos
    
    Args:
        dados: Dados da proposta
    
    Returns:
        URL pública do PDF gerado
    """
    logger_service.log_info("=== INÍCIO: GERAÇÃO DE PDF DE PROPOSTA ===")
    
    try:
        # Extrair informações básicas
        nome_cliente = dados.get("nome_cliente", "Cliente")
        desconto = dados.get("desconto_aplicado", 0)
        tipo_blindagem = dados.get("tipo_blindagem", "")
        
        logger_service.log_info(f"Gerando proposta para: {nome_cliente} | Tipo: {tipo_blindagem} | Desconto: {desconto}")
        
        # Selecionar o template apropriado
        template_url_tuple = await selecionar_template(desconto)
        template_url, template_type = template_url_tuple
        
        # Baixar o template usando apenas a URL
        template_bytes = await baixar_template(template_url)
        
        # Mapear dados para os campos do formulário
        campos_preenchidos = await mapear_dados_para_formulario(dados)
        
        # Preencher os campos no PDF com o tipo de template correto
        pdf_preenchido = await preencher_formulario_pdf(template_bytes, campos_preenchidos, template_type)
        
        # Gerar nome de arquivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_seguro = nome_cliente.replace(" ", "_").lower()
        unique_id = str(uuid.uuid4())[:8]
        nome_arquivo = f"proposta_{nome_seguro}_{timestamp}_{unique_id}.pdf"
        
        # Fazer upload do PDF para o Supabase
        pdf_url = await upload_pdf_para_supabase(pdf_preenchido, nome_arquivo)
        
        logger_service.log_info(f"PDF gerado com sucesso: {pdf_url}")
        logger_service.log_info("=== FIM: GERAÇÃO DE PDF DE PROPOSTA ===")
        
        return pdf_url
        
    except Exception as e:
        logger_service.log_error(f"Erro ao gerar PDF de proposta: {str(e)}")
        raise e
