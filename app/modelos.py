from pydantic import BaseModel
from typing import Optional


class NovoCofre(BaseModel):
    nome: str
    senha_mestra: str


class NovoSegredo(BaseModel):
    titulo: str
    usuario: Optional[str] = None
    url: Optional[str] = None
    senha: str


class AtualizarSegredo(BaseModel):
    senha: str
