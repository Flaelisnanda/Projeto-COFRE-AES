# Cofre de Senhas Corporativo

Projeto de Criptografia Aplicada: API FastAPI, AES-256-GCM, PBKDF2 e Supabase,
conforme as Seções 8 a 14 do documento Projeto_Cofre_AES.

## Equipe

Preencher os nomes dos integrantes e a identificação da equipe antes da entrega.

## Instalação e execução

Use Python 3.10 ou superior. A partir da pasta `Projeto-COFRE-AES`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.exemplo .env
```

Preencha `.env` com a URL e a chave pública anon/publishable do projeto da equipe.
Execute `sql/esquema.sql` no SQL Editor de um projeto Supabase novo.
As políticas `laboratorio` permitem acesso ao papel `anon`, conforme a Seção 8.3.
Não publique `.env`.

```bash
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/docs. Use **Try it out** e preencha o cabeçalho
`X-Senha-Mestra` em todas as operações, exceto na criação de cofre.

O SQL é para instalação nova: não modifica tabelas já existentes. A versão
anterior usava IDs de cofre em texto e não tinha `atualizado_em`; bancos nessa
situação precisam de migração antes do uso com esta versão. O AAD do verificador
agora é apenas o ID do cofre, como exige o documento. Verificadores antigos que
usavam `cofre_id|verificador` precisam ser migrados com a senha-mestra correta;
esta versão não os aceita automaticamente. Nenhum banco remoto foi alterado.

## Rotas e exemplos

Os IDs abaixo representam os UUIDs retornados pela API. As senhas dos exemplos
são fictícias. Os campos `usuario` e `url` são opcionais.

| Método e caminho | Corpo de exemplo | Resposta de sucesso |
| --- | --- | --- |
| POST `/cofres` | `{"nome":"Equipe","senha_mestra":"exemplo-didatico"}` | 201: `{"id":"<cofre_id>","nome":"Equipe"}` |
| POST `/cofres/{id}/abrir` | Sem corpo | 200: `{"mensagem":"Cofre aberto"}` |
| POST `/cofres/{id}/segredos` | `{"titulo":"Email","senha":"senha-de-exemplo"}` | 201: `{"id":"<segredo_id>","titulo":"Email","usuario":null,"url":null}` |
| GET `/cofres/{id}/segredos` | Sem corpo | 200: lista com `id`, `titulo`, `usuario`, `url`, `criado_em` |
| GET `/cofres/{id}/segredos/{sid}` | Sem corpo | 200: `{"id":"<segredo_id>","titulo":"Email","usuario":null,"url":null,"senha":"senha-de-exemplo"}` |
| PUT `/cofres/{id}/segredos/{sid}` | `{"senha":"nova-senha-de-exemplo"}` | 200: `{"mensagem":"Segredo atualizado"}` |
| DELETE `/cofres/{id}/segredos/{sid}` | Sem corpo | 200: `{"mensagem":"Segredo removido"}` |

Abrir o cofre apenas verifica a senha; não cria sessão nem mantém chave em memória
entre requisições. A senha-mestra deve ser enviada novamente nas demais operações.

| Código | Significado |
| --- | --- |
| 200 | Abertura, leitura, listagem, atualização ou exclusão bem-sucedida |
| 201 | Cofre ou segredo criado |
| 401 | Senha-mestra incorreta ou falha do verificador |
| 404 | Cofre ou segredo inexistente; inclui identificador inválido |
| 422 | Payload inválido ou cabeçalho obrigatório ausente |
| 500 | Registro adulterado após autenticação válida, ou falha interna |

A falha de integridade retorna
`{"detail":"Registro adulterado: falha na verificação de integridade"}` sem texto
claro. Outras falhas internas retornam uma mensagem genérica, sem detalhes do provedor.
A autenticação precede o acesso ao segredo: para consultar a existência de um segredo
em um cofre existente é necessário fornecer a senha correta.

## Organização

- `app/main.py`: rotas, autenticação e tratamento HTTP.
- `app/modelos.py`: modelos Pydantic.
- `app/cripto.py`: criptografia com PyCryptodome, sem HTTP ou banco.
- `app/banco.py`: persistência no Supabase, sem lógica criptográfica.
- `banco.py`: compatibilidade com imports antigos.
- `tests/`: testes automatizados.
- `testes/`: resultados, roteiro manual e evidências.

## Parâmetros criptográficos

PBKDF2 usa HMAC-SHA-256, 210.000 iterações e sal aleatório de 16 bytes por cofre.
O sal impede que senhas iguais gerem a mesma chave em cofres distintos; as iterações
encarecem tentativas de adivinhação e são persistidas para permitir evolução futura.
A chave derivada tem 32 bytes para AES-256.

AES-GCM usa nonce aleatório de 12 bytes novo em cada cifragem, inclusive atualizações,
e etiqueta de 16 bytes. A etiqueta é verificada antes de devolver o texto claro.
O AAD dos segredos é `cofre_id|segredo_id`; o do verificador é apenas `cofre_id`.
O verificador cifra a frase `cofre-ok`. Campos binários são persistidos em Base64.

## Limitações

O projeto protege senhas contra cópias do banco e detecta adulteração de registros.
Não protege um servidor comprometido durante o uso, nem compensa senha-mestra fraca
ou divulgada. Não há auditoria individual. Título, usuário e URL ficam em claro:
quem obtiver o banco saberá quais serviços são usados, mesmo sem ler suas senhas.
Senha-mestra e chave derivada não são persistidas nem mantidas entre requisições.

As políticas amplas são uma escolha didática exigida no enunciado. Quem possui a
chave pública pode consultar ou alterar os registros diretamente. Em produção,
o acesso ao banco precisaria de restrições e o transporte HTTP precisaria de HTTPS.

## Verificação

```bash
python3 -m pytest -v
```

Os testes usam criptografia real, banco em memória e, para a camada de persistência,
o cliente Supabase com transporte HTTP simulado. Não acessam o banco remoto.
Confira `testes/resultados.md` para os resultados observados e as etapas manuais
que ainda precisam ser executadas no Swagger/Supabase.
