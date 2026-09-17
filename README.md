# Cofre AES

Aplicação de API REST para armazenamento de senhas com criptografia forte, desenvolvida em Python com FastAPI e Supabase.

## Visão geral

Este projeto implementa um cofre de senhas corporativo em que:

- a senha mestra do usuário nunca é salva no banco;
- cada cofre usa um salt aleatório e PBKDF2-HMAC-SHA256;
- os segredos são cifrados com AES-GCM;
- cada registro possui autenticação de integridade por meio de tag GCM;
- a API valida a senha mestra antes de permitir leitura ou atualização de segredos.

O objetivo é demonstrar o uso de criptografia aplicada em um sistema didático de gerenciamento de segredos, respeitando as exigências de segurança e de fluxo de autenticação do enunciado do projeto.

## Requisitos da solução

A aplicação atende aos requisitos principais do projeto:

- geração de salt aleatório para cada cofre;
- derivação de chave com PBKDF2 e SHA-256;
- uso de AES-256-GCM para cifragem de segredos;
- uso de nonce aleatório em cada operação de cifragem;
- verificação de integridade com autenticação de etiqueta;
- autenticação do acesso por meio da senha mestra em todas as rotas protegidas;
- persistência dos dados em Base64 quando armazenados no banco;
- isolamento entre cofres e segredos;
- prevenção de leitura de segredo sem autenticação válida.

## Estrutura do projeto

- app/main.py: rotas, autenticação e tratamento de erros HTTP
- app/cripto.py: funções de derivação, cifragem e verificação de integridade
- app/banco.py: acesso ao Supabase e persistência dos registros
- app/modelos.py: modelos Pydantic das entradas da API
- sql/esquema.sql: esquema do banco
- tests/: suíte automatizada com pytest
- testes/: evidências e documentação de execução manual
- .env.example: template das variáveis de ambiente

## Pré-requisitos

- Python 3.10 ou superior
- Ambiente virtual
- Projeto Supabase com URL e chave pública configurados

## Instalação

No Windows PowerShell, execute:

```powershell
cd "C:\Users\flael\Projeto-COFRE-AES"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

No Linux/macOS, comandos equivalentes:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Crie o arquivo `.env` com base em `.env.example`:

```env
SUPABASE_URL=https://SEU_PROJETO.supabase.co
SUPABASE_KEY=sua_chave_publica_ou_publishable
```

> Importante: nunca publique o arquivo `.env` em repositório público.

## Banco de dados

Antes de iniciar a aplicação, aplique o esquema no Supabase:

```sql
-- consulte o arquivo sql/esquema.sql
```

A estrutura contemplada é:

- cofres
  - id
  - nome
  - kdf_sal
  - kdf_iteracoes
  - verificador_nonce
  - verificador_criptograma
  - verificador_etiqueta
  - criado_em

- segredos
  - id
  - cofre_id
  - titulo
  - usuario
  - url
  - nonce
  - criptograma
  - etiqueta
  - criado_em
  - atualizado_em

## Execução da API

Inicie o servidor local:

```powershell
cd "C:\Users\flael\Projeto-COFRE-AES"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

A aplicação ficará disponível em:

```text
http://127.0.0.1:8000/docs
```

A rota raiz `/` não possui endpoint específico e retornará 404, por isso o acesso correto é via `/docs` ou `/openapi.json`.

## Endpoints principais

| Método | Rota | Descrição |
| --- | --- | --- |
| POST | /cofres | Cria um novo cofre |
| POST | /cofres/{cofre_id}/abrir | Verifica a senha mestra |
| POST | /cofres/{cofre_id}/segredos | Cria um segredo cifrado |
| GET | /cofres/{cofre_id}/segredos | Lista os segredos do cofre |
| GET | /cofres/{cofre_id}/segredos/{segredo_id} | Lê um segredo específico |
| PUT | /cofres/{cofre_id}/segredos/{segredo_id} | Atualiza um segredo |
| DELETE | /cofres/{cofre_id}/segredos/{segredo_id} | Remove um segredo |

### Header obrigatório

Todas as rotas protegidas exigem:

```http
X-Senha-Mestra: <senha-mestra>
```

## Fluxo de funcionamento

1. O usuário cria um cofre com nome e senha mestra.
2. O sistema gera um salt aleatório e deriva uma chave PBKDF2.
3. A frase verificação `cofre-ok` é cifrada e armazenada no registro do cofre.
4. O usuário adiciona um segredo com título, dados opcionais e senha.
5. O segredo é cifrado com AES-GCM utilizando o AAD `cofre_id|segredo_id`.
6. O banco recebe somente informações em Base64 e metadados não sensíveis.
7. Ao ler o segredo, a API valida a senha mestra, verifica a etiqueta GCM e decifra o valor.

## Segurança implementada

A solução foi pensada para cumprir as exigências do projeto:

- PBKDF2-HMAC-SHA256 com 210.000 iterações
- salt de 16 bytes
- AES-256-GCM
- nonce aleatório de 12 bytes para cada operação
- AAD `cofre_id|segredo_id` para segredos
- AAD apenas `cofre_id` para verificador do cofre
- validação de etiqueta antes de devolver o texto claro
- resposta padrão sem vazamento de detalhes internos em falhas gerais

## Limitações e observações

- A aplicação não mantém sessão nem armazena a chave derivada entre requisições.
- O projeto é didático e usa políticas amplas de acesso no Supabase, como exigido pelo enunciado.
- O título, usuário e URL ficam visíveis no banco; somente a senha do segredo é cifrada.
- Em produção, seria necessário reforçar políticas de banco, autenticação robusta, HTTPS e auditoria.

## Verificação automatizada

Para validar o comportamento da aplicação:

```powershell
cd "C:\Users\flael\Projeto-COFRE-AES"
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py
```

Resultado verificado na execução local:

- 53 testes aprovados
- 0 falhas

Também foi validado o fluxo real do backend com um script de teste de integração, incluindo:

- criação do cofre;
- abertura do cofre;
- criação do segredo;
- listagem;
- leitura;
- atualização;
- remoção.

## Evidências e documentação complementar

- [tests/test_api.py](tests/test_api.py): validação do fluxo HTTP e autenticação
- [tests/test_cripto.py](tests/test_cripto.py): testes de parâmetros criptográficos
- [testes/resultados.md](testes/resultados.md): registro de evidências e roteiro manual
- [sql/esquema.sql](sql/esquema.sql): esquema do banco
- [docs/documentacao.md](docs/documentacao.md): documentação técnica detalhada do projeto

## Conclusão

O projeto implementa um cofre de senhas com foco em segurança prática e didática, usando criptografia real e validação automatizada. A arquitetura final está alinhada com os objetivos esperados pelo enunciado e pelos testes de qualidade executados.
