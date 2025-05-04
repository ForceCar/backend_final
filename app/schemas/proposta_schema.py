"""
Schemas para validação de dados da proposta
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class PropostaBase(BaseModel):
    """
    Schema base para os dados da proposta.
    Inclui validação para os campos principais e permite campos adicionais dinâmicos.
    """
    # Campos obrigatórios do cliente
    nome_cliente: str
    telefone_cliente: str
    email_cliente: str
    
    # Campos obrigatórios do veículo
    marca_veiculo: str
    modelo_veiculo: str
    
    # Opções de configuração
    teto_solar: bool = False
    abertura_porta_malas: bool = False
    
    # Documentação
    tipo_documentacao: str
    possui_documentacao: bool = False
    
    # Opções comerciais
    desconto_aplicado: float = 0
    vidro_10_anos: bool = False
    vidro_5_anos: bool = False
    pacote_revisao: bool = False
    
    # Tipo de blindagem - define quais subtotais e descontos são obrigatórios
    tipo_blindagem: str
    
    class Config:
        """Configuração do schema permitindo campos extras"""
        extra = "allow"  # Permite campos extras não definidos no schema


class PropostaComfort10Anos(PropostaBase):
    """Schema específico para propostas com blindagem Comfort 10 anos"""
    comfort10YearsSubTotal: float
    comfort10YearsDiscount: float = 0
    
    @validator('tipo_blindagem')
    def validar_tipo_blindagem(cls, v):
        if v != "Comfort 10 anos":
            raise ValueError("Tipo de blindagem deve ser 'Comfort 10 anos'")
        return v


class PropostaComfort18mm(PropostaBase):
    """Schema específico para propostas com blindagem Comfort 18mm"""
    comfort18mmSubTotal: float
    comfort18mmDiscount: float = 0
    
    @validator('tipo_blindagem')
    def validar_tipo_blindagem(cls, v):
        if v != "Comfort 18 mm":
            raise ValueError("Tipo de blindagem deve ser 'Comfort 18 mm'")
        return v


class PropostaUltralight(PropostaBase):
    """Schema específico para propostas com blindagem Ultralight"""
    ultralightSubTotal: float
    ultralightDiscount: float = 0
    
    @validator('tipo_blindagem')
    def validar_tipo_blindagem(cls, v):
        if v != "Ultralight":
            raise ValueError("Tipo de blindagem deve ser 'Ultralight'")
        return v


class PropostaNenhuma(PropostaBase):
    """
    Schema para propostas que incluem todas as opções de blindagem 
    (para comparação)
    """
    comfort10YearsSubTotal: float
    comfort10YearsDiscount: float = 0
    comfort18mmSubTotal: float
    comfort18mmDiscount: float = 0
    ultralightSubTotal: float
    ultralightDiscount: float = 0
    
    @validator('tipo_blindagem')
    def validar_tipo_blindagem(cls, v):
        if v != "Nenhuma":
            raise ValueError("Tipo de blindagem deve ser 'Nenhuma'")
        return v


class CondicoesPagamento(BaseModel):
    """Schema para as condições de pagamento calculadas"""
    valor_base: float
    a_vista: Dict[str, Any]
    parcelado_direto: List[Dict[str, Any]]
    parcelado_cartao: List[Dict[str, Any]]


class PropostaResponse(BaseModel):
    """Resposta padrão para geração de proposta"""
    status: str
    message: str
    tipo_blindagem: Optional[str] = None
    valor_blindagem: Optional[float] = None
    condicoes_pagamento: Optional[Union[CondicoesPagamento, Dict[str, CondicoesPagamento]]] = None
    timestamp: Optional[str] = datetime.now().isoformat()
