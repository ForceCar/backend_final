"""
Serviço para geração de PDFs de proposta
"""
import os
import io
import uuid
import httpx
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, BinaryIO

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile
import os
from app.services import logger_service

# URLs dos templates de PDF no Supabase
PDF_COM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-com-desconto//Proposta%20COM%20Desconto%20Editavel.pdf"
PDF_SEM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-sem-desconto//Proposta%20SEM%20Desconto%20Editavel.pdf"

# Credenciais Supabase
SUPABASE_URL = "https://ahvryabvarxisvfdnmye.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFodnJ5YWJ2YXJ4aXN2ZmRubXllIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MzYxMjk0NiwiZXhwIjoyMDU5MTg4OTQ2fQ.BPoLMoBvXZ-_7uQVDO1OuTHmP3mNyxT6ZclYSQEoFlc"

# Bucket onde os PDFs gerados serão armazenados
PDF_BUCKET_NAME = "propostas-geradas"


async def selecionar_template(desconto: float) -> str:
    """
    Seleciona o URL do template apropriado com base no valor do desconto
    
    Args:
        desconto: Valor do desconto aplicado
        
    Returns:
        URL do template de PDF a ser utilizado
    """
    logger_service.log_info(f"Selecionando template de PDF: desconto={desconto}")
    if desconto > 0:
        logger_service.log_info("Template COM desconto selecionado")
        return PDF_COM_DESCONTO_URL
    else:
        logger_service.log_info("Template SEM desconto selecionado")
        return PDF_SEM_DESCONTO_URL


