-- Schema do projeto Cofre AES
-- Ativar extensões necessárias
create extension if not exists pgcrypto;

create table if not exists cofres (
    id text primary key,
    nome text not null,
    kdf_sal text not null,
    kdf_iteracoes integer not null check (kdf_iteracoes > 0),
    verificador_nonce text not null,
    verificador_criptograma text not null,
    verificador_etiqueta text not null,
    criado_em timestamptz not null default now()
);

create table if not exists segredos (
    id uuid primary key default gen_random_uuid(),
    cofre_id text not null references cofres(id) on delete cascade,
    titulo text not null,
    usuario text,
    url text,
    nonce text not null,
    criptograma text not null,
    etiqueta text not null,
    criado_em timestamptz not null default now()
);

alter table cofres enable row level security;
alter table segredos enable row level security;

-- Política: cada usuário só pode acessar o cofre associado ao seu token.
create policy "cofres_mesmo_cofre"
on cofres
for all
using (
    id = (current_setting('request.jwt.claims', true)::jsonb ->> 'cofre_id')
)
with check (
    id = (current_setting('request.jwt.claims', true)::jsonb ->> 'cofre_id')
);

-- Política: segredos só podem ser acessados dentro do mesmo cofre.
create policy "segredos_mesmo_cofre"
on segredos
for all
using (
    cofre_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'cofre_id')
)
with check (
    cofre_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'cofre_id')
);

-- Observação:
-- O projeto deve injetar o claim 'cofre_id' no token JWT do usuário,
-- ou usar o padrão do supabase para autenticação por usuário/tenant.
-- Isso impede acesso cruzado entre cofres diferentes.
