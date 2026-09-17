import requests

BASE_URL = 'http://127.0.0.1:8000'
SENHA_MESTRA = 'minha-senha-secreta'


def imprimir(label, resposta):
    print(f'--- {label} ---')
    print('status:', resposta.status_code)
    try:
        print(resposta.json())
    except ValueError:
        print(resposta.text)
    print()


# 1) Criar cofre
resp = requests.post(
    f'{BASE_URL}/cofres',
    json={'nome': 'Meu cofre', 'senha_mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Criar cofre', resp)
cofre_id = resp.json()['id']

# 2) Abrir cofre
resp = requests.post(
    f'{BASE_URL}/cofres/{cofre_id}/abrir',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Abrir cofre', resp)

# 3) Criar segredo
resp = requests.post(
    f'{BASE_URL}/cofres/{cofre_id}/segredos',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    json={
        'titulo': 'Email',
        'usuario': 'meu@email.com',
        'url': 'https://example.com',
        'senha': 'Nanda777',
    },
    timeout=10,
)
imprimir('Criar segredo', resp)
segredo_id = resp.json()['id']

# 4) Listar segredos
resp = requests.get(
    f'{BASE_URL}/cofres/{cofre_id}/segredos',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Listar segredos', resp)

# 5) Ler segredo
resp = requests.get(
    f'{BASE_URL}/cofres/{cofre_id}/segredos/{segredo_id}',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Ler segredo', resp)

# 6) Atualizar segredo
resp = requests.put(
    f'{BASE_URL}/cofres/{cofre_id}/segredos/{segredo_id}',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    json={'senha': 'Nanda123'},
    timeout=10,
)
imprimir('Atualizar segredo', resp)

# 7) Ler novamente para confirmar atualização
resp = requests.get(
    f'{BASE_URL}/cofres/{cofre_id}/segredos/{segredo_id}',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Ler segredo atualizado', resp)

# 8) Deletar segredo
resp = requests.delete(
    f'{BASE_URL}/cofres/{cofre_id}/segredos/{segredo_id}',
    headers={'X-Senha-Mestra': SENHA_MESTRA},
    timeout=10,
)
imprimir('Deletar segredo', resp)