async def baixar_template(url: str) -> bytes:
    """
    Baixa o template de PDF da URL especificada
    
    Args:
        url: URL do template de PDF
        
    Returns:
        Conteúdo binário do template
    """
    logger_service.log_info(f"Baixando template PDF: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            erro = f"Falha ao baixar template PDF. Status: {response.status_code}"
            logger_service.log_error(erro)
            raise Exception(erro)
        
        logger_service.log_info("Template PDF baixado com sucesso")
        return response.content


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
    campos["teto_solar"] = "Sim" if dados.get("teto_solar") else "Não"
    campos["porta_malas"] = "Sim" if dados.get("abertura_porta_malas") else "Não"
    campos["tipo_documentacao"] = dados.get("tipo_documentacao", "")
    campos["pacote_revisao"] = "Sim" if dados.get("pacote_revisao") else "Não"
    campos["vidro_10_anos"] = "Sim" if dados.get("vidro_10_anos") else "Não"
    campos["vidro_5_anos"] = "Sim" if dados.get("vidro_5_anos") else "Não"
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
        cond = cenario.get("condicoes_pagamento", {})
        # À vista
        a_vista = cond.get("a_vista", {}).get("valor_total", 0)
        campos[f"a_vista_{sufixo}"] = f"R$ {a_vista:.2f}"
        # Total geral
        subtotal = cenario.get("subtotal", 0)
        total = subtotal - desconto_val if desconto_val else subtotal
        campos[f"total_{sufixo}"] = f"R$ {total:.2f}"
        # Parcelamentos diretos
        if "duas_vezes" in cond:
            dv = cond["duas_vezes"]
            campos[f"total_2x_{sufixo}"] = f"R$ {dv.get("valor_total", 0):.2f}"
            p = dv.get("parcelas", [])
            if len(p) >= 2:
                campos[f"primeira_parcela_2x_{sufixo}"] = f"R$ {p[0].get("valor", 0):.2f}"
                campos[f"segunda_parcela_2x_{sufixo}"] = f"R$ {p[1].get("valor", 0):.2f}"
        # Parcelamentos 3x
        if "tres_vezes" in cond:
            tv = cond["tres_vezes"]
            campos[f"total_3x_{sufixo}"] = f"R$ {tv.get("valor_total", 0):.2f}"
            campos[f"sinal_50_3x_{sufixo}"] = f"R$ {tv.get("valor_entrada", 0):.2f}"
            p = tv.get("parcelas", [])
            if len(p) >= 3:
                campos[f"primeira_parcela_3x_{sufixo}"] = f"R$ {p[0].get("valor", 0):.2f}"
                campos[f"segunda_parcela_3x_{sufixo}"] = f"R$ {p[1].get("valor", 0):.2f}"
                campos[f"terceira_parcela_3x_{sufixo}"] = f"R$ {p[2].get("valor", 0):.2f}"
        # Parcelamentos 4x
        if "quatro_vezes" in cond:
            qv = cond["quatro_vezes"]
            campos[f"total_4x_{sufixo}"] = f"R$ {qv.get("valor_total", 0):.2f}"
            campos[f"sinal_60_4x_{sufixo}"] = f"R$ {qv.get("valor_entrada", 0):.2f}"
            p = qv.get("parcelas", [])
            if len(p) >= 4:
                campos[f"primeira_parcela_4x_{sufixo}"] = f"R$ {p[0].get("valor", 0):.2f}"
                campos[f"segunda_parcela_4x_{sufixo}"] = f"R$ {p[1].get("valor", 0):.2f}"
                campos[f"terceira_parcela_4x_{sufixo}"] = f"R$ {p[2].get("valor", 0):.2f}"
                campos[f"quarta_parcela_4x_{sufixo}"] = f"R$ {p[3].get("valor", 0):.2f}"
        # Cartão de crédito
        for key, info in cond.get("cartao", {}).items():
            try:
                n = int(key.replace("x", ""))
            except:
                continue
            campos[f"cartao_{n}_parcelas_{sufixo}"] = f"R$ {info.get("valor_parcela", 0):.2f}"
    return campos


async def preencher_formulario_pdf(template_bytes: bytes, campos: Dict[str, Any]) -> bytes:
    """Preenche os campos do formulário usando uma camada de overlay com reportlab, mapeando campos por página."""
    logger_service.log_info(f"Iniciando preenchimento inteligente de {len(campos)} campos no PDF")

    # Salvar template em arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_in:
        tmp_in.write(template_bytes)
        input_path = tmp_in.name
    
    # Define campos por página - baseado nas imagens do template
    # Página 1 - Dados pessoais e informações do veículo
    page_1_fields = {
        # Campos de identificação (primeira página)
        'nome_cliente': (400, 345),  # Coordenadas ajustadas conforme imagem
        'telefone_cliente': (400, 310), 
        'email_cliente': (400, 273),
        'marca_carro': (400, 237),
        'modelo_carro': (400, 200),
        'teto_solar': (400, 163),
        'porta_malas': (400, 125),
        'tipo_documentacao': (400, 88),
    }
    
    # Página 2 - Tabela de valores
    page_2_fields = {
        # Coluna 1 - Comfort 10 anos
        'a_vista_10_anos': (140, 95),     # À vista
        'total_10_anos': (140, 150),      # Total geral
        'total_2x_10_anos': (140, 205),   # Total 2x
        'primeira_parcela_2x_10_anos': (140, 240),
        'segunda_parcela_2x_10_anos': (140, 275),
        'total_3x_10_anos': (140, 327),   # Total 3x 
        'sinal_50_3x_10_anos': (140, 362),
        'primeira_parcela_3x_10_anos': (140, 397),
        'segunda_parcela_3x_10_anos': (140, 432),
        'terceira_parcela_3x_10_anos': (140, 467),
        'total_4x_10_anos': (140, 522),
        'sinal_60_4x_10_anos': (140, 559),
        'primeira_parcela_4x_10_anos': (140, 594),
        'segunda_parcela_4x_10_anos': (140, 629),
        'terceira_parcela_4x_10_anos': (140, 664),
        'quarta_parcela_4x_10_anos': (140, 699),
        
        # Coluna 2 - Comfort 18mm
        'a_vista_18mm': (295, 95),
        'total_18mm': (295, 150),
        'total_2x_18mm': (295, 205),
        'primeira_parcela_2x_18mm': (295, 240),
        'segunda_parcela_2x_18mm': (295, 275),
        'total_3x_18mm': (295, 327),
        'sinal_50_3x_18mm': (295, 362),
        'primeira_parcela_3x_18mm': (295, 397),
        'segunda_parcela_3x_18mm': (295, 432),
        'terceira_parcela_3x_18mm': (295, 467),
        'total_4x_18mm': (295, 522),
        'sinal_60_4x_18mm': (295, 559),
        'primeira_parcela_4x_18mm': (295, 594),
        'segunda_parcela_4x_18mm': (295, 629),
        'terceira_parcela_4x_18mm': (295, 664),
        'quarta_parcela_4x_18mm': (295, 699),
        
        # Coluna 3 - Ultralight
        'a_vista_ultralight': (450, 95),
        'total_ultralight': (450, 150),
        'total_2x_ultralight': (450, 205),
        'primeira_parcela_2x_ultralight': (450, 240),
        'segunda_parcela_2x_ultralight': (450, 275),
        'total_3x_ultralight': (450, 327),
        'sinal_50_3x_ultralight': (450, 362),
        'primeira_parcela_3x_ultralight': (450, 397),
        'segunda_parcela_3x_ultralight': (450, 432),
        'terceira_parcela_3x_ultralight': (450, 467),
        'total_4x_ultralight': (450, 522),
        'sinal_60_4x_ultralight': (450, 559),
        'primeira_parcela_4x_ultralight': (450, 594),
        'segunda_parcela_4x_ultralight': (450, 629),
        'terceira_parcela_4x_ultralight': (450, 664),
        'quarta_parcela_4x_ultralight': (450, 699),
    }

    # Página 3 - Cartão de Crédito
    page_3_fields = {
        # Cartão Coluna 1
        'cartao_4_parcelas_10_anos': (140, 850),
        'cartao_5_parcelas_10_anos': (140, 815),
        'cartao_6_parcelas_10_anos': (140, 780),
        'cartao_7_parcelas_10_anos': (140, 745), 
        'cartao_8_parcelas_10_anos': (140, 710),
        'cartao_9_parcelas_10_anos': (140, 675),
        'cartao_10_parcelas_10_anos': (140, 640),
        
        # Cartão Coluna 2
        'cartao_4_parcelas_18mm': (295, 850),
        'cartao_5_parcelas_18mm': (295, 815),
        'cartao_6_parcelas_18mm': (295, 780),
        'cartao_7_parcelas_18mm': (295, 745),
        'cartao_8_parcelas_18mm': (295, 710),
        'cartao_9_parcelas_18mm': (295, 675),
        'cartao_10_parcelas_18mm': (295, 640),
        
        # Cartão Coluna 3
        'cartao_4_parcelas_ultralight': (450, 850),
        'cartao_5_parcelas_ultralight': (450, 815),
        'cartao_6_parcelas_ultralight': (450, 780),
        'cartao_7_parcelas_ultralight': (450, 745),
        'cartao_8_parcelas_ultralight': (450, 710),
        'cartao_9_parcelas_ultralight': (450, 675),
        'cartao_10_parcelas_ultralight': (450, 640)
    }
    
    # Mapeia campos por página
    pages_fields_map = {
        0: page_1_fields,  # Página 1 (índice 0)
        1: page_2_fields,  # Página 2 (índice 1) 
        2: page_3_fields,  # Página 3 (índice 2)
    }
    
    # Informações do PDF
    reader = PdfReader(input_path)
    num_pages = len(reader.pages)
    logger_service.log_info(f"PDF possui {num_pages} páginas")
    
    # Criar arquivos temporários para cada página
    page_files = []
    campos_preenchidos = 0
    
    # Processar cada página do PDF
    for page_num in range(num_pages):
        # Verificar se temos campos mapeados para esta página
        if page_num not in pages_fields_map:
            # Copiar página sem alterações
            page = reader.pages[page_num]
            page_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_page_{page_num}.pdf")
            page_files.append(page_file.name)
            page_writer = PdfWriter()
            page_writer.add_page(page)
            with open(page_file.name, 'wb') as f:
                page_writer.write(f)
            logger_service.log_info(f"Página {page_num+1} copiada sem alterações (sem campos mapeados)")
            continue
        
        # Obter campos mapeados para esta página
        page_fields = pages_fields_map[page_num]
        
        # Usar reportlab para criar camada de texto
        packet = io.BytesIO()
        
        # Obter dimensões da página original
        page = reader.pages[page_num]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        
        # Criar canvas para desenhar texto
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont("Helvetica", 11)  # Fonte um pouco maior para visibilidade
        
        # Campos preenchidos nesta página
        page_campos_count = 0
        
        # Desenhar texto nos campos relevantes para esta página
        for field_name, value in campos.items():
            if field_name in page_fields and value is not None:
                # Obter posição do campo
                x, y = page_fields[field_name]
                
                # Converter para string se necessário
                if not isinstance(value, str):
                    value = str(value)
                
                # Desenhar o texto na posição especificada
                c.drawString(x, y, value)
                page_campos_count += 1
                campos_preenchidos += 1
                logger_service.log_info(f"Página {page_num+1}: Campo '{field_name}' = '{value}' na posição ({x}, {y})")
        
        c.save()
        packet.seek(0)
        
        # Criar temporário para página
        overlay = PdfReader(packet)
        page_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_page_{page_num}.pdf")
        page_files.append(page_file.name)
        
        # Mesclar camada de texto com a página original
        overlay_page = overlay.pages[0]
        page.merge_page(overlay_page)
        
        # Criar novo writer para esta página
        page_writer = PdfWriter()
        page_writer.add_page(page)
        
        # Salvar página com overlay
        with open(page_file.name, 'wb') as f:
            page_writer.write(f)
            
        logger_service.log_info(f"Página {page_num+1} processada com {page_campos_count} campos")
    
    # Combinar todas as páginas em um único PDF
    output = io.BytesIO()
    merger_writer = PdfWriter()
    
    for page_file in page_files:
        page_reader = PdfReader(page_file)
        merger_writer.add_page(page_reader.pages[0])
    
    merger_writer.write(output)
    output.seek(0)
    result = output.read()
    
    # Limpar arquivos temporários
    os.remove(input_path)
    for page_file in page_files:
        os.remove(page_file)
    
    logger_service.log_info(f"PDF preenchido com sucesso ({campos_preenchidos} campos no total)")
    return result


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
        template_url = await selecionar_template(desconto)
        
        # Baixar o template
        template_bytes = await baixar_template(template_url)
        
        # Mapear dados para os campos do formulário
        campos_preenchidos = await mapear_dados_para_formulario(dados)
        
        # Preencher os campos no PDF
        pdf_preenchido = await preencher_formulario_pdf(template_bytes, campos_preenchidos)
        
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
