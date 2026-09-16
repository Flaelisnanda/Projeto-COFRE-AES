import hashlib

import pytest

from app import cripto


def test_parametros_e_pbkdf2():
    sal = cripto.gerar_sal()
    assert len(sal) == 16
    assert sal != cripto.gerar_sal()
    assert cripto.ITERACOES_PADRAO >= 210_000
    chave = cripto.derivar_chave("ação🔐", sal, cripto.ITERACOES_PADRAO)
    assert chave == hashlib.pbkdf2_hmac("sha256", "ação🔐".encode(), sal, 210_000, dklen=32)
    nonce, texto, etiqueta = cripto.cifrar(chave, "teste", b"aad")
    assert len(cripto.de_b64(nonce)) == 12
    assert len(cripto.de_b64(etiqueta)) == 16
    assert cripto.decifrar(chave, nonce, texto, etiqueta, b"aad") == "teste"
    with pytest.raises(ValueError):
        cripto.decifrar(chave, nonce, texto, etiqueta, b"outro")


def test_aad_verificador():
    chave = cripto.derivar_chave("teste", cripto.gerar_sal(), 210_000)
    campos = cripto.criar_verificador(chave, "cofre")
    assert cripto.decifrar(chave, *campos, b"cofre") == "cofre-ok"
    assert cripto.senha_mestra_correta(chave, *campos, "cofre")
    assert not cripto.senha_mestra_correta(chave, *campos, "outro")
