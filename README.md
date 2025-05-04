# Forcecar Backend API

Backend para automatização de geração de propostas da empresa Forcecar.

## Tecnologias utilizadas

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- Loguru

## Estrutura do projeto

```
forsecar_backend/
│
├── main.py              # Ponto de entrada da aplicação
├── requirements.txt     # Dependências do projeto
├── .env                 # Configurações de ambiente
├── app/                 # Pacote principal da aplicação
│   ├── __init__.py
│   ├── routes/          # Rotas da API
│   │   └── proposta.py
│   ├── schemas/         # Modelos de dados Pydantic
│   │   └── proposta_schema.py
│   ├── services/        # Serviços e lógica de negócios
│   │   ├── calculos.py
│   │   └── logger_service.py
│   └── config.py        # Configurações da aplicação
└── logs/                # Diretório para arquivos de log
    └── app.log
```

## Instalação

1. Clone o repositório:
```bash
git clone <url_do_repositorio>
cd forcecar_backend
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Execução

Para iniciar o servidor em modo de desenvolvimento:

```bash
python main.py
```

Ou diretamente com o Uvicorn:
```bash
uvicorn main:app --reload
```

O servidor estará disponível em: http://localhost:8000

## Endpoints da API

### Gerar Proposta
```
POST /api/gerar_proposta_rodrigo
```

Recebe os dados da proposta e retorna as condições de pagamento calculadas.

Payload de exemplo:
```json
{
  "nome_cliente": "João Silva",
  "telefone_cliente": "(11) 99999-9999",
  "email_cliente": "joao@exemplo.com",
  "marca_veiculo": "Toyota",
  "modelo_veiculo": "Corolla",
  "teto_solar": true,
  "abertura_porta_malas": false,
  "tipo_documentacao": "CNH",
  "possui_documentacao": true,
  "desconto_aplicado": 0,
  "vidro_10_anos": true,
  "vidro_5_anos": false,
  "pacote_revisao": true,
  "tipo_blindagem": "Comfort 10 anos",
  "comfort10YearsSubTotal": 45000,
  "comfort10YearsDiscount": 2000
}
```

## Documentação

A documentação interativa da API está disponível em:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Próximos passos

O projeto está estruturado para facilitar a implementação de:

1. Preenchimento automático de PDFs
2. Integração com Supabase
3. Envio de mensagens via WhatsApp (Z-API)
4. Autenticação e autorização
5. Persistência de dados em banco de dados relacional
