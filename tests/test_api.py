from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import cripto
from app.main import app, obter_banco


class BancoMemoria:
    def __init__(self):
        self.cofres = {}
        self.segredos = {}

    def inserir_cofre(self, identificador, nome, sal, iteracoes, nonce, criptograma, etiqueta):
        self.cofres[identificador] = dict(
            id=identificador, nome=nome, kdf_sal=sal,
            kdf_iteracoes=iteracoes, verificador_nonce=nonce,
            verificador_criptograma=criptograma, verificador_etiqueta=etiqueta,
        )

    def buscar_cofre(self, identificador):
        return self.cofres.get(identificador)

    def inserir_segredo(self, cofre_id, nome, **dados):
        identificador = dados.pop("segredo_id")
        self.segredos[cofre_id, identificador] = dict(id=identificador, **dados)

    def listar_segredos(self, cofre_id):
        return [s for (c, _), s in self.segredos.items() if c == cofre_id]

    def buscar_segredo(self, cofre_id, segredo_id):
        return self.segredos.get((cofre_id, segredo_id))

    def atualizar_segredo(self, cofre_id, segredo_id, nonce, criptograma, etiqueta):
        self.segredos[cofre_id, segredo_id].update(
            nonce=nonce, criptograma=criptograma, etiqueta=etiqueta
        )

    def remover_segredo(self, cofre_id, segredo_id):
        del self.segredos[cofre_id, segredo_id]


@pytest.fixture
def api():
    banco = BancoMemoria()
    app.dependency_overrides[obter_banco] = lambda: banco
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, banco
    app.dependency_overrides.clear()


@pytest.fixture
def cofre(api):
    client, banco = api
    resposta = client.post("/cofres", json={"nome": "Pessoal", "senha_mestra": "mestra"})
    assert resposta.status_code == 201
    return resposta.json()["id"]


AUTH = {"X-Senha-Mestra": "mestra"}
OPERACOES = [("post", "/abrir", None), ("post", "/segredos", {"titulo": "Email", "senha": "segredo"}),
             ("get", "/segredos", None), ("get", "/segredos/{id}", None),
             ("put", "/segredos/{id}", {"senha": "nova"}), ("delete", "/segredos/{id}", None)]


def test_ciclo_completo(api, cofre):
    client, banco = api
    url = f"/cofres/{cofre}/segredos"
    resposta = client.post(url, headers=AUTH, json={"titulo": "Email", "senha": "segredo"})
    assert resposta.status_code == 201
    identificador = resposta.json()["id"]
    registro = deepcopy(banco.segredos[cofre, identificador])
    assert "senha" not in registro
    assert "segredo" not in registro.values()
    lista = client.get(url, headers=AUTH)
    assert lista.status_code == 200
    assert lista.json() == [resposta.json()]
    alvo = f"{url}/{identificador}"
    leitura = client.get(alvo, headers=AUTH)
    assert leitura.status_code == 200
    assert leitura.json()["senha"] == "segredo"
    assert client.put(alvo, headers=AUTH, json={"senha": "nova"}).status_code == 200
    assert banco.segredos[cofre, identificador]["nonce"] != registro["nonce"]
    assert client.get(alvo, headers=AUTH).json()["senha"] == "nova"
    assert client.delete(alvo, headers=AUTH).status_code == 200
    assert client.get(alvo, headers=AUTH).status_code == 404


@pytest.mark.parametrize("metodo,sufixo,payload", OPERACOES)
@pytest.mark.parametrize("headers", [{}, {"X-Senha-Mestra": "errada"}])
def test_autenticacao_em_todas_as_rotas(api, cofre, metodo, sufixo, payload, headers):
    client, banco = api
    antes = deepcopy((banco.cofres, banco.segredos))
    url = f"/cofres/{cofre}" + sufixo.format(id=uuid4())
    assert client.request(metodo, url, headers=headers, json=payload).status_code == (401 if headers else 422)
    assert (banco.cofres, banco.segredos) == antes


@pytest.mark.parametrize("metodo,sufixo,payload", OPERACOES)
def test_cofre_inexistente(api, metodo, sufixo, payload):
    client, _ = api
    url = f"/cofres/{uuid4()}" + sufixo.format(id=uuid4())
    assert client.request(metodo, url, headers=AUTH, json=payload).status_code == 404


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
@pytest.mark.parametrize("identificador", [str(uuid4()), "inexistente"])
def test_segredo_inexistente(api, cofre, metodo, identificador):
    client, _ = api
    url = f"/cofres/{cofre}/segredos/{identificador}"
    assert client.request(metodo, url, headers=AUTH, json={"senha": "nova"}).status_code == 404


@pytest.mark.parametrize("metodo,sufixo,payload", OPERACOES)
def test_valueerror_verificador(api, cofre, monkeypatch, metodo, sufixo, payload):
    def falhar(*args):
        raise ValueError("detalhe privado")
    monkeypatch.setattr(cripto, "senha_mestra_correta", falhar)
    client, _ = api
    url = f"/cofres/{cofre}" + sufixo.format(id=uuid4())
    assert client.request(metodo, url, headers=AUTH, json=payload).status_code == 401


