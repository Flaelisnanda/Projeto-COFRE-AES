"""Módulo de criptografia do projeto."""

import base64
import hashlib
from os import urandom as get_random_bytes

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERACOES_PADRAO = 210_000
TAMANHO_CHAVE = 32
TAMANHO_SAL = 16
TAMANHO_NONCE = 12


def para_b64(dados: bytes) -> str:
    """Converte bytes para string em Base64."""
    return base64.b64encode(dados).decode("utf-8")


def de_b64(valor: str) -> bytes:
    """Converte string em Base64 para bytes."""
    return base64.b64decode(valor.encode("utf-8"))


def gerar_sal() -> bytes:
    """Gera um salt aleatório para uso na derivação da chave."""
    return get_random_bytes(TAMANHO_SAL)


def derivar_chave(senha_mestra: str, sal: bytes, iteracoes: int) -> bytes:
    """Deriva uma chave criptográfica a partir de uma senha e um salt."""
    senha_bytes = senha_mestra.encode("utf-8")
    return hashlib.pbkdf2_hmac(
        "sha256",
        senha_bytes,
        sal,
        iteracoes,
        dklen=TAMANHO_CHAVE,
    )


def montar_aad_segredo(cofre_id: str, segredo_id: str) -> bytes:
    """Monta o AAD para um segredo no formato 'cofre_id|segredo_id'."""
    return f"{cofre_id}|{segredo_id}".encode("utf-8")


def cifrar(chave: bytes, texto_claro: bytes | str, aad: bytes | str) -> tuple[str, str, str]:
    """Criptografa um texto com AES-GCM usando um nonce novo em cada chamada."""
    if isinstance(texto_claro, str):
        texto_claro = texto_claro.encode("utf-8")
    if isinstance(aad, str):
        aad = aad.encode("utf-8")

    nonce = get_random_bytes(TAMANHO_NONCE)
    cripto = AESGCM(chave).encrypt(nonce, texto_claro, aad)
    texto_criptografado = cripto[:-16]
    etiqueta = cripto[-16:]
    return para_b64(nonce), para_b64(texto_criptografado), para_b64(etiqueta)


def decifrar(
    chave: bytes,
    nonce_b64: str,
    cripto_b64: str,
    etiqueta_b64: str,
    aad: bytes | str,
) -> bytes:
    """Descriptografa um texto com AES-GCM e deixa ValueError subir."""
    if isinstance(aad, str):
        aad = aad.encode("utf-8")

    nonce = de_b64(nonce_b64)
    texto_criptografado = de_b64(cripto_b64)
    etiqueta = de_b64(etiqueta_b64)

    try:
        return AESGCM(chave).decrypt(nonce, texto_criptografado + etiqueta, aad)
    except InvalidTag as exc:
        raise ValueError("Dados criptografados inválidos ou AAD incorreto") from exc


def criar_verificador(chave: bytes, cofre_id: str) -> tuple[str, str, str]:
    """Cria um verificador para validar a senha mestra do cofre."""
    aad = montar_aad_segredo(cofre_id, "verificador")
    return cifrar(chave, "cofre-ok", aad)


def senha_mestra_correta(
    chave: bytes,
    nonce: str,
    cripto: str,
    etiqueta: str,
    cofre_id: str,
) -> bool:
    """Retorna True se a senha mestra for correta, e False em caso de dado inválido."""
    aad = montar_aad_segredo(cofre_id, "verificador")
    try:
        texto = decifrar(chave, nonce, cripto, etiqueta, aad)
    except ValueError:
        return False
    return texto == b"cofre-ok"
