# Documentação técnica do Cofre AES

## 1. Introdução

Este projeto implementa um cofre de senhas corporativo com foco em segurança, uso de criptografia real e fluxo de autenticação por senha mestra. A solução foi desenvolvida em Python usando FastAPI e Supabase, com criptografia baseada em AES-GCM e PBKDF2-HMAC-SHA256.

A aplicação permite que o usuário:

- crie um cofre;
- autentique o cofre com uma senha mestra;
- armazene segredos cifrados;
- liste, leia, atualize e remova segredos;
- valide integridade e autenticação dos registros;
- reutilize o mesmo fluxo em testes automatizados e em requisições HTTP.

## 2. Objetivo do sistema

O objetivo principal é proteger segredos sensíveis em um banco de dados, sem armazenar os valores em texto puro. A aplicação garante que:

- a senha mestra não fique persistida no banco;
- cada cofre tenha um salt próprio;
- a derivação da chave use PBKDF2 com SHA-256;
- os segredos usem AES-GCM com nonce aleatório;
- qualquer adulteração do registro seja detectada por verificação da etiqueta GCM;
- o acesso a segredos só seja permitido após autenticação válida da senha mestra.

## 3. Arquitetura geral

### 3.1 Camadas

1. Camada de API
   - arquivo: app/main.py
   - responsável por rotas HTTP, autenticação e respostas

2. Camada de criptografia
   - arquivo: app/cripto.py
   - responsável por derivar chaves, cifrar, decifrar e validar verificador

3. Camada de persistência
   - arquivo: app/banco.py
   - responsável pela integração com o banco Supabase

4. Camada de modelos
   - arquivo: app/modelos.py
   - define os payloads de entrada da API usando Pydantic

5. Banco de dados
   - arquivo: sql/esquema.sql
   - estrutura de tabelas e políticas didáticas para laboratório

## 4. Fluxo de autenticação

A autenticação da API é baseada na senha mestra do cofre.

### Passo a passo

1. O usuário cria um cofre enviando nome e senha mestra.
2. O sistema gera um salt aleatório.
3. A chave do cofre é derivada usando PBKDF2 com SHA-256.
4. A frase `cofre-ok` é cifrada e armazenada como verificador do cofre.
5. Para qualquer operação com segredos, o cliente envia o cabeçalho `X-Senha-Mestra`.
6. A API deriva a chave novamente com o salt do cofre.
7. A chave derivada é usada para verificar o verificador do cofre.
8. Se a autenticação falhar, a API responde 401.
9. Se a autenticação passar, a operação prossegue.

## 5. Criptografia aplicada

### 5.1 PBKDF2

Cada cofre usa:

- salt aleatório de 16 bytes;
- 210.000 iterações;
- HMAC-SHA256;
- output de 32 bytes para chave AES-256.

A derivação é realizada em app/cripto.py por meio da função `derivar_chave`.

### 5.2 AES-GCM

Os segredos são cifrados utilizando AES-GCM em modo autenticado.

Parâmetros usados:

- chave: 32 bytes
- nonce: 12 bytes aleatórios
- texto claro: senha do segredo
- AAD dos segredos: `cofre_id|segredo_id`

O esquema usa autenticação de integridade por meio da etiqueta GCM. Se os dados forem alterados no banco, a API rejeita a leitura com erro de integridade.

## 6. AAD e verificador do cofre

### Verificador do cofre

O verificador do cofre é uma cifra da frase literal:

```text
cofre-ok
```

Esse verificador é gerado com o AAD sendo apenas o identificador do cofre. Assim, a senha mestra correta só é aceita para o cofre correto.

### AAD dos segredos

Cada segredo usa como AAD:

```text
{cofre_id}|{segredo_id}
```

Isso garante que um segredo não possa ser lido em outro cofre, mesmo que o atacante tenha acesso ao banco.

## 7. Persistência no banco

Os campos sensíveis que são armazenados no banco são convertidos para Base64 antes do armazenamento, como exigido pelo projeto.

### Exemplos de campos persistidos

- kdf_sal
- verificador_nonce
- verificador_criptograma
- verificador_etiqueta
- nonce
- criptograma
- etiqueta

Esses campos são texto codificado em Base64, não o conteúdo em texto plano.

## 8. Estrutura do banco

### Tabela cofres