def test_segredo_adulterado(api, cofre):
    client, banco = api
    url = f"/cofres/{cofre}/segredos"
    identificador = client.post(url, headers=AUTH, json={"titulo": "Email", "senha": "abc"}).json()["id"]
    banco.segredos[cofre, identificador]["etiqueta"] = cripto.para_b64(bytes(16))
    resposta = client.get(f"{url}/{identificador}", headers=AUTH)
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Registro adulterado: falha na verificação de integridade"}


def test_validacao(api, cofre):
    client, _ = api
    for payload in [{}, {"nome": 123, "senha_mestra": "x"}, {"nome": "x", "senha_mestra": None}]:
        assert client.post("/cofres", json=payload).status_code == 422
    url = f"/cofres/{cofre}/segredos"
    for payload in [{}, {"titulo": "Email", "senha": 123}]:
        assert client.post(url, headers=AUTH, json=payload).status_code == 422
    assert client.put(f"{url}/{uuid4()}", headers=AUTH, json={}).status_code == 422


@pytest.mark.parametrize("metodo,sufixo,payload", OPERACOES)
def test_falha_banco(api, cofre, monkeypatch, metodo, sufixo, payload):
    client, banco = api
    def falhar(*args):
        raise RuntimeError("credencial privada")
    monkeypatch.setattr(banco, "buscar_cofre", falhar)
    url = f"/cofres/{cofre}" + sufixo.format(id=uuid4())
    resposta = client.request(metodo, url, headers=AUTH, json=payload)
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno do servidor"}


def test_docs(api):
    client, _ = api
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert sum(len(operacoes) for operacoes in schema["paths"].values()) == 7
    for path, operacoes in schema["paths"].items():
        if path == "/cofres":
            continue
        for operacao in operacoes.values():
            assert any(p["name"] == "X-Senha-Mestra" and p["in"] == "header" and p["required"]
                       for p in operacao["parameters"])


def test_criar_cofre_falha_banco(api, monkeypatch):
    client, banco = api
    def falhar(*args):
        raise RuntimeError("credencial privada")
    monkeypatch.setattr(banco, "inserir_cofre", falhar)
    resposta = client.post("/cofres", json={"nome": "Teste", "senha_mestra": "mestra"})
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno do servidor"}


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
def test_segredo_de_outro_cofre(api, cofre, metodo):
    client, _ = api
    outro = client.post("/cofres", json={"nome": "Outro", "senha_mestra": "mestra"}).json()["id"]
    segredo = client.post(f"/cofres/{outro}/segredos", headers=AUTH,
                          json={"titulo": "Privado", "senha": "secreta"}).json()["id"]
    resposta = client.request(metodo, f"/cofres/{cofre}/segredos/{segredo}",
                              headers=AUTH, json={"senha": "nova"})
    assert resposta.status_code == 404
    assert client.get(f"/cofres/{outro}/segredos/{segredo}", headers=AUTH).json()["senha"] == "secreta"


def test_abrir_cofre(api, cofre):
    client, _ = api
    assert client.post(f"/cofres/{cofre}/abrir", headers=AUTH).status_code == 200


def test_nonces_distintos_e_troca_de_criptogramas(api, cofre):
    client, banco = api
    url = f"/cofres/{cofre}/segredos"
    ids = [client.post(url, headers=AUTH, json={"titulo": titulo, "senha": "igual"}).json()["id"]
           for titulo in ("A", "B")]
    origem, destino = [banco.segredos[cofre, i] for i in ids]
    assert origem["nonce"] != destino["nonce"]
    assert origem["criptograma"] != destino["criptograma"]
    for campo in ("nonce", "criptograma", "etiqueta"):
        destino[campo] = origem[campo]
    resposta = client.get(f"{url}/{ids[1]}", headers=AUTH)
    assert resposta.status_code == 500
    assert "senha" not in resposta.json()
    assert client.get(f"{url}/{ids[0]}", headers=AUTH).json()["senha"] == "igual"


@pytest.mark.parametrize("metodo,sufixo,payload", OPERACOES)
def test_cofre_id_invalido(api, metodo, sufixo, payload):
    client, _ = api
    resposta = client.request(metodo, "/cofres/invalido" + sufixo.format(id=uuid4()),
                              headers=AUTH, json=payload)
    assert resposta.status_code == 404


def test_senha_unicode_e_vazia(api, cofre):
    client, _ = api
    url = f"/cofres/{cofre}/segredos"
    for senha in ("", "ação🔐"):
        resposta = client.post(url, headers=AUTH, json={"titulo": "Teste", "senha": senha})
        assert resposta.status_code == 201
        identificador = resposta.json()["id"]
        assert client.get(f"{url}/{identificador}", headers=AUTH).json()["senha"] == senha
