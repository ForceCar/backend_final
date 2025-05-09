"""
Serviço para geração de PDFs de proposta
"""
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from app.services import logger_service
import io
from PyPDF2 import PdfReader, PdfWriter

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


def fill_pdf_form(template_path: str, output_path: str, form_data: dict) -> None:
    """
    Preenche um formulário PDF com os dados fornecidos
    
    Args:
        template_path: Caminho para o arquivo PDF de template
        output_path: Caminho onde o PDF preenchido será salvo
        form_data: Dicionário com os dados a serem preenchidos no formulário
        
    Returns:
        None
    """
    logger_service.log_info(f"Preenchendo formulário PDF: {template_path}")
    
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    
    for page in writer.pages:
        if "/Annots" in page:
            writer.update_page_form_field_values(page, form_data)
    
    logger_service.log_info(f"Salvando PDF preenchido em: {output_path}")
    with open(output_path, "wb") as f:
        writer.write(f)


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
            content=pdf_bytes,
            headers=headers
        )
        
        if response.status_code not in (200, 201):
            erro = f"Falha ao fazer upload do PDF. Status: {response.status_code}, Resposta: {response.text}"
            logger_service.log_error(erro)
            raise Exception(erro)
            
    # URL pública para o PDF
    url_publica = f"{SUPABASE_URL}/storage/v1/object/public/{PDF_BUCKET_NAME}/{nome_arquivo}"
    logger_service.log_info(f"PDF enviado com sucesso. URL pública: {url_publica}")
    
    return url_publica


async def gerar_pdf_proposta(dados: Dict[str, Any]) -> str:
    """
    Gera um PDF de proposta com base nos dados fornecidos
    
    Args:
        dados: Dados da proposta
    
    Returns:
        URL pública do PDF gerado
    """
    logger_service.log_info("Iniciando geração de PDF de proposta...")
    
    try:
        # Mapear os dados para o formato esperado pelo formulário PDF
        form_data = await mapear_dados_para_formulario(dados)
        
        # Determinar qual template usar com base no desconto
        desconto = dados.get("desconto_aplicado", 0)
        template_url, template_type = await selecionar_template(desconto)
        
        # Baixar o template
        logger_service.log_info(f"Baixando template: {template_url}")
        template_bytes = await baixar_template(template_url)
        
        # Verificar se o template foi baixado com sucesso
        if not template_bytes:
            raise Exception("Falha ao baixar template PDF")
        
        # Criar arquivos temporários para processamento
        proposta_id = dados.get("id", str(uuid.uuid4()))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"proposta_{proposta_id}_{timestamp}.pdf"
        
        # Caminhos temporários para processamento local
        temp_template_path = f"/tmp/template_{proposta_id}.pdf"
        temp_output_path = f"/tmp/{nome_arquivo}"
        
        # Salvar o template baixado para processamento
        with open(temp_template_path, "wb") as f:
            f.write(template_bytes)
        
        # Preencher o formulário PDF
        logger_service.log_info(f"Preenchendo formulário PDF com {len(form_data)} campos")
        fill_pdf_form(temp_template_path, temp_output_path, form_data)
        
        # Ler o PDF gerado para upload
        with open(temp_output_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Fazer upload do PDF para o Supabase
        url_publica = await upload_pdf_para_supabase(pdf_bytes, nome_arquivo)
        
        logger_service.log_info(f"PDF gerado e enviado com sucesso: {url_publica}")
        return url_publica
        
    except Exception as e:
        erro = f"Erro na geração do PDF: {str(e)}"
        logger_service.log_error(erro)
        raise Exception(erro)
