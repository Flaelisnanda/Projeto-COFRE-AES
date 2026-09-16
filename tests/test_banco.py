"""Exercita o cliente real do Supabase com transporte HTTP simulado."""
import importlib
import sys
from datetime import datetime

import httpx
from supabase import ClientOptions, create_client


def test_contrato_do_banco(monkeypatch):
    requisicoes = []

    def responder(request):
        requisicoes.append(request)
        return httpx.Response(200, json=[])

    transporte = httpx.Client(transport=httpx.MockTransport(responder))
    cliente = create_client("https://laboratorio.supabase.co", "chave-ficticia",
                            options=ClientOptions(httpx_client=transporte))
    monkeypatch.setenv("SUPABASE_URL", "https://laboratorio.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "chave-ficticia")
    monkeypatch.setattr("supabase.create_client", lambda *args: cliente)
    sys.modules.pop("app.banco", None)
    banco = importlib.import_module("app.banco")
    try:
        assert banco.buscar_cofre("cofre") is None
        assert banco.buscar_segredo("cofre", "segredo") is None
        assert banco.listar_segredos("cofre") == []
        assert requisicoes[-1].url.params["select"] == "id,titulo,usuario,url,criado_em"
        banco.inserir_cofre("cofre", "Nome", "sal", 210000, "nonce", "cripto", "tag")
        banco.inserir_segredo("cofre", "Titulo", segredo_id="segredo", nonce="nonce",
                              criptograma="", etiqueta="tag")
        import json
        registro = json.loads(requisicoes[-1].content)
        assert registro["criptograma"] == ""
        assert registro["id"] == "segredo"
        assert "senha" not in registro
        banco.atualizar_segredo("cofre", "segredo", "novo", "cripto", "tag")
        atualizacao = requisicoes[-1]
        assert atualizacao.method == "PATCH"
        assert atualizacao.url.params["cofre_id"] == "eq.cofre"
        assert atualizacao.url.params["id"] == "eq.segredo"
        assert datetime.fromisoformat(json.loads(atualizacao.content)["atualizado_em"]).tzinfo
        banco.remover_segredo("cofre", "segredo")
        assert requisicoes[-1].method == "DELETE"
        assert requisicoes[-1].url.params["cofre_id"] == "eq.cofre"
        assert requisicoes[-1].url.params["id"] == "eq.segredo"
    finally:
        transporte.close()
        sys.modules.pop("app.banco", None)
        import app
        if hasattr(app, "banco"):
            delattr(app, "banco")
