#!/usr/bin/env python3
"""Script para inspecionar os campos de formulário em um PDF"""
import os
import sys
import tempfile
import httpx
from PyPDF2 import PdfReader

# URLs dos PDFs
PDF_COM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/preenchivel-com-desconto//com-desconto.pdf"
PDF_SEM_DESCONTO_URL = "https://ahvryabvarxisvfdnmye.supabase.co/storage/v1/object/public/preenchivel-sem-desconto//sem_desconto.pdf"

def download_pdf(url, output_path):
    """Baixa um PDF de uma URL e salva no caminho especificado"""
    print(f"Baixando PDF de {url}...")
    response = httpx.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"PDF salvo em {output_path}")
        return True
    else:
        print(f"Erro ao baixar PDF: {response.status_code}")
        return False

def inspect_pdf_fields(pdf_path):
    """Inspeciona os campos de formulário em um PDF"""
    print(f"\nInspecionando campos em {pdf_path}...")
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    
    if not fields:
        print("Nenhum campo de formulário encontrado!")
        return
    
    print(f"Encontrados {len(fields)} campos de formulário:")
    for name, field in fields.items():
        field_type = field.get('/FT', 'Desconhecido').replace('/', '')
        field_value = field.get('/V', '')
        field_info = f"- {name} (Tipo: {field_type})"
        if field_value:
            field_info += f", Valor: {field_value}"
        print(field_info)

def main():
    """Função principal"""
    # Criar diretório temporário
    with tempfile.TemporaryDirectory() as temp_dir:
        # Baixar os PDFs
        pdf_com_desconto = os.path.join(temp_dir, "com_desconto.pdf")
        pdf_sem_desconto = os.path.join(temp_dir, "sem_desconto.pdf")
        
        if download_pdf(PDF_COM_DESCONTO_URL, pdf_com_desconto):
            inspect_pdf_fields(pdf_com_desconto)
        
        if download_pdf(PDF_SEM_DESCONTO_URL, pdf_sem_desconto):
            inspect_pdf_fields(pdf_sem_desconto)

if __name__ == "__main__":
    main()
