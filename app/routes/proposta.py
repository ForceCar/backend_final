"""Rotas para manipulação de propostas"""

import uuid
from datetime import datetime
from typing import Dict, Any, Union
import json  # Para serializar payload de PDF

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
        pdf_data = {}
        # Campos básicos
        for field in [
            'nome_cliente','telefone_cliente','email_cliente','nome_vendedor',
            'marca_veiculo','modelo_veiculo','teto_solar','abertura_porta_malas',
            'tipo_documentacao','pacote_revisao','vidro_10_anos','vidro_5_anos',
            'tipo_blindagem','desconto_aplicado','observations'
        ]:
            if field in data:
                pdf_data[field] = data[field]
                
        # Cenários de blindagem - SIMPLIFICADO para evitar duplicações
        pdf_data['cenarios'] = {}
        
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
                    
                pdf_data['cenarios'][label] = scenario
        else:
            # Para um tipo específico de blindagem, usar valor_base que já contém desconto
            valor_base = subtotais['valor_base']
            
            # Identificar o subtotal original sem desconto
            subtotal_map = {
                'Comfort 10 anos': 'comfort10YearsSubTotal',
                'Comfort 18 mm': 'comfort18mmSubTotal',
                'Ultralight': 'ultralightSubTotal'
            }
            subtotal = float(data.get(subtotal_map.get(tipo_blindagem, 0), 0))
            
            # Criar cenário único com condições de pagamento já calculadas
            scenario = {
                'subtotal': subtotal,
                'condicoes_pagamento': condicoes_pagamento
            }
            
            # Se houver desconto, incluir no cenário
            desconto = data.get('desconto_aplicado', 0)
            if desconto > 0:
                scenario['desconto_aplicado'] = desconto
                
            pdf_data['cenarios'][tipo_blindagem] = scenario
            
        # Log payload para PDF em formato de tabela
        logger_service.log_info("Dados para PDF:")
        # Campos básicos
        basic = {k: v for k, v in pdf_data.items() if k != 'cenarios'}
        logger_service.log_info(logger_service.format_dict_table(basic))
        
        # Se tiver cenários, apresenta cada um com formatação mais limpa
        cenarios = pdf_data.get('cenarios', {})
        if cenarios:
            for label, scenario in cenarios.items():
                logger_service.log_info(f"CENÁRIO - {label}:")
                
                # Extrair e formatar informações principais do cenário
                subtotal = scenario.get('subtotal', 0)
                desconto = scenario.get('desconto_aplicado', 0)
                
                # Criar um dicionário simplificado para exibição
                cenario_info = {
                    'subtotal': f"{subtotal:,.2f}".replace(',', '.'),
                }
                
                if desconto:
                    cenario_info['desconto_aplicado'] = f"{desconto:,.2f}".replace(',', '.') 
                
                # Exibir informações básicas do cenário
                logger_service.log_info(logger_service.format_dict_table(cenario_info))
                
                # Exibir condições de pagamento formatadas
                condicoes = scenario.get('condicoes_pagamento', {})
                if condicoes:
                    logger_service.log_info("Condições de Pagamento:")
                    
                    # À vista
                    if 'a_vista' in condicoes:
                        av = condicoes['a_vista']
                        valor = av.get('valor_total', 0)
                        desconto_perc = av.get('desconto_percentual', 0)
                        logger_service.log_info(f"  - À VISTA: R$ {valor:,.2f}".replace(',', '.') + 
                                                f" ({desconto_perc}% de desconto)")
                    
                    # 2 parcelas
                    if 'duas_vezes' in condicoes:
                        dv = condicoes['duas_vezes']
                        parcelas = dv.get('parcelas', [])
                        if len(parcelas) >= 2:
                            valor_parcela = parcelas[0].get('valor', 0)
                            logger_service.log_info(f"  - 2X SEM JUROS: {len(parcelas)}x de R$ {valor_parcela:,.2f}".replace(',', '.'))
                    
                    # 3 parcelas
                    if 'tres_vezes' in condicoes:
                        tv = condicoes['tres_vezes']
                        parcelas = tv.get('parcelas', [])
                        if len(parcelas) >= 3:
                            entrada = parcelas[0].get('valor', 0)
                            valor_parcela = parcelas[1].get('valor', 0)
                            acrescimo = tv.get('acrescimo_percentual', 0)
                            logger_service.log_info(f"  - 3X: Entrada de R$ {entrada:,.2f}".replace(',', '.') + 
                                                    f" + 2x de R$ {valor_parcela:,.2f}".replace(',', '.') +
                                                    f" ({acrescimo}% de acréscimo)")
                    
                    # 4 parcelas
                    if 'quatro_vezes' in condicoes:
                        qv = condicoes['quatro_vezes']
                        parcelas = qv.get('parcelas', [])
                        if len(parcelas) >= 4:
                            entrada = parcelas[0].get('valor', 0)
                            valor_parcela = parcelas[1].get('valor', 0)
                            acrescimo = qv.get('acrescimo_percentual', 0)
                            logger_service.log_info(f"  - 4X: Entrada de R$ {entrada:,.2f}".replace(',', '.') + 
                                                    f" + 3x de R$ {valor_parcela:,.2f}".replace(',', '.') +
                                                    f" ({acrescimo}% de acréscimo)")
                    
                    # Cartão
                    cartao = condicoes.get('cartao', {})
                    if cartao:
                        for parcela, info in cartao.items():
                            valor_parcela = info.get('valor_parcela', 0)
                            valor_total = info.get('valor_total', 0)
                            acrescimo = info.get('acrescimo', 0)
                            logger_service.log_info(f"    * {parcela}: R$ {valor_parcela:,.2f}".replace(',', '.') + 
                                                   f" (Total: R$ {valor_total:,.2f}, Acréscimo: {acrescimo}%)".replace(',', '.'))
                
                # Se houver desconto, incluir no cenário para documentação
                desconto = subtotais.get('desconto_aplicado', 0)
                if desconto > 0:
                    scenario['desconto_aplicado'] = desconto
                    
                pdf_data['cenarios'][label] = scenario
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
                
            pdf_data['cenarios'][tipo_blindagem] = scenario

        # Log payload para PDF - apenas os dados relevantes
        logger_service.log_info("Dados para PDF:")
        logger_service.log_info(json.dumps(pdf_data, indent=2, ensure_ascii=False))

        # --- Fim salvamento PDF ---

        # Gerar PDF da proposta
        logger_service.log_info("Iniciando geração de PDF da proposta...")
        try:
            pdf_url = await pdf_service.gerar_pdf_proposta(pdf_data)
            logger_service.log_info(f"PDF gerado com sucesso: {pdf_url}")
            
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
            logger_service.log_error(f"Erro ao gerar PDF ou enviar WhatsApp: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF ou enviar WhatsApp: {str(e)}")
            
    except Exception as e:
        logger_service.log_error(f"Erro no processamento da proposta: {str(e)}")
        return PropostaResponse(
            status="error",
            message=f"Erro ao processar proposta: {str(e)}"
        )
