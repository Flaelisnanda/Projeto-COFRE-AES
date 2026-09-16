"""API do cofre de senhas. Execute com uvicorn app.main:app."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app import cripto
from app.modelos import AtualizarSegredo, NovoCofre, NovoSegredo


def obter_banco():
    # Adia a configuração externa até o uso e permite substituição nos testes.
    from app import banco

    return banco


app = FastAPI(title="Cofre AES")
Banco = Annotated[object, Depends(obter_banco)]


@app.exception_handler(Exception)
async def erro_interno(request: Request, exc: Exception):
    # Não exponha credenciais, dados criptográficos ou mensagens do provedor.
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})


def autenticar(
    cofre_id: str,
    banco: Banco,
    senha_mestra: Annotated[str, Header(alias="X-Senha-Mestra")],
) -> bytes:
    try:
        UUID(cofre_id)
    except ValueError as exc:
        raise HTTPException(404, "Cofre não encontrado") from exc
    cofre = banco.buscar_cofre(cofre_id)
    if cofre is None:
        raise HTTPException(404, "Cofre não encontrado")
    chave = cripto.derivar_chave(
        senha_mestra, cripto.de_b64(cofre["kdf_sal"]), cofre["kdf_iteracoes"]
    )
    try:
        correta = cripto.senha_mestra_correta(
            chave,
            cofre["verificador_nonce"],
            cofre["verificador_criptograma"],
            cofre["verificador_etiqueta"],
            cofre_id,
        )
    except ValueError as exc:
        raise HTTPException(401, "Senha mestra incorreta ou dados inválidos") from exc
    if not correta:
        raise HTTPException(401, "Senha mestra incorreta ou dados inválidos")
    return chave


Chave = Annotated[bytes, Depends(autenticar)]
ERROS = {401: {"description": "Autenticação inválida"},
         404: {"description": "Cofre ou segredo não encontrado"},
         500: {"description": "Erro interno do servidor"}}


def buscar_segredo(banco, cofre_id: str, segredo_id: str) -> dict:
    # O banco usa UUID; valores que não podem identificar uma linha são 404.
    try:
        segredo_id = str(UUID(segredo_id))
    except ValueError as exc:
        raise HTTPException(404, "Segredo não encontrado") from exc
    segredo = banco.buscar_segredo(cofre_id, segredo_id)
    if segredo is None:
        raise HTTPException(404, "Segredo não encontrado")
    return segredo


@app.post("/cofres", status_code=201, responses={500: ERROS[500]})
def criar_cofre(dados: NovoCofre, banco: Banco):
    cofre_id = str(uuid4())
    sal = cripto.gerar_sal()
    chave = cripto.derivar_chave(dados.senha_mestra, sal, cripto.ITERACOES_PADRAO)
    nonce, criptograma, etiqueta = cripto.criar_verificador(chave, cofre_id)
    banco.inserir_cofre(
        cofre_id, dados.nome, cripto.para_b64(sal), cripto.ITERACOES_PADRAO,
        nonce, criptograma, etiqueta,
    )
    return {"id": cofre_id, "nome": dados.nome}


@app.post("/cofres/{cofre_id}/abrir", responses=ERROS)
def abrir_cofre(cofre_id: str, chave: Chave):
    return {"mensagem": "Cofre aberto"}


@app.post("/cofres/{cofre_id}/segredos", status_code=201, responses=ERROS)
def criar_segredo(cofre_id: str, dados: NovoSegredo, chave: Chave, banco: Banco):
    segredo_id = str(uuid4())
    nonce, criptograma, etiqueta = cripto.cifrar(
        chave, dados.senha, cripto.montar_aad_segredo(cofre_id, segredo_id)
    )
    banco.inserir_segredo(
        cofre_id, dados.titulo, segredo_id=segredo_id, titulo=dados.titulo,
        usuario=dados.usuario, url=dados.url, nonce=nonce,
        criptograma=criptograma, etiqueta=etiqueta,
    )
    return {"id": segredo_id, "titulo": dados.titulo,
            "usuario": dados.usuario, "url": dados.url}


@app.get("/cofres/{cofre_id}/segredos", responses=ERROS)
def listar_segredos(cofre_id: str, chave: Chave, banco: Banco):
    campos = ("id", "titulo", "usuario", "url", "criado_em")
    return [{campo: item[campo] for campo in campos if campo in item}
            for item in banco.listar_segredos(cofre_id)]


@app.get("/cofres/{cofre_id}/segredos/{segredo_id}", responses=ERROS)
def ler_segredo(cofre_id: str, segredo_id: str, chave: Chave, banco: Banco):
    segredo = buscar_segredo(banco, cofre_id, segredo_id)
    try:
        senha = cripto.decifrar(
            chave, segredo["nonce"], segredo["criptograma"], segredo["etiqueta"],
            cripto.montar_aad_segredo(cofre_id, segredo["id"]),
        )
    except ValueError as exc:
        raise HTTPException(500, "Registro adulterado: falha na verificação de integridade") from exc
    return {"id": segredo["id"], "titulo": segredo["titulo"],
            "usuario": segredo.get("usuario"), "url": segredo.get("url"),
            "senha": senha}


@app.put("/cofres/{cofre_id}/segredos/{segredo_id}", responses=ERROS)
def atualizar_segredo(
    cofre_id: str, segredo_id: str, dados: AtualizarSegredo, chave: Chave, banco: Banco,
):
    segredo = buscar_segredo(banco, cofre_id, segredo_id)
    nonce, criptograma, etiqueta = cripto.cifrar(
        chave, dados.senha, cripto.montar_aad_segredo(cofre_id, segredo["id"])
    )
    banco.atualizar_segredo(cofre_id, segredo["id"], nonce, criptograma, etiqueta)
    return {"mensagem": "Segredo atualizado"}


@app.delete("/cofres/{cofre_id}/segredos/{segredo_id}", responses=ERROS)
def remover_segredo(cofre_id: str, segredo_id: str, chave: Chave, banco: Banco):
    segredo = buscar_segredo(banco, cofre_id, segredo_id)
    banco.remover_segredo(cofre_id, segredo["id"])
    return {"mensagem": "Segredo removido"}
