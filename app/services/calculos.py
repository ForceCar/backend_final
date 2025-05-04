"""
Módulo para cálculos de condições de pagamento
"""
from typing import Dict, Any, List, Tuple


def calcular_subtotais_blindagem(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula os subtotais das blindagens com base no tipo de blindagem selecionado
    e aplica o desconto, se houver.
    
    Args:
        data: Dados da proposta
        
    Returns:
        Dicionário com os valores calculados para cada tipo de blindagem
    """
    tipo_blindagem = data.get("tipo_blindagem")
    desconto_aplicado = data.get("desconto_aplicado", 0)
    
    # Obtém os subtotais
    comfort10_subtotal = float(data.get("comfort10YearsSubTotal", 0))
    comfort18_subtotal = float(data.get("comfort18mmSubTotal", 0))
    ultralight_subtotal = float(data.get("ultralightSubTotal", 0))
    
    # Calcula os valores de acordo com o tipo de blindagem
    resultado = {
        "tipo_blindagem": tipo_blindagem,
        "desconto_aplicado": desconto_aplicado
    }
    
    if tipo_blindagem == "Nenhuma":
        # Para tipo "Nenhuma", retorna todos os subtotais para comparação
        resultado["comfort10_anos"] = {"subtotal": comfort10_subtotal, "valor_final": comfort10_subtotal - desconto_aplicado}
        resultado["comfort18mm"] = {"subtotal": comfort18_subtotal, "valor_final": comfort18_subtotal - desconto_aplicado}
        resultado["ultralight"] = {"subtotal": ultralight_subtotal, "valor_final": ultralight_subtotal - desconto_aplicado}
        resultado["valor_base"] = 0  # Não há valor base para "Nenhuma"
    elif tipo_blindagem == "Comfort 10 anos":
        resultado["valor_base"] = comfort10_subtotal - desconto_aplicado
    elif tipo_blindagem in ("Comfort 18 mm", "Comfort 18mm"):  # suporta ambas as variações
        resultado["valor_base"] = comfort18_subtotal - desconto_aplicado
    elif tipo_blindagem == "Ultralight":
        resultado["valor_base"] = ultralight_subtotal - desconto_aplicado
    else:
        # Tipo não reconhecido
        resultado["valor_base"] = 0
        
    return resultado


def calcular_condicoes_pagamento(subtotais: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula todas as condições de pagamento com base nos subtotais
    
    Args:
        subtotais: Dicionário com os subtotais calculados
        
    Returns:
        Dicionário com todas as condições de pagamento
    """
    tipo_blindagem = subtotais.get("tipo_blindagem")
    valor_base = subtotais.get("valor_base", 0)
    
    # Se não houver valor base (tipo_blindagem == "Nenhuma"), retorna valores zerados
    if valor_base == 0:
        return {
            "a_vista": {"valor_total": 0, "parcelas": [{"numero": 1, "valor": 0}]},
            "duas_vezes": {"valor_total": 0, "parcelas": [{"numero": 1, "valor": 0}, {"numero": 2, "valor": 0}]},
            "tres_vezes": {"valor_total": 0, "parcelas": [{"numero": 1, "valor": 0}, {"numero": 2, "valor": 0}, {"numero": 3, "valor": 0}]},
            "quatro_vezes": {"valor_total": 0, "parcelas": [{"numero": 1, "valor": 0}, {"numero": 2, "valor": 0}, {"numero": 3, "valor": 0}, {"numero": 4, "valor": 0}]},
            "cartao": {
                "4x": {"acrescimo": 6, "valor_total": 0, "valor_parcela": 0},
                "5x": {"acrescimo": 7, "valor_total": 0, "valor_parcela": 0},
                "6x": {"acrescimo": 8, "valor_total": 0, "valor_parcela": 0},
                "7x": {"acrescimo": 9, "valor_total": 0, "valor_parcela": 0},
                "8x": {"acrescimo": 10, "valor_total": 0, "valor_parcela": 0},
                "9x": {"acrescimo": 11, "valor_total": 0, "valor_parcela": 0},
                "10x": {"acrescimo": 12, "valor_total": 0, "valor_parcela": 0}
            }
        }
    
    # Calculando todas as opções de pagamento
    resultado = {}
    
    # À vista: 2% de desconto
    valor_a_vista = valor_base * 0.98
    resultado["a_vista"] = {
        "valor_total": valor_a_vista,
        "desconto_percentual": 2,
        "parcelas": [{"numero": 1, "valor": valor_a_vista}]
    }
    
    # 2 parcelas: divide o valor por 2
    resultado["duas_vezes"] = {
        "valor_total": valor_base,
        "desconto_percentual": 0,
        "parcelas": [
            {"numero": 1, "valor": valor_base / 2},
            {"numero": 2, "valor": valor_base / 2}
        ]
    }
    
    # 3 parcelas: sinal de 50% + 2 parcelas com acréscimo de 1%
    valor_tres_vezes = valor_base * 1.01
    valor_entrada_3x = valor_tres_vezes * 0.5
    valor_parcela_3x = (valor_tres_vezes - valor_entrada_3x) / 2
    resultado["tres_vezes"] = {
        "valor_total": valor_tres_vezes,
        "acrescimo_percentual": 1,
        "parcelas": [
            {"numero": 1, "valor": valor_entrada_3x, "tipo": "entrada"},
            {"numero": 2, "valor": valor_parcela_3x},
            {"numero": 3, "valor": valor_parcela_3x}
        ]
    }
    
    # 4 parcelas: sinal de 60% + 3 parcelas com acréscimo de 3%
    valor_quatro_vezes = valor_base * 1.03
    valor_entrada_4x = valor_quatro_vezes * 0.6
    valor_parcela_4x = (valor_quatro_vezes - valor_entrada_4x) / 3
    resultado["quatro_vezes"] = {
        "valor_total": valor_quatro_vezes,
        "acrescimo_percentual": 3,
        "parcelas": [
            {"numero": 1, "valor": valor_entrada_4x, "tipo": "entrada"},
            {"numero": 2, "valor": valor_parcela_4x},
            {"numero": 3, "valor": valor_parcela_4x},
            {"numero": 4, "valor": valor_parcela_4x}
        ]
    }
    
    # Opções de cartão de crédito
    resultado["cartao"] = {}
    
    # De 4x a 10x com acréscimos crescentes
    acrescimos = {
        "4x": 6,
        "5x": 7,
        "6x": 8,
        "7x": 9,
        "8x": 10,
        "9x": 11,
        "10x": 12
    }
    
    for parcelas, acrescimo in acrescimos.items():
        num_parcelas = int(parcelas.replace("x", ""))
        valor_total_cartao = valor_base * (1 + acrescimo/100)
        valor_parcela_cartao = valor_total_cartao / num_parcelas
        
        resultado["cartao"][parcelas] = {
            "acrescimo": acrescimo,
            "valor_total": valor_total_cartao,
            "valor_parcela": valor_parcela_cartao
        }
    
    return resultado


def calcular_valor_blindagem(data: Dict[str, Any]) -> float:
    """
    Calcula o valor base da blindagem (subtotal - desconto) com base no tipo de blindagem selecionado
    
    DEPRECATED: Use calcular_subtotais_blindagem em vez desta função
    """
    tipo_blindagem = data.get("tipo_blindagem")
    desconto = data.get("desconto_aplicado", 0)
    
    if tipo_blindagem == "Comfort 10 anos":
        subtotal = data.get("comfort10YearsSubTotal", 0)
    elif tipo_blindagem in ("Comfort 18 mm", "Comfort 18mm"):  # suporta ambas as variações
        subtotal = data.get("comfort18mmSubTotal", 0)
    elif tipo_blindagem == "Ultralight":
        subtotal = data.get("ultralightSubTotal", 0)
    else:  # Se for "Nenhuma" ou outro valor não esperado
        # Neste caso, não faz sentido calcular um valor, então retornamos 0
        return 0
        
    return subtotal - desconto


def calcular_a_vista(valor_base: float) -> Dict[str, Any]:
    """
    Calcula o valor à vista com 2% de desconto
    """
    desconto = round(valor_base * 0.02, 2)
    valor_final = valor_base - desconto
    
    return {
        "desconto_percentual": 2,
        "valor_desconto": desconto,
        "valor_final": valor_final
    }


def calcular_parcelado_direto(valor_base: float) -> List[Dict[str, Any]]:
    """
    Calcula as opções de pagamento direto:
    - 2 parcelas → valor dividido por 2
    - 3 parcelas → sinal de 50% + 2x, com 1% de acréscimo no total
    - 4 parcelas → sinal de 60% + 3x, com 3% de acréscimo no total
    """
    resultado = []
    
    # 2 parcelas → valor dividido por 2
    opcao_2x = {
        "parcelas": 2,
        "acrescimo_percentual": 0,
        "valor_acrescimo": 0,
        "valor_total": valor_base,
        "valor_parcela": round(valor_base / 2, 2),
        "detalhes": "2x sem acréscimo"
    }
    resultado.append(opcao_2x)
    
    # 3 parcelas → sinal de 50% + 2x, com 1% de acréscimo no total
    acrescimo_3x = round(valor_base * 0.01, 2)
    valor_total_3x = valor_base + acrescimo_3x
    sinal_3x = round(valor_total_3x * 0.5, 2)
    restante_3x = valor_total_3x - sinal_3x
    parcela_3x = round(restante_3x / 2, 2)
    
    opcao_3x = {
        "parcelas": 3,
        "acrescimo_percentual": 1,
        "valor_acrescimo": acrescimo_3x,
        "valor_total": valor_total_3x,
        "valor_entrada": sinal_3x,
        "valor_parcela": parcela_3x,
        "detalhes": f"Entrada de {sinal_3x:.2f} + 2x de {parcela_3x:.2f}"
    }
    resultado.append(opcao_3x)
    
    # 4 parcelas → sinal de 60% + 3x, com 3% de acréscimo no total
    acrescimo_4x = round(valor_base * 0.03, 2)
    valor_total_4x = valor_base + acrescimo_4x
    sinal_4x = round(valor_total_4x * 0.6, 2)
    restante_4x = valor_total_4x - sinal_4x
    parcela_4x = round(restante_4x / 3, 2)
    
    opcao_4x = {
        "parcelas": 4,
        "acrescimo_percentual": 3,
        "valor_acrescimo": acrescimo_4x,
        "valor_total": valor_total_4x,
        "valor_entrada": sinal_4x,
        "valor_parcela": parcela_4x,
        "detalhes": f"Entrada de {sinal_4x:.2f} + 3x de {parcela_4x:.2f}"
    }
    resultado.append(opcao_4x)
    
    return resultado


def calcular_parcelado_cartao(valor_base: float) -> List[Dict[str, Any]]:
    """
    Calcula as opções de pagamento com cartão de crédito:
    - 4 parcelas → 6% de acréscimo
    - 5 parcelas → 7%
    - 6 parcelas → 8%
    - 7 parcelas → 9%
    - 8 parcelas → 10%
    - 9 parcelas → 11%
    - 10 parcelas → 12%
    """
    opcoes_cartao = [
        {"parcelas": 4, "acrescimo": 6},
        {"parcelas": 5, "acrescimo": 7},
        {"parcelas": 6, "acrescimo": 8},
        {"parcelas": 7, "acrescimo": 9},
        {"parcelas": 8, "acrescimo": 10},
        {"parcelas": 9, "acrescimo": 11},
        {"parcelas": 10, "acrescimo": 12}
    ]
    
    resultado = []
    
    for opcao in opcoes_cartao:
        parcelas = opcao["parcelas"]
        acrescimo_percentual = opcao["acrescimo"]
        
        valor_acrescimo = round(valor_base * (acrescimo_percentual / 100), 2)
        valor_total = valor_base + valor_acrescimo
        valor_parcela = round(valor_total / parcelas, 2)
        
        resultado.append({
            "parcelas": parcelas,
            "acrescimo_percentual": acrescimo_percentual,
            "valor_acrescimo": valor_acrescimo,
            "valor_total": valor_total,
            "valor_parcela": valor_parcela,
            "detalhes": f"{parcelas}x de {valor_parcela:.2f}"
        })
    
    return resultado


def calcular_condicoes_pagamento_legacy(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula todas as condições de pagamento com base no valor da blindagem
    """
    valor_base = calcular_valor_blindagem(data)
    
    # Se o valor for zero, não faz sentido calcular condições de pagamento
    if valor_base <= 0:
        return {
            "valor_base": 0,
            "a_vista": {},
            "parcelado_direto": [],
            "parcelado_cartao": []
        }
        
    a_vista = calcular_a_vista(valor_base)
    parcelado_direto = calcular_parcelado_direto(valor_base)
    parcelado_cartao = calcular_parcelado_cartao(valor_base)
    
    return {
        "valor_base": valor_base,
        "a_vista": a_vista,
        "parcelado_direto": parcelado_direto,
        "parcelado_cartao": parcelado_cartao
    }
