import os

from dotenv import load_dotenv
from supabase import Client, create_client

from app.cripto import de_b64, para_b64

load_dotenv()  # lê o arquivo .env

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError(
        "Variáveis de ambiente ausentes: configure SUPABASE_URL e SUPABASE_KEY no arquivo .env"
    )

supabase: Client = create_client(supabase_url, supabase_key)


def _normalizar_b64(valor: bytes | str | None) -> str | None:
    """Converte bytes para Base64 para persistência segura no banco."""
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor
    return para_b64(valor)


# ---------------------------------------------------------------
# Cofres
# ---------------------------------------------------------------


def inserir_cofre(
    cofre_id: str,
    nome: str,
    kdf_sal: str | bytes,
    kdf_iteracoes: int,
    verificador_nonce: str | bytes,
    verificador_criptograma: str | bytes,
    verificador_etiqueta: str | bytes,
) -> None:
    """Grava um novo cofre. Usada pela rota POST /cofres."""
    supabase.table("cofres").insert({
        "id": cofre_id,
        "nome": nome,
        "kdf_sal": _normalizar_b64(kdf_sal),
        "kdf_iteracoes": kdf_iteracoes,
        "verificador_nonce": _normalizar_b64(verificador_nonce),
        "verificador_criptograma": _normalizar_b64(verificador_criptograma),
        "verificador_etiqueta": _normalizar_b64(verificador_etiqueta),
    }).execute()


def buscar_cofre(cofre_id: str) -> dict | None:
    """Busca um cofre pelo identificador. Devolve None se não existir."""
    resposta = supabase.table("cofres").select("*").eq("id", cofre_id).execute()
    registros = resposta.data
    if not registros:
        return None

    registro = dict(registros[0])
    if "kdf_sal" in registro and isinstance(registro["kdf_sal"], str):
        registro["kdf_sal_bytes"] = de_b64(registro["kdf_sal"])
    return registro


# ---------------------------------------------------------------
# Segredos
# ---------------------------------------------------------------

def inserir_segredo(
    cofre_id: str,
    nome: str,
    dados_cifrados: dict | None = None,
    *,
    segredo_id: str | None = None,
    titulo: str | None = None,
    usuario: str | None = None,
    url: str | None = None,
    nonce: str | bytes | None = None,
    criptograma: str | bytes | None = None,
    etiqueta: str | bytes | None = None,
) -> None:
    """Grava um novo segredo cifrado.

    Compatível com ambas as convenções de API:
    - inserir_segredo(cofre_id, nome, dados_cifrados)
    - inserir_segredo(segredo_id, cofre_id, titulo, usuario, url, nonce, criptograma, etiqueta)
    """
    if dados_cifrados is not None:
        titulo = dados_cifrados.get("titulo", nome)
        usuario = dados_cifrados.get("usuario")
        url = dados_cifrados.get("url")
        nonce = dados_cifrados.get("nonce")
        criptograma = dados_cifrados.get("criptograma")
        etiqueta = dados_cifrados.get("etiqueta")

    if not nonce or not criptograma or not etiqueta:
        raise ValueError("Dados cifrados incompletos: nonce, criptograma e etiqueta são obrigatórios")

    payload = {
        "cofre_id": cofre_id,
        "titulo": titulo or nome,
        "usuario": usuario,
        "url": url,
        "nonce": _normalizar_b64(nonce),
        "criptograma": _normalizar_b64(criptograma),
        "etiqueta": _normalizar_b64(etiqueta),
    }

    if segredo_id:
        payload["id"] = segredo_id

    supabase.table("segredos").insert(payload).execute()


def listar_segredos(cofre_id: str) -> list[dict]:
    resposta = (
        supabase.table("segredos")
        .select("id, titulo, usuario, url, criado_em")
        .eq("cofre_id", cofre_id)
        .execute()
    )
    return resposta.data


def buscar_segredo(cofre_id: str, segredo_id: str) -> dict | None:
    resposta = (
        supabase.table("segredos")
        .select("*")
        .eq("cofre_id", cofre_id)
        .eq("id", segredo_id)
        .execute()
    )
    registros = resposta.data
    return registros[0] if registros else None


def atualizar_segredo(
    cofre_id: str,
    segredo_id: str,
    nonce: str | bytes,
    criptograma: str | bytes,
    etiqueta: str | bytes,
) -> None:
    supabase.table("segredos").update({
        "nonce": _normalizar_b64(nonce),
        "criptograma": _normalizar_b64(criptograma),
        "etiqueta": _normalizar_b64(etiqueta),
    }).eq("cofre_id", cofre_id).eq("id", segredo_id).execute()


def remover_segredo(cofre_id: str, segredo_id: str) -> None:
    supabase.table("segredos").delete().eq("cofre_id", cofre_id).eq("id", segredo_id).execute()