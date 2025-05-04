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
            
        # Log payload para PDF - apenas os dados relevantes
        logger_service.log_info("Dados para PDF:")
        logger_service.log_info(json.dumps(pdf_data, indent=2, ensure_ascii=False))
        # --- Fim salvamento PDF ---
        
        resultado = {
            "status": "success",
            "message": "Proposta processada com sucesso",
            "proposta_id": proposta_id,
            "tipo_blindagem": tipo_blindagem,
            "valor_blindagem": valor_base,
            "condicoes_pagamento": condicoes_pagamento,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log de sucesso: passar dados originais e resultado para evitar erro de .get em string
        logger_service.log_success(data, resultado)
        
        return resultado
        
    except Exception as e:
        logger_service.log_error(f"Erro ao processar proposta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar proposta: {str(e)}")
