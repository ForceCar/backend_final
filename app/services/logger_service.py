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
    # Log completo dos dados brutos recebidos em formato de tabela (excluindo cenários)
    raw_req = {k: v for k, v in request_data.items() if k != "cenarios"}
    logger.info("\n" + format_dict_table(raw_req))
    
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
    """Registra que os dados foram salvos com sucesso, mostrando apenas as informações essenciais"""
    
    # Registra que os dados foram salvos
    if "nome_cliente" in request_data:
        nome_cliente = request_data["nome_cliente"]
        logger.info(f"Dados da proposta salvos com sucesso - Cliente: {nome_cliente}")
    else:
        logger.info(f"Dados da proposta salvos com sucesso")
    
    # Exibir dados básicos recebidos sem cenários
    raw_data = {k: v for k, v in request_data.items() if k != "cenarios"}
    logger.info("DADOS RECEBIDOS (sem cenários de pagamento):")
    logger.info("\n" + format_dict_table(raw_data))
    
    # Exibir apenas o cenário relevante com formato simplificado
    cenarios = request_data.get("cenarios", {})
    tipo = request_data.get("tipo_blindagem")
    
    if tipo and tipo != "Nenhuma":
        cenario = cenarios.get(tipo, {})
        if cenario:
            subtotal = cenario.get("subtotal", 0)
            desconto = cenario.get("desconto_aplicado", 0)
            condicoes = cenario.get("condicoes_pagamento", {})
            
            logger.info(f"CONDIÇÕES DE PAGAMENTO - {tipo.upper()}:")
            logger.info(f"Valor Base: R$ {subtotal:,.2f}")
            if desconto > 0:
                logger.info(f"Desconto Aplicado: R$ {desconto:,.2f}")
                logger.info(f"Valor Base com Desconto: R$ {subtotal - desconto:,.2f}")
                
            # À vista
            if "a_vista" in condicoes:
                av = condicoes["a_vista"]
                logger.info(f"1) À VISTA: R$ {av.get('valor_total', 0):,.2f} (2% de desconto)")
            
            # 2 parcelas
            if "duas_vezes" in condicoes:
                dv = condicoes["duas_vezes"]
                parcelas = dv.get("parcelas", [])
                if len(parcelas) >= 2:
                    valor_parcela = parcelas[0].get("valor", 0)
                    logger.info(f"2) 2X SEM JUROS: 2x de R$ {valor_parcela:,.2f}")
            
            # 3 parcelas
            if "tres_vezes" in condicoes:
                tv = condicoes["tres_vezes"]
                parcelas = tv.get("parcelas", [])
                if len(parcelas) >= 3:
                    entrada = parcelas[0].get("valor", 0)
                    valor_parcela = parcelas[1].get("valor", 0)
                    logger.info(f"3) 3X: Entrada de R$ {entrada:,.2f} + 2x de R$ {valor_parcela:,.2f} (1% de acréscimo)")
            
            # 4 parcelas
            if "quatro_vezes" in condicoes:
                qv = condicoes["quatro_vezes"]
                parcelas = qv.get("parcelas", [])
                if len(parcelas) >= 4:
                    entrada = parcelas[0].get("valor", 0)
                    valor_parcela = parcelas[1].get("valor", 0)
                    logger.info(f"4) 4X: Entrada de R$ {entrada:,.2f} + 3x de R$ {valor_parcela:,.2f} (3% de acréscimo)")
            
            # Cartão
            logger.info("5) PAGAMENTO NO CARTÃO:")
            for parcela, info in condicoes.get("cartao", {}).items():
                valor_parcela = info.get("valor_parcela", 0)
                acrescimo = info.get("acrescimo", 0)
                logger.info(f"   {parcela.upper()}: R$ {valor_parcela:,.2f} ({acrescimo}% de acréscimo)")
    
    elif tipo == "Nenhuma":
        logger.info("COMPARATIVO DE BLINDAGENS:")
        for t in ["Comfort 10 anos", "Comfort 18 mm", "Ultralight"]:
            cenario = cenarios.get(t, {})
            if cenario:
                subtotal = cenario.get("subtotal", 0)
                desconto = cenario.get("desconto_aplicado", 0)
                valor_final = subtotal - desconto
                logger.info(f"{t}: R$ {subtotal:,.2f} - Desconto: R$ {desconto:,.2f} = R$ {valor_final:,.2f}")
    
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
            # Calcular subtotais líquidos considerando desconto
            comfort10_bruto = request_data.get("comfort10YearsSubTotal", 0)
            comfort10_desconto = request_data.get("comfort10YearsDiscount", 0)
            proposal_data["comfort_10_anos_sub_total"] = comfort10_bruto - comfort10_desconto
            proposal_data["comfort_10_anos_desconto"] = comfort10_desconto
            comfort18_bruto = request_data.get("comfort18mmSubTotal", 0)
            comfort18_desconto = request_data.get("comfort18mmDiscount", 0)
            proposal_data["comfort_18mm_sub_total"] = comfort18_bruto - comfort18_desconto
            proposal_data["comfort_18mm_desconto"] = comfort18_desconto
            ultralight_bruto = request_data.get("ultralightSubTotal", 0)
            ultralight_desconto = request_data.get("ultralightDiscount", 0)
            proposal_data["ultralight_sub_total"] = ultralight_bruto - ultralight_desconto
            proposal_data["ultralight_desconto"] = ultralight_desconto
            
            # Registrar informações de comparação das blindagens
            logger.info("COMPARAÇÃO DE BLINDAGENS:")
            logger.info(f"  - Comfort 10 anos: R$ {proposal_data['comfort_10_anos_sub_total']:,.2f} (Desconto: R$ {proposal_data['comfort_10_anos_desconto']:,.2f})")
            logger.info(f"  - Comfort 18 mm: R$ {proposal_data['comfort_18mm_sub_total']:,.2f} (Desconto: R$ {proposal_data['comfort_18mm_desconto']:,.2f})")
            logger.info(f"  - Ultralight: R$ {proposal_data['ultralight_sub_total']:,.2f} (Desconto: R$ {proposal_data['ultralight_desconto']:,.2f})")
            
        elif tipo_blindagem == "Comfort 10 anos":
            # Para 'Comfort 10 anos', registramos apenas os valores dessa opção
            # Calcular subtotal líquido considerando desconto
            bruto = request_data.get("comfort10YearsSubTotal", 0)
            desconto = request_data.get("comfort10YearsDiscount", 0)
            proposal_data["sub_total_blindagem"] = bruto - desconto
            proposal_data["desconto_blindagem"] = desconto
            logger.info(f"DETALHES DE BLINDAGEM COMFORT 10 ANOS:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
            
        elif tipo_blindagem == "Comfort 18 mm":
            # Para 'Comfort 18 mm', registramos apenas os valores dessa opção
            # Calcular subtotal líquido considerando desconto
            bruto = request_data.get("comfort18mmSubTotal", 0)
            desconto = request_data.get("comfort18mmDiscount", 0)
            proposal_data["sub_total_blindagem"] = bruto - desconto
            proposal_data["desconto_blindagem"] = desconto
            logger.info(f"DETALHES DE BLINDAGEM COMFORT 18MM:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
            
        elif tipo_blindagem == "Ultralight":
            # Para 'Ultralight', registramos apenas os valores dessa opção
            # Calcular subtotal líquido considerando desconto
            bruto = request_data.get("ultralightSubTotal", 0)
            desconto = request_data.get("ultralightDiscount", 0)
            proposal_data["sub_total_blindagem"] = bruto - desconto
            proposal_data["desconto_blindagem"] = desconto
            logger.info(f"DETALHES DE BLINDAGEM ULTRALIGHT:")
            logger.info(f"  - Subtotal: R$ {proposal_data['sub_total_blindagem']:,.2f}")
            logger.info(f"  - Desconto: R$ {proposal_data['desconto_blindagem']:,.2f}")
        
        # Log dos dados processados da proposta
        logger.info("DADOS PROCESSADOS DA PROPOSTA:")
        logger.info("\n" + format_dict_table(proposal_data))
    
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


def format_dict_table(data: dict, indent=0) -> str:
    """Formata dicionário como tabela para log com melhor suporte para estruturas aninhadas."""
    if not data:
        return ""
    
    indent_str = " " * indent
    max_key = max(len(str(k)) for k in data.keys())
    
    lines = []
    for k, v in data.items():
        key_str = f"{indent_str}{str(k).ljust(max_key)}"
        
        # Formatação especial para tipos específicos
        if isinstance(v, dict):
            if len(v) > 0:
                # Para dicionários pequenos e simples, tente uma linha única
                if len(v) <= 3 and all(not isinstance(val, (dict, list)) for val in v.values()):
                    simple_dict = ", ".join(f"{sk}:{sv}" for sk, sv in v.items())
                    lines.append(f"{key_str} : {{{simple_dict}}}")
                else:
                    # Para dicionários complexos, mostra um por linha com indentação
                    lines.append(f"{key_str} :")
                    for sub_k, sub_v in v.items():
                        sub_indent = indent + 4
                        if isinstance(sub_v, dict):
                            lines.append(f"{indent_str}    {sub_k}:")
                            for s_line in format_dict_table(sub_v, sub_indent + 4).split("\n"):
                                if s_line.strip():
                                    lines.append(s_line)
                        elif isinstance(sub_v, list):
                            lines.append(f"{indent_str}    {sub_k}:")
                            for i, item in enumerate(sub_v):
                                if isinstance(item, dict):
                                    lines.append(f"{indent_str}        Item {i+1}:")
                                    for s_line in format_dict_table(item, sub_indent + 8).split("\n"):
                                        if s_line.strip():
                                            lines.append(s_line)
                                else:
                                    lines.append(f"{indent_str}        - {item}")
                        else:
                            lines.append(f"{indent_str}    {sub_k}: {sub_v}")
            else:
                lines.append(f"{key_str} : {{}}")
        elif isinstance(v, list):
            if len(v) > 0:
                if all(not isinstance(item, (dict, list)) for item in v):
                    # Lista simples
                    list_str = ", ".join(str(item) for item in v)
                    lines.append(f"{key_str} : [{list_str}]")
                else:
                    # Lista complexa
                    lines.append(f"{key_str} :")
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            lines.append(f"{indent_str}    Item {i+1}:")
                            for s_line in format_dict_table(item, indent + 8).split("\n"):
                                if s_line.strip():
                                    lines.append(s_line)
                        else:
                            lines.append(f"{indent_str}    - {item}")
            else:
                lines.append(f"{key_str} : []")
        else:
            # Para tipos simples, apenas mostrar o valor
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                # Formatar números com vírgula para separadores de milhares
                try:
                    formatted_v = f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"
                    formatted_v = formatted_v.replace(",", ".")
                    lines.append(f"{key_str} : {formatted_v}")
                except:
                    lines.append(f"{key_str} : {v}")
            else:
                lines.append(f"{key_str} : {v}")
    
    return "\n".join(lines)
