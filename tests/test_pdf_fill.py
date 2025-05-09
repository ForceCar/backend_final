"""
Testes para verificar o preenchimento de formulários PDF
"""
import unittest
import os
import tempfile
import io
from PyPDF2 import PdfReader

from app.services.pdf_service import fill_pdf_form
from config.form_map import (
    FORM_MAP_WITH_DESCONTO,
    FORM_MAP_SEM_DESCONTO,
    PAYMENT_CONDITIONS_MAP
)

class TestPDFFill(unittest.TestCase):
    """Testes para o preenchimento de formulários PDF"""

    def setUp(self):
        """Configuração para os testes"""
        # Criar um caminho para o template PDF de teste
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        os.makedirs(self.templates_dir, exist_ok=True)
        self.template_path = os.path.join(self.templates_dir, "Final.pdf")
        
        # Criar um arquivo temporário para o PDF de saída
        self.temp_output = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        self.temp_output.close()
        self.output_path = self.temp_output.name
    
    def tearDown(self):
        """Limpeza após os testes"""
        # Remover o arquivo temporário de saída
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)
    
    def test_fill_pdf_form_with_discount(self):
        """Testa o preenchimento de um formulário PDF com desconto"""
        # Verificar se o template existe
        if not os.path.exists(self.template_path):
            self.skipTest(f"Template PDF não encontrado: {self.template_path}")
        
        # Preparar dados de teste
        test_data = {
            "nome_cliente": "João Silva",
            "telefone_cliente": "(11) 99999-9999",
            "email_cliente": "joao@example.com",
            "marca_carro": "Toyota",
            "modelo_carro": "Corolla",
            "teto_solar": "Sim",
            "porta-malas": "Elétrico",
            "tipo_documentacao": "CPF",
            "desconto": "R$ 2000,00",
            "vidro_10_anos": "R$ 45000,00",
            "vidro_5_anos_18mm": "R$ 38000,00",
            "vidro_5_anos_ultralight": "R$ 42000,00",
            "total_10_anos": "R$ 45000,00",
            "a_vista_10_anos": "R$ 42750,00",
            "primeira_parcela_2x_10_anos": "R$ 22500,00",
            "segunda_parcela_2x_10_anos": "R$ 22500,00"
        }
        
        # Mapear para os campos do formulário usando FORM_MAP_WITH_DESCONTO
        form_data = {}
        for key, pdf_field in FORM_MAP_WITH_DESCONTO.items():
            if key in test_data:
                form_data[pdf_field] = test_data[key]
        
        # Adicionar alguns campos de condições de pagamento
        for key, pdf_field in PAYMENT_CONDITIONS_MAP.items():
            if key in test_data:
                form_data[pdf_field] = test_data[key]
        
        try:
            # Preencher o formulário PDF
            fill_pdf_form(self.template_path, self.output_path, form_data)
            
            # Verificar se o arquivo de saída foi criado
            self.assertTrue(os.path.exists(self.output_path), "O arquivo PDF de saída não foi criado")
            
            # Ler o PDF preenchido para verificar os campos
            reader = PdfReader(self.output_path)
            
            # Verificar se o PDF tem campos de formulário
            if reader.get_fields():
                # Verificar se os campos foram preenchidos corretamente
                fields = reader.get_fields()
                for pdf_field, value in form_data.items():
                    if pdf_field in fields:
                        field_value = fields[pdf_field].get("/V", "")
                        self.assertEqual(value, field_value, f"Campo {pdf_field} tem valor '{field_value}', esperava '{value}'")
        except Exception as e:
            self.fail(f"Erro ao preencher o formulário PDF: {str(e)}")
    
    def test_fill_pdf_form_without_discount(self):
        """Testa o preenchimento de um formulário PDF sem desconto"""
        # Verificar se o template existe
        if not os.path.exists(self.template_path):
            self.skipTest(f"Template PDF não encontrado: {self.template_path}")
        
        # Preparar dados de teste
        test_data = {
            "nome_cliente": "Maria Oliveira",
            "telefone_cliente": "(21) 88888-8888",
            "email_cliente": "maria@example.com",
            "marca_carro": "Honda",
            "modelo_carro": "Civic",
            "teto_solar": "Não",
            "porta-malas": "Manual",
            "tipo_documentacao": "CNPJ",
            "vidro_10_anos": "R$ 45000,00",
            "vidro_5_anos_18mm": "R$ 38000,00",
            "vidro_5_anos_ultralight": "R$ 42000,00",
            "total_10_anos": "R$ 45000,00",
            "a_vista_10_anos": "R$ 42750,00",
            "primeira_parcela_2x_10_anos": "R$ 22500,00",
            "segunda_parcela_2x_10_anos": "R$ 22500,00"
        }
        
        # Mapear para os campos do formulário usando FORM_MAP_SEM_DESCONTO
        form_data = {}
        for key, pdf_field in FORM_MAP_SEM_DESCONTO.items():
            if key in test_data:
                form_data[pdf_field] = test_data[key]
        
        # Adicionar alguns campos de condições de pagamento
        for key, pdf_field in PAYMENT_CONDITIONS_MAP.items():
            if key in test_data:
                form_data[pdf_field] = test_data[key]
        
        try:
            # Preencher o formulário PDF
            fill_pdf_form(self.template_path, self.output_path, form_data)
            
            # Verificar se o arquivo de saída foi criado
            self.assertTrue(os.path.exists(self.output_path), "O arquivo PDF de saída não foi criado")
            
            # Ler o PDF preenchido para verificar os campos
            reader = PdfReader(self.output_path)
            
            # Verificar se o PDF tem campos de formulário
            if reader.get_fields():
                # Verificar se os campos foram preenchidos corretamente
                fields = reader.get_fields()
                for pdf_field, value in form_data.items():
                    if pdf_field in fields:
                        field_value = fields[pdf_field].get("/V", "")
                        self.assertEqual(value, field_value, f"Campo {pdf_field} tem valor '{field_value}', esperava '{value}'")
        except Exception as e:
            self.fail(f"Erro ao preencher o formulário PDF: {str(e)}")
    
    def test_get_pdf_fields(self):
        """Testa a leitura dos campos disponíveis no formulário PDF"""
        # Verificar se o template existe
        if not os.path.exists(self.template_path):
            self.skipTest(f"Template PDF não encontrado: {self.template_path}")
        
        try:
            # Ler os campos do formulário PDF
            reader = PdfReader(self.template_path)
            fields = reader.get_fields()
            
            # Verificar se há campos no formulário
            self.assertIsNotNone(fields, "O PDF não contém campos de formulário")
            
            # Listar todos os campos para fins de depuração
            print(f"\nCampos encontrados no formulário PDF ({len(fields)}):")
            for name in fields.keys():
                print(f"- {name}")
            
            # Verificar se campos específicos estão presentes
            expected_fields = [
                "NOME com desc",
                "TELEFONE com desc",
                "E-MAIL com desc",
                "MARCA com desc",
                "MODELO com desc",
                "NOME sem desc",
                "TELEFONE sem desc",
                "E-MAIL sem desc"
            ]
            
            for field in expected_fields:
                self.assertIn(field, fields, f"Campo esperado '{field}' não encontrado no formulário")
        except Exception as e:
            self.fail(f"Erro ao ler campos do formulário PDF: {str(e)}")


if __name__ == "__main__":
    unittest.main()
