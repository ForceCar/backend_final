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
PDF_COM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-com-desconto//proposta-force-com-descconto.pdf"
PDF_SEM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/proposta-forcecar-sem-desconto//proposta-force-sem-desconto.pdf"

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
        # Preços
        campos[f"modelo_{sufixo}"] = nome_c
        campos[f"preco_original_{sufixo}"] = f"R$ {cenario.get('preco_original', 0):.2f}"
        campos[f"preco_final_{sufixo}"] = f"R$ {cenario.get('preco_final', 0):.2f}"
        
        # Condições de pagamento
        cond_pagto = cenario.get("condicoes_pagamento", {})
        
        # À vista
        a_vista = cond_pagto.get("a_vista", {})
        campos[f"valor_avista_{sufixo}"] = f"R$ {a_vista.get('valor', 0):.2f}"
        
        # Entrada + parcelas
        entrada_parcelas = cond_pagto.get("entrada_parcelas", {})
        campos[f"valor_entrada_{sufixo}"] = f"R$ {entrada_parcelas.get('valor_entrada', 0):.2f}"
        campos[f"valor_parcela_{sufixo}"] = f"R$ {entrada_parcelas.get('valor_parcela', 0):.2f}"
        campos[f"num_parcelas_{sufixo}"] = str(entrada_parcelas.get("num_parcelas", 0))
        
        # Parcelas sem entrada
        sem_entrada = cond_pagto.get("sem_entrada", {})
        campos[f"valor_parcela_sem_entrada_{sufixo}"] = f"R$ {sem_entrada.get('valor_parcela', 0):.2f}"
        campos[f"num_parcelas_sem_entrada_{sufixo}"] = str(sem_entrada.get("num_parcelas", 0))
    
    # Contagem de campos preenchidos para log
    campos_preenchidos = len([k for k, v in campos.items() if v])
    logger_service.log_info(f"Dados mapeados para formulário PDF: {campos_preenchidos} campos preenchidos")
    
    return campos


# Mapeamento de coordenadas para preenchimento de campos no PDF
COORDINATE_MAP: Dict[str, Dict[str, Any]] = {
    # Página 11 - Dados do cliente e veículo
    "nome_cliente": {"page": 11, "x": 100, "y": 700},
    "telefone_cliente": {"page": 11, "x": 300, "y": 700},
    "email_cliente": {"page": 11, "x": 100, "y": 670},
    "marca_carro": {"page": 11, "x": 300, "y": 670},
    "modelo_carro": {"page": 11, "x": 100, "y": 640},
    "teto_solar": {"page": 11, "x": 300, "y": 640},
    "porta_malas": {"page": 11, "x": 100, "y": 610},
    "tipo_documentacao": {"page": 11, "x": 300, "y": 610},
    "pacote_revisao": {"page": 11, "x": 100, "y": 580},
    "vidro_10_anos": {"page": 11, "x": 300, "y": 580},
    "vidro_5_anos": {"page": 11, "x": 100, "y": 550},
    "desconto": {"page": 11, "x": 300, "y": 550},
    
    # Página 11 - Opção Comfort 10 anos
    "modelo_10_anos": {"page": 11, "x": 100, "y": 500},
    "preco_original_10_anos": {"page": 11, "x": 300, "y": 500},
    "preco_final_10_anos": {"page": 11, "x": 100, "y": 470},
    "valor_avista_10_anos": {"page": 11, "x": 300, "y": 470},
    "valor_entrada_10_anos": {"page": 11, "x": 100, "y": 440},
    "valor_parcela_10_anos": {"page": 11, "x": 300, "y": 440},
    "num_parcelas_10_anos": {"page": 11, "x": 100, "y": 410},
    "valor_parcela_sem_entrada_10_anos": {"page": 11, "x": 300, "y": 410},
    "num_parcelas_sem_entrada_10_anos": {"page": 11, "x": 100, "y": 380},
    
    # Página 12 - Opção Comfort 18mm
    "modelo_18mm": {"page": 12, "x": 100, "y": 700},
    "preco_original_18mm": {"page": 12, "x": 300, "y": 700},
    "preco_final_18mm": {"page": 12, "x": 100, "y": 670},
    "valor_avista_18mm": {"page": 12, "x": 300, "y": 670},
    "valor_entrada_18mm": {"page": 12, "x": 100, "y": 640},
    "valor_parcela_18mm": {"page": 12, "x": 300, "y": 640},
    "num_parcelas_18mm": {"page": 12, "x": 100, "y": 610},
    "valor_parcela_sem_entrada_18mm": {"page": 12, "x": 300, "y": 610},
    "num_parcelas_sem_entrada_18mm": {"page": 12, "x": 100, "y": 580},
    
    # Página 12 - Opção Ultralight
    "modelo_ultralight": {"page": 12, "x": 100, "y": 500},
    "preco_original_ultralight": {"page": 12, "x": 300, "y": 500},
    "preco_final_ultralight": {"page": 12, "x": 100, "y": 470},
    "valor_avista_ultralight": {"page": 12, "x": 300, "y": 470},
    "valor_entrada_ultralight": {"page": 12, "x": 100, "y": 440},
    "valor_parcela_ultralight": {"page": 12, "x": 300, "y": 440},
    "num_parcelas_ultralight": {"page": 12, "x": 100, "y": 410},
    "valor_parcela_sem_entrada_ultralight": {"page": 12, "x": 300, "y": 410},
    "num_parcelas_sem_entrada_ultralight": {"page": 12, "x": 100, "y": 380},
}

async def preencher_formulario_pdf(template_bytes: bytes, campos: Dict[str, Any]) -> bytes:
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
                
            coord = COORDINATE_MAP.get(field)
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
                    x, y = float(coord.get("x")), float(coord.get("y"))
                    overlay_canvas.setFillColorRGB(0, 0, 0.8)  # Azul escuro
                    overlay_canvas.drawString(x, y, str(value))
                    logger_service.log_info(f"Campo '{field}': '{value}' em ({x},{y}) na página {page_num}")
                
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