```sql
create table public.cofres (
  id uuid primary key,
  nome text not null,
  kdf_sal text not null,
  kdf_iteracoes integer not null,
  verificador_nonce text not null,
  verificador_criptograma text not null,
  verificador_etiqueta text not null,
  criado_em timestamptz not null default now()
);
```

### Tabela segredos

```sql
create table public.segredos (
  id uuid primary key,
  cofre_id uuid not null references public.cofres(id) on delete cascade,
  titulo text not null,
  usuario text,
  url text,
  nonce text not null,
  criptograma text not null,
  etiqueta text not null,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
```

## 9. Endpoints da API

### POST /cofres

Cria um novo cofre.

Request body:

```json
{
  "nome": "Meu cofre",
  "senha_mestra": "minha-senha-secreta"
}
```

Resposta de sucesso:

```json
{
  "id": "uuid",
  "nome": "Meu cofre"
}
```

### POST /cofres/{cofre_id}/abrir

Valida a senha mestra do cofre.

Headers:

```http
X-Senha-Mestra: minha-senha-secreta
```

Resposta de sucesso:

```json
{
  "mensagem": "Cofre aberto"
}
```

### POST /cofres/{cofre_id}/segredos

Cria um novo segredo cifrado.

Body:

```json
{
  "titulo": "Email",
  "usuario": "meu@email.com",
  "url": "https://example.com",
  "senha": "senha-do-email"
}
```

Resposta de sucesso:

```json
{
  "id": "uuid-do-segredo",
  "titulo": "Email",
  "usuario": "meu@email.com",
  "url": "https://example.com"
}
```

### GET /cofres/{cofre_id}/segredos

Lista os segredos de um cofre.

Resposta:

```json
[
  {
    "id": "uuid",
    "titulo": "Email",
    "usuario": "meu@email.com",
    "url": "https://example.com",
    "criado_em": "2026-09-16T00:00:00+00:00"
  }
]
```

### GET /cofres/{cofre_id}/segredos/{segredo_id}

Lê um segredo específico e devolve a senha em texto claro após autenticação.

Resposta:

```json
{
  "id": "uuid",
  "titulo": "Email",
  "usuario": "meu@email.com",
  "url": "https://example.com",
  "senha": "senha-do-email"
}
```

### PUT /cofres/{cofre_id}/segredos/{segredo_id}

Atualiza o valor de senha de um segredo.

Body:

```json
{
  "senha": "nova-senha"
}
```

Resposta:

```json
{
  "mensagem": "Segredo atualizado"
}
```

### DELETE /cofres/{cofre_id}/segredos/{segredo_id}

Remove um segredo do cofre.

Resposta:

```json
{
  "mensagem": "Segredo removido"
}
```

## 10. Tratamento de erros

A API responde com os códigos principais:

- 200: operação bem-sucedida
- 201: entidade criada
- 401: senha mestra inválida ou integridade falha
- 404: cofre ou segredo não encontrado
- 422: payload inválido ou campo obrigatório ausente
- 500: falha interna ou registro adulterado após autenticação válida

No caso de registro adulterado, a resposta é:

```json
{
  "detail": "Registro adulterado: falha na verificação de integridade"
}
```

## 11. Testes automatizados

Os testes estão em tests/test_api.py e cobrem:

- criação do cofre;
- autenticação correta e incorreta;
- acesso a rotas protegidas;
- criação, leitura, atualização e exclusão de segredos;
- falha de integridade;
- cofre inexistente;
- segredo inexistente;
- payload inválido;
- suporte a Unicode;
- não vazamento do conteúdo da senha no banco em memória;
- documentação OpenAPI.

Também existem testes criptográficos em tests/test_cripto.py.

## 12. Validação executada

A suíte de testes foi executada com sucesso no ambiente local, com resultado verificado:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py
```

Resultado obtido:

- 53 testes passaram
- 0 falhas

## 13. Observações finais

O projeto cumpre os requisitos de confidencialidade, integridade e autenticação para o cenário didático proposto. Ele usa técnicas reais de criptografia, validação no nível de rota e persistência em banco relacional com dados protegidos por criptografia. A solução foi pensada para demonstrar o uso seguro de senhas em aplicações web, com foco em boas práticas de segurança e na lógica exigida pelo enunciado.
