"""Rotas para manipulação de propostas"""

import uuid
from datetime import datetime
from typing import Dict, Any, Union
import json  # Para serializar payload de PDF
import os
import tempfile

from fastapi import APIRouter, Request, HTTPException, Body

from app.schemas.proposta_schema import (
    PropostaResponse, 
    PropostaComfort10Anos,
    PropostaComfort18mm,
    PropostaUltralight,
    PropostaNenhuma
)
from app.services import calculos
from app.services import logger_service
from app.services import pdf_service
from app.services import whatsapp_service
from app.config import PROPOSTA_ENDPOINT
from config.form_map import (
    FORM_MAP_WITH_DESCONTO,
    FORM_MAP_SEM_DESCONTO,
    PAYMENT_CONDITIONS_MAP
)

# Criação do router
router = APIRouter()


@router.post(PROPOSTA_ENDPOINT, response_model=PropostaResponse)
async def gerar_proposta(request: Request, data: Dict[str, Any] = Body(...)):
    """Endpoint para receber dados, processar e gerar proposta."""
    try:
        # Gera um ID único para a proposta
        proposta_id = str(uuid.uuid4())
        
        # Captura o corpo bruto da requisição
        raw_body = await request.body()
        
        # Registra o corpo bruto da requisição
        logger_service.log_raw_request_body(raw_body)
        
        # Registra a requisição inicial
        nome_cliente = data.get("nome_cliente", "N/A")
        tipo_blindagem = data.get("tipo_blindagem", "N/A")
        
        # Log inicial
        logger_service.log_info(f"=== INICIANDO PROCESSAMENTO DE NOVA REQUISIÇÃO ====")
        logger_service.log_info(f"Requisição recebida - Cliente: {nome_cliente} | Tipo blindagem: {tipo_blindagem}")
        
        # Calcula os subtotais com base no tipo de blindagem
        subtotais = calculos.calcular_subtotais_blindagem(data)
        
        # Calcula as condições de pagamento
        logger_service.log_info("Calculando condições de pagamento...")
        condicoes_pagamento = calculos.calcular_condicoes_pagamento(subtotais)
        
        valor_base = subtotais.get("valor_base", 0)
        logger_service.log_info(f"Cálculos de pagamento concluídos para valor base: R$ {valor_base:.2f}")
        
        # Loga as comparações de blindagens e condições de pagamento
        if tipo_blindagem == "Nenhuma":
            logger_service.log_info("COMPARAÇÃO DE BLINDAGENS:")
            logger_service.log_info(f"  - Comfort 10 anos: R$ {subtotais['comfort10_anos']['subtotal']:.2f}" + 
                                   f" (Desconto: R$ {subtotais['desconto_aplicado']:.2f})")
            logger_service.log_info(f"  - Comfort 18 mm: R$ {subtotais['comfort18mm']['subtotal']:.2f}" + 
                                   f" (Desconto: R$ {subtotais['desconto_aplicado']:.2f})")
            logger_service.log_info(f"  - Ultralight: R$ {subtotais['ultralight']['subtotal']:.2f}" + 
                                   f" (Desconto: R$ {subtotais['desconto_aplicado']:.2f})")
            
            # Log detalhado para cada cenário de blindagem em 'Nenhuma'
            for key, label in [("comfort10_anos", "Comfort 10 anos"), ("comfort18mm", "Comfort 18 mm"), ("ultralight", "Ultralight")]:
                valor = subtotais[key]["valor_final"]
                conds = calculos.calcular_condicoes_pagamento({"valor_base": valor})
                logger_service.log_info(f"=== Cálculos para {label} ===")
                logger_service.log_info("DETALHES DAS CONDIÇÕES DE PAGAMENTO:")
                logger_service.log_info(f"  - À vista: R$ {conds['a_vista']['valor_total']:.2f} (Desconto: {conds['a_vista']['desconto_percentual']}%)")
                logger_service.log_info(f"  - 2x sem juros: {conds['duas_vezes']['parcelas'][0]['valor']:.2f} + {conds['duas_vezes']['parcelas'][1]['valor']:.2f}")
                logger_service.log_info(f"  - 3x: Entrada de R$ {conds['tres_vezes']['parcelas'][0]['valor']:.2f} + 2x de R$ {conds['tres_vezes']['parcelas'][1]['valor']:.2f} (Acréscimo: {conds['tres_vezes']['acrescimo_percentual']}%)")
                logger_service.log_info(f"  - 4x: Entrada de R$ {conds['quatro_vezes']['parcelas'][0]['valor']:.2f} + 3x de R$ {conds['quatro_vezes']['parcelas'][1]['valor']:.2f} (Acréscimo: {conds['quatro_vezes']['acrescimo_percentual']}%)")
                logger_service.log_info("  - Opções de cartão:")
                for parcela, info in conds['cartao'].items():
                    valor_parcela = info.get('valor_parcela', 0)
                    valor_total = info.get('valor_total', 0)
                    acrescimo = info.get('acrescimo', 0)
                    logger_service.log_info(f"    * {parcela}: R$ {valor_parcela:.2f} (Total: R$ {valor_total:.2f}, Acréscimo: {acrescimo}%)")
        
        # Se houver um valor base (tipo de blindagem escolhido), loga detalhes das condições de pagamento
        if valor_base > 0:
            logger_service.log_info("DETALHES DAS CONDIÇÕES DE PAGAMENTO:")
            
            # À vista
            logger_service.log_info(f"  - À vista: R$ {condicoes_pagamento['a_vista']['valor_total']:.2f}" +
                                   f" (Desconto: {condicoes_pagamento['a_vista']['desconto_percentual']}%)")
            
            # Parcelado
            logger_service.log_info(f"  - 2x sem juros: {condicoes_pagamento['duas_vezes']['parcelas'][0]['valor']:.2f} + " +
                                   f"{condicoes_pagamento['duas_vezes']['parcelas'][1]['valor']:.2f}")
                               
            logger_service.log_info(f"  - 3x: Entrada de R$ {condicoes_pagamento['tres_vezes']['parcelas'][0]['valor']:.2f} + " +
                                   f"2x de R$ {condicoes_pagamento['tres_vezes']['parcelas'][1]['valor']:.2f}" +
                                   f" (Acréscimo: {condicoes_pagamento['tres_vezes']['acrescimo_percentual']}%)")
                               
            logger_service.log_info(f"  - 4x: Entrada de R$ {condicoes_pagamento['quatro_vezes']['parcelas'][0]['valor']:.2f} + " +
                                   f"3x de R$ {condicoes_pagamento['quatro_vezes']['parcelas'][1]['valor']:.2f}" +
                                   f" (Acréscimo: {condicoes_pagamento['quatro_vezes']['acrescimo_percentual']}%)")
            
            # Cartão
            logger_service.log_info("  - Opções de cartão:")
            for parcela, info in condicoes_pagamento["cartao"].items():
                try:
                    valor_parcela = info.get("valor_parcela", 0)
                    valor_total = info.get("valor_total", 0)
                    acrescimo = info.get("acrescimo", 0)
                    logger_service.log_info(f"    * {parcela}: R$ {valor_parcela:.2f} " +
                                           f"(Total: R$ {valor_total:.2f}, Acréscimo: {acrescimo}%)")
                except Exception as e:
                    logger_service.log_warning(f"Erro ao processar informações de cartão para {parcela}: {str(e)}")
        
        # Prepara resposta final
        logger_service.log_info("Preparando resposta final da proposta...")
        
        if tipo_blindagem == "Nenhuma":
            # Propostas completas para cada blindagem em comparação
            proposals = {}
            for key, label in [("comfort10_anos", "Comfort 10 anos"), ("comfort18mm", "Comfort 18 mm"), ("ultralight", "Ultralight")]:
                valor = subtotais[key]["valor_final"]
                conds = calculos.calcular_condicoes_pagamento({"valor_base": valor})
                conds["valor_base"] = valor
                conds["parcelado_direto"] = [
                    conds["duas_vezes"],
                    conds["tres_vezes"],
                    conds["quatro_vezes"],
                ]
                conds["parcelado_cartao"] = list(conds["cartao"].values())
                proposals[label] = conds
            condicoes_pagamento = proposals
        else:
            # Ajusta estrutura conforme CondicoesPagamento schema
            condicoes_pagamento["valor_base"] = valor_base
            condicoes_pagamento["parcelado_direto"] = [
                condicoes_pagamento["duas_vezes"],
                condicoes_pagamento["tres_vezes"],
                condicoes_pagamento["quatro_vezes"],
            ]
            condicoes_pagamento["parcelado_cartao"] = list(condicoes_pagamento["cartao"].values())
        
        # --- Salvar dados para PDF ---
        logger_service.log_info("Salvando dados para PDF...")
        backend_data = {}
        # Campos básicos
        for field in [
            'nome_cliente','telefone_cliente','email_cliente','nome_vendedor',
            'marca_veiculo','modelo_veiculo','teto_solar','abertura_porta_malas',
            'tipo_documentacao','pacote_revisao','vidro_10_anos','vidro_5_anos',
            'tipo_blindagem','desconto_aplicado','observations'
        ]:
            if field in data:
                backend_data[field] = data[field]
                
        # Cenários de blindagem - SIMPLIFICADO para evitar duplicações
        backend_data['cenarios'] = {}
        
        if tipo_blindagem == "Nenhuma":
            # Para comparação, incluir apenas um cenário por tipo de blindagem
            for label, key in [("Comfort 10 anos", "comfort10_anos"), 
                              ("Comfort 18 mm", "comfort18mm"), 
                              ("Ultralight", "ultralight")]:
                # Usar valores já calculados com desconto aplicado
                valor_final = subtotais[key]['valor_final']
                
                # O valor de condicoes_pagamento já calculado no proposals contém o desconto
                scenario = {
                    'subtotal': subtotais[key]['subtotal'],
                    'condicoes_pagamento': condicoes_pagamento[label]
                }
                
                # Se houver desconto, incluir no cenário para documentação
                desconto = subtotais.get('desconto_aplicado', 0)
                if desconto > 0:
                    scenario['desconto_aplicado'] = desconto
                    
                backend_data['cenarios'][label] = scenario
        else:
            # Para um tipo específico de blindagem, usar valor_base que já contém desconto
            valor_base = subtotais['valor_base']
            
            # Identificar o subtotal original sem desconto
            subtotal_map = {
                'Comfort 10 anos': 'comfort10YearsSubTotal',
                'Comfort 18 mm': 'comfort18mmSubTotal',
                'Ultralight': 'ultralightSubTotal'
            }
            subtotal = float(data.get(subtotal_map.get(tipo_blindagem, ''), 0))
            
            # Criar cenário único com condições de pagamento já calculadas
            scenario = {
                'subtotal': subtotal,
                'condicoes_pagamento': condicoes_pagamento
            }
            
            # Se houver desconto, incluir no cenário
            desconto = data.get('desconto_aplicado', 0)
            if desconto > 0:
                scenario['desconto_aplicado'] = desconto
                
            backend_data['cenarios'][tipo_blindagem] = scenario
            
        # Log payload para PDF em formato de tabela
        logger_service.log_info("Dados para PDF:")
        # Campos básicos
        basic = {k: v for k, v in backend_data.items() if k != 'cenarios'}
        logger_service.log_info(logger_service.format_dict_table(basic))
        
        # Preparar dados para o formulário PDF usando os mapeamentos
        form_map = (FORM_MAP_WITH_DESCONTO if data.get("desconto_aplicado", 0) > 0 else FORM_MAP_SEM_DESCONTO).copy()
        form_map.update(PAYMENT_CONDITIONS_MAP)
        
        # Converter dados do backend para o formato dos campos do formulário PDF
        form_data = {pdf_field: str(backend_data.get(key, "")) for key, pdf_field in form_map.items() if key in backend_data}
        
        # Adicionar dados específicos de cenários
        for nome_cenario, cenario in backend_data.get('cenarios', {}).items():
            suffix_map = {"Comfort 10 anos": "10_anos", "Comfort 18 mm": "18mm", "Ultralight": "ultralight"}
            sufixo = suffix_map.get(nome_cenario)
            if not sufixo:
                continue
                
            cond_pagto = cenario.get('condicoes_pagamento', {})
            
            # À vista
            a_v = cond_pagto.get('a_vista', {})
            if 'valor_total' in a_v:
                form_data[form_map.get(f"a_vista_{sufixo}", "")] = f"R$ {a_v.get('valor_total', 0):.2f}"
                form_data[form_map.get(f"total_{sufixo}", "")] = f"R$ {a_v.get('valor_total', 0):.2f}"
            
            # 2x sem juros
            duas = cond_pagto.get('duas_vezes', {})
            parcelas2 = duas.get('parcelas', [])
            if len(parcelas2) >= 2:
                form_data[form_map.get(f"primeira_parcela_2x_{sufixo}", "")] = f"R$ {parcelas2[0].get('valor', 0):.2f}"
                form_data[form_map.get(f"segunda_parcela_2x_{sufixo}", "")] = f"R$ {parcelas2[1].get('valor', 0):.2f}"
            if 'valor_total' in duas:
                form_data[form_map.get(f"total_2x_{sufixo}", "")] = f"R$ {duas.get('valor_total', 0):.2f}"
            
            # 3x
            tres = cond_pagto.get('tres_vezes', {})
            parcelas3 = tres.get('parcelas', [])
            if len(parcelas3) >= 1:
                form_data[form_map.get(f"sinal_50_3x_{sufixo}", "")] = f"R$ {parcelas3[0].get('valor', 0):.2f}"
            if len(parcelas3) >= 2:
                form_data[form_map.get(f"primeira_parcela_3x_{sufixo}", "")] = f"R$ {parcelas3[1].get('valor', 0):.2f}"
            if len(parcelas3) >= 3:
                form_data[form_map.get(f"segunda_parcela_3x_{sufixo}", "")] = f"R$ {parcelas3[2].get('valor', 0):.2f}"
                form_data[form_map.get(f"terceira_parcela_3x_{sufixo}", "")] = f"R$ {parcelas3[2].get('valor', 0):.2f}"
            if 'valor_total' in tres:
                form_data[form_map.get(f"total_3x_{sufixo}", "")] = f"R$ {tres.get('valor_total', 0):.2f}"
            
            # 4x
            quatro = cond_pagto.get('quatro_vezes', {})
            parcelas4 = quatro.get('parcelas', [])
            if len(parcelas4) >= 1:
                form_data[form_map.get(f"sinal_60_4x_{sufixo}", "")] = f"R$ {parcelas4[0].get('valor', 0):.2f}"
            if len(parcelas4) >= 2:
                form_data[form_map.get(f"primeira_parcela_4x_{sufixo}", "")] = f"R$ {parcelas4[1].get('valor', 0):.2f}"
            if len(parcelas4) >= 3:
                form_data[form_map.get(f"segunda_parcela_4x_{sufixo}", "")] = f"R$ {parcelas4[2].get('valor', 0):.2f}"
            if len(parcelas4) >= 4:
                form_data[form_map.get(f"terceira_parcela_4x_{sufixo}", "")] = f"R$ {parcelas4[3].get('valor', 0):.2f}"
                form_data[form_map.get(f"quarta_parcela_4x_{sufixo}", "")] = f"R$ {parcelas4[3].get('valor', 0):.2f}"
            if 'valor_total' in quatro:
                form_data[form_map.get(f"total_4x_{sufixo}", "")] = f"R$ {quatro.get('valor_total', 0):.2f}"
            
            # Cartão de crédito
            cartao = cond_pagto.get('cartao', {})
            for n in range(4, 11):
                opc = cartao.get(f"{n}x", {})
                if 'valor_parcela' in opc:
                    campo = form_map.get(f"cartao_{n}_parcelas_{sufixo}", "")
                    if campo:
                        form_data[campo] = f"R$ {opc.get('valor_parcela', 0):.2f}"

        # Criar arquivos temporários para o PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_template:
            # Baixar template
            desconto = data.get("desconto_aplicado", 0)
            template_url, template_type = await pdf_service.selecionar_template(desconto)
            template_bytes = await pdf_service.baixar_template(template_url)
            temp_template.write(template_bytes)
            temp_template_path = temp_template.name
        
        # Nome do arquivo de saída
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"proposta_{proposta_id}_{timestamp}.pdf"
        output_path = os.path.join("/tmp", output_filename)
        
        # Preencher o formulário PDF
        logger_service.log_info(f"Preenchendo formulário PDF com {len(form_data)} campos")
        pdf_service.fill_pdf_form(temp_template_path, output_path, form_data)
        
        # Fazer upload do PDF gerado
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Upload para o Supabase
        pdf_url = await pdf_service.upload_pdf_para_supabase(pdf_bytes, output_filename)
        
        logger_service.log_info(f"PDF gerado com sucesso: {pdf_url}")
        
        # Limpar arquivos temporários
        os.unlink(temp_template_path)
        os.unlink(output_path)
        
        # Enviar PDF por WhatsApp se o telefone estiver disponível
        telefone_cliente = data.get("telefone_cliente")
        if telefone_cliente:
            logger_service.log_info(f"Enviando proposta por WhatsApp para: {telefone_cliente}")
            
            # Mensagem personalizada para o WhatsApp
            marca = data.get("marca_veiculo", "")
            modelo = data.get("modelo_veiculo", "")
            mensagem = f"Olá {nome_cliente}, segue sua proposta de blindagem para o {marca} {modelo}."
            
            # Enviar PDF por WhatsApp
            whatsapp_result = await whatsapp_service.enviar_pdf_whatsapp(
                telefone_cliente, 
                pdf_url, 
                mensagem
            )
            logger_service.log_info(f"Proposta enviada por WhatsApp: {whatsapp_result}")
            
        # Preparar resultado final
        resultado = {
            "status": "success",
            "message": "Proposta gerada com sucesso",
            "tipo_blindagem": tipo_blindagem,
            "valor_blindagem": valor_base,
            "condicoes_pagamento": condicoes_pagamento,
            "pdf_url": pdf_url
        }
        
        return PropostaResponse(**resultado)
        
    except Exception as e:
        logger_service.log_error(f"Erro no processamento da proposta: {str(e)}")
        return PropostaResponse(
            status="error",
            message=f"Erro ao processar proposta: {str(e)}"
        )
