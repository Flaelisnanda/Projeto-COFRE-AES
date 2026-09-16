# Resultados de verificação

## Execução automatizada

Resultado: **56 testes passaram**. Evidência integral: [pytest.txt](evidencias/pytest.txt).
Foram usados FastAPI TestClient, PyCryptodome real, banco em memória e cliente
Supabase com transporte HTTP simulado. Não houve acesso ao Supabase remoto.

O ambiente disponível tem Python 3.9.2; os testes passaram nele, com dois avisos
de descontinuação do cliente Supabase. O documento exige Python 3.10 ou superior
para instalação e execução, conforme o README. Esta execução não valida outro
interpretador nem a interface interativa do Swagger em um navegador.

| Teste obrigatório da Seção 12 | Resultado local observado | Evidência remota |
| --- | --- | --- |
| 1. Nonces distintos | Duas senhas iguais produziram nonces e criptogramas diferentes; atualização também renovou o nonce | Pendente consulta ao Supabase |
| 2. Senha-mestra incorreta | 401 nas seis rotas protegidas, sem conteúdo do segredo | Pendente captura do Swagger |
| 3. O que o invasor enxerga | Registros simulados sem campo de senha em claro; listagem somente de metadados | Pendente SQL direto no Supabase |
| 4. Registro adulterado | Etiqueta adulterada resultou em 500 com mensagem de integridade, sem texto claro | Pendente adulteração pelo SQL Editor |
| 5. Troca de criptogramas | Copiar nonce, criptograma e etiqueta de A para B resultou em 500 na leitura de B | Pendente execução no Supabase |

Também foram verificados: criação 201, abertura/leitura/atualização/exclusão 200,
cofre e segredo inexistentes 404, payload e cabeçalho ausente 422, falha interna 500,
ValueError no verificador 401, isolamento entre cofres, senhas Unicode e vazias,
parâmetros PBKDF2, AAD do verificador, filtros de banco e timestamp de atualização.
`/docs` responde 200 e o OpenAPI declara sete operações e o cabeçalho obrigatório.

## Roteiro manual pendente

Configure `.env`, aplique o esquema em um projeto Supabase novo e inicie
`uvicorn app.main:app --reload`. Use apenas dados fictícios nas evidências.

1. Em `/docs`, crie um cofre e anote seu ID (201). Repita com payload incompleto (422).
2. Abra o cofre com a senha correta (200), incorreta (401), sem cabeçalho (422)
   e com um UUID de cofre inexistente (404).
3. Cadastre dois segredos com a mesma senha e títulos diferentes (201).
4. Liste os metadados e leia as senhas (200). Atualize uma senha (200) e confira
   o novo valor e a mudança do nonce no banco.
5. Repita criação, listagem, leitura, atualização e exclusão com senha errada (401).
   Repita com cabeçalho ausente (422) e cofre inexistente (404).
6. Tente ler, atualizar e excluir um segredo inexistente com senha correta (404).
   Envie payloads inválidos em POST e PUT (422).
7. Consulte no SQL Editor e salve a saída para os testes 1 e 3:

   ```sql
   select id, titulo, usuario, nonce, criptograma, etiqueta
   from public.segredos;
   ```

8. Altere o criptograma de um segredo de teste, garantindo que o caractere mude:

   ```sql
   update public.segredos
   set criptograma =
     (case when left(criptograma, 1) = 'X' then 'Y' else 'X' end)
     || substring(criptograma from 2)
   where id = '<UUID do segredo de teste>';
   ```

   Leia-o com a senha-mestra correta: esperado 500 indicando registro adulterado,
   sem senha no corpo. Use um segredo com senha não vazia nesse teste.
9. Em dois novos segredos do mesmo cofre, copie os três campos de um para o outro:

   ```sql
   update public.segredos as destino
   set nonce = origem.nonce,
       criptograma = origem.criptograma,
       etiqueta = origem.etiqueta
   from public.segredos as origem
   where origem.id = '<UUID de origem>'
     and destino.id = '<UUID de destino>';
   ```

   Leia o destino: esperado 500. A origem deve continuar legível (200).
10. Exclua um segredo (200) e confirme que a leitura seguinte retorna 404.
11. Salve capturas em `testes/evidencias/` e registre os resultados reais aqui.

O aceite manual permanece pendente até essas etapas serem executadas no ambiente
configurado. Não há capturas ou resultados remotos presumidos neste relatório.
