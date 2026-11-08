# DriveNow — API de um stand de carros

[![CI](https://github.com/diogofcpereira/isla-dwfa-ecommerce/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/diogofcpereira/isla-dwfa-ecommerce/actions/workflows/ci.yml)

**Desenvolvimento Web Full-stack Avançado** · Mestrado em Engenharia Informática · ISLA Gaia · 2026/27 · Projeto M1

## O domínio

O DriveNow é a API de um stand de carros. O catálogo tem marcas e viaturas (modelo, versão, ano, combustível, preço e stock) e é público. Há dois papéis: o **cliente**, qualquer utilizador autenticado, que só vê e mexe no que é seu (perfil, encomendas, linhas e pagamentos); e o **gestor**, do grupo `gestores`, que gere o catálogo e vê tudo. O fluxo de negócio é a encomenda: o cliente cria-a com as linhas (viatura e quantidade) num só pedido, numa transação que verifica e desconta o stock, e depois paga-a (`POST /api/v1/orders/{id}/pay/`), o que regista o pagamento e passa a encomenda de pendente a paga; pagar de novo dá 409.

## Grupo

| Membro | Nº | Recurso individual |
|---|---|---|
| Diogo Pereira | `a22604547` | Delivery — entregas (`/api/v1/deliveries/`) |
| Filipe Cardoso | `a22601943` | Review — avaliações de viaturas (`/api/v1/reviews/`) |
| Rúben Afonso | `a22605044` | TestDrive — marcações de test drive (`/api/v1/test-drives/`) |

Quem fez o quê, com links para os commits e pull requests: [`docs/m1.md`](docs/m1.md). As decisões: [`docs/decisions.md`](docs/decisions.md).

## Como correr (num clone limpo)

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/), Docker Compose v2 e Git.

```sh
git clone https://github.com/diogofcpereira/isla-dwfa-ecommerce.git
cd isla-dwfa-ecommerce
cp .env.example .env                 # nunca commitar o .env
docker compose up -d                 # PostgreSQL 16; docker compose ps mostra "healthy"
uv sync
uv run python manage.py migrate
uv run python manage.py seed         # dados de demonstração (pode correr várias vezes)
uv run python manage.py runserver    # http://localhost:8000/api/docs/
```

Testes e verificações (as mesmas do CI):

```sh
uv run ruff check . && uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
uv run pytest                        # na primeira vez: uv run pytest --create-db
```

Porta 5432 ocupada? `ports: ["5433:5432"]` no `compose.yaml` e `:5433` no `DATABASE_URL` do `.env`.

## Credenciais de demonstração

Criadas pelo `manage.py seed`. Só existem em desenvolvimento.

| Utilizador | Password | Papel |
|---|---|---|
| `gestor` | `drivenow-demo-2026` | gestor (grupo `gestores`) |
| `ana`, `bruno`, `carla` | `drivenow-demo-2026` | clientes, cada um com uma encomenda pendente, uma paga, uma entregue e uma cancelada |

Login: `POST /api/v1/auth/token/ {"username": "ana", "password": "drivenow-demo-2026"}` devolve o `access` e o `refresh`. No Swagger (`/api/docs/`), carrega em **Authorize** e cola o `access`.

## A API

Tudo sob `/api/v1/`, com paginação (20 por página), filtros, pesquisa (`?search=`) e ordenação (`?ordering=`). Os erros seguem a RFC 9457 (`application/problem+json`). O `schema.yaml` está commitado e o Swagger em `/api/docs/`.

| Recurso | Endpoints |
|---|---|
| Marcas e viaturas | `/brands/`, `/cars/` (ex.: `/cars/?fuel=electric&max_price=45000`) |
| Clientes | `/customers/` (o cliente vê e edita o seu perfil) |
| Encomendas | `/orders/` (criar com `items`), `/orders/{id}/pay/`, `/order-items/` |
| Pagamentos | `/payments/` (só leitura) |
| Autenticação | `/auth/token/`, `/auth/token/refresh/`, `/auth/logout/`, `/me/` |
| Entregas (Diogo) | `/deliveries/`, `/deliveries/{id}/ship/`, `/deliveries/{id}/complete/` |
| Avaliações (Filipe) | `/reviews/`, `/reviews/{id}/moderate/` |
| Test drives (Rúben) | `/test-drives/`, `/test-drives/{id}/confirm/`, `/decline/`, `/cancel/` |

## Declaração de IA

Usámos IA generativa (Claude, da Anthropic) neste projeto:

- **O quê e onde:** usámos IA generativa (Claude, da Anthropic) como ferramenta de apoio no M1. O Diogo usou-a para preparar o guia do grupo: a divisão das tarefas por membro e o código das partes 1 a 6 (adaptação do domínio, API, testes e seed), que o grupo seguiu como guia partilhado. Os recursos individuais foram feitos por cada membro, a partir da especificação do guia.
- **Como trabalhámos:** cada membro aplicou, leu, testou e fez commit da sua parte e do seu recurso, com o seu nome; a divisão está no [`docs/m1.md`](docs/m1.md).
- **Como foi verificado:** ruff, `makemigrations --check`, a suite de testes (todos verdes), `check --deploy` com `config.settings.prod`, o `seed` num clone limpo e o fluxo de ponta a ponta com `curl` (login → encomenda com linhas → pagar → 409 ao pagar de novo → logout).
- **Recurso Delivery (Diogo):** O código do recurso (modelo, migração gerada com `makemigrations`, serializer, permissões, serviços `ship`/`complete`, viewset e testes) foi preparado com o apoio do Claude (claude.ai) no guia do M1, tal como o das partes 1 a 6; o Diogo aplicou-o na app `deliveries`, leu-o, testou-o e fez os commits. Quando o CI do push falhou por faltar a linha final em 10 ficheiros, corrigiu-o com `ruff format` num commit à parte. Depois da auditoria, corrigiu dois casos com testes novos: uma entrega concluída já não se altera (409) e dois pedidos simultâneos para a mesma encomenda dão 400 em vez de 500. Verificado com os testes do recurso, o ruff, o `makemigrations --check`, o `sqlmigrate` da migração e pedidos `curl`, com os quais confirmou que concluir uma entrega passa a encomenda a entregue e que repetir dá 409.
- **Recurso Review (Filipe):** O código do recurso (modelo, migração gerada com makemigrations, serializer, permissões, viewset com a ação moderate e testes) foi preparado com o apoio do Claude (claude.ai) no guia do M1, tal como o das partes 1 a 6; o Filipe aplicou-o na app reviews, leu-o, testou-o e fez os commits. Usou também o Claude para rever os diffs das partes 2 e 5, e o Claude Code fez uma auditoria final ao projeto, em modo só de leitura. Verificado com os testes do recurso, o ruff, o makemigrations --check, o spectacular --validate e pedidos curl.
- **Recurso Test drives (Rúben):** O código do recurso (modelo, serializer, permissões, serviço, views e testes) foi preparado com o apoio do Claude (claude.ai) no guia do M1; o Rúben aplicou-o na app `testdrives`, leu-o, testou-o e fez os commits. Verificado com os testes do recurso, o ruff, o `makemigrations --check` e pedidos `curl`.
