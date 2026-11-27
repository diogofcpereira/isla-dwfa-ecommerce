# DriveNow — um stand de carros (API + SPA)

[![CI](https://github.com/diogofcpereira/isla-dwfa-ecommerce/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/diogofcpereira/isla-dwfa-ecommerce/actions/workflows/ci.yml)

**Desenvolvimento Web Full-stack Avançado** · Mestrado em Engenharia Informática · ISLA Gaia · 2026/27 · Projeto M2

## O domínio

O DriveNow é um stand de carros. O catálogo tem marcas e viaturas (modelo, versão, ano, combustível, preço e stock) e é público. Há dois papéis: o **cliente**, qualquer utilizador autenticado, que só vê e mexe no que é seu (perfil, encomendas, entregas, avaliações e test drives); e o **gestor**, do grupo `gestores`, que gere o catálogo e vê tudo. O fluxo de negócio é a encomenda: o cliente cria-a com as linhas (viatura e quantidade) num só pedido, numa transação que verifica e desconta o stock, e depois paga-a, o que regista o pagamento e passa a encomenda de pendente a paga; pagar de novo dá 409.

No M2 o DriveNow ganhou uma SPA (Vue 3 + TypeScript, em `frontend/`) com o cliente da API gerado a partir do `schema.yaml`, e arranca inteiro em contentores com `compose.prod.yaml`: PostgreSQL, a API com Gunicorn e o Nginx a servir a SPA e a fazer proxy da API.

## Grupo

| Membro | Nº | Recurso individual | Ecrã na SPA |
|---|---|---|---|
| Diogo Pereira | `a22604547` | Delivery — entregas (`/api/v1/deliveries/`) | `/deliveries` (acompanhar; o gestor expede e conclui) e `/deliveries/new` (só gestores) |
| Filipe Cardoso | `a22601943` | Review — avaliações de viaturas (`/api/v1/reviews/`) | `/reviews` (avaliar o que comprou, editar, apagar) e `/reviews/moderation` (só gestores) |
| Rúben Afonso | `a22605044` | TestDrive — marcações de test drive (`/api/v1/test-drives/`) | `/test-drives` (marcar, pesquisar, cancelar; o gestor confirma e recusa) |

Quem fez o quê, com links: [`docs/m1.md`](docs/m1.md) e [`docs/m2.md`](docs/m2.md). As decisões: [`docs/decisions.md`](docs/decisions.md).

## Correr como em produção (num clone limpo)

Requisitos: Docker Compose v2 e Git. Nada mais: o Python e o Node ficam dentro das imagens.

```sh
git clone https://github.com/diogofcpereira/isla-dwfa-ecommerce.git
cd isla-dwfa-ecommerce
cp .env.example .env                                                   # nunca commitar o .env
docker compose -f compose.prod.yaml up --build -d --wait               # db, backend e web "healthy"
docker compose -f compose.prod.yaml exec backend python manage.py migrate
docker compose -f compose.prod.yaml exec backend python manage.py seed # dados de demonstração
```

Abrir **http://localhost** (a SPA). A API está em http://localhost/api/v1/, o Swagger em http://localhost/api/docs/ e o admin em http://localhost/admin/. Porta 80 ocupada? `WEB_PORT=8080` no `.env` e http://localhost:8080. Para desligar: `docker compose -f compose.prod.yaml down` (com `-v` apaga também a base de dados).

Os emails ao cliente sobre as entregas (agendada, saiu do stand, entregue) vão para a consola: `docker compose -f compose.prod.yaml logs backend`.

O compose local é HTTP: o `.env.example` traz `DJANGO_HTTPS=False`. Em `settings.prod` o HTTPS (redirect, cookies `Secure`, HSTS) está ligado por omissão.

## Desenvolvimento

Requisitos: Python 3.13, [uv](https://docs.astral.sh/uv/), Node 22 e Docker Compose v2.

```sh
cp .env.example .env
docker compose up -d                 # só o PostgreSQL 16 (projeto dwfa-grupo)
uv sync
uv run python manage.py migrate
uv run python manage.py seed
uv run python manage.py runserver    # API em http://localhost:8000 (Swagger em /api/docs/)

cd frontend
cp .env.example .env                 # VITE_API_URL=http://localhost:8000
npm ci
npm run dev                          # SPA em http://localhost:5173
```

Depois de mudar um serializer: `uv run python manage.py spectacular --file schema.yaml --validate` e `cd frontend && npm run gen:api` (o CI falha se o `schema.yaml` ou o `src/api/schema.d.ts` ficarem desatualizados).

Verificações (as mesmas do CI):

```sh
uv run ruff check . && uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
uv run pytest --cov                  # cobertura: falha abaixo de 95% (na 1.ª vez: --create-db)

cd frontend
npm run type-check && npm run check:lint && npm run check:format
npm run test:coverage                # Vitest com cobertura mínima (relatório em coverage/)
npm run build
```

Testes e2e (Playwright), contra os contentores já a correr e com o `seed` feito (como no CI):

```sh
cd frontend
npx playwright install chromium      # só na primeira vez: descarrega o browser
npm run test:e2e                     # 3 testes num Chromium, contra http://localhost
```

Porta 5432 ocupada? `ports: ["5433:5432"]` no `compose.yaml` e `:5433` no `DATABASE_URL` do `.env`.

## Credenciais de demonstração

Criadas pelo `manage.py seed` (em dev e no compose local). Não são para uma produção a sério.

| Utilizador | Password | Papel |
|---|---|---|
| `gestor` | `drivenow-demo-2026` | gestor (grupo `gestores`): painel da viatura, entregas, moderação, confirmar test drives |
| `ana`, `bruno`, `carla` | `drivenow-demo-2026` | clientes, cada um com uma encomenda pendente, uma paga, uma entregue e uma cancelada |

## A SPA

| Rota | Quem | O quê |
|---|---|---|
| `/cars` | todos | catálogo com pesquisa, combustível e página no URL (`?search=golf&fuel=hybrid&page=2`) |
| `/cars/:id` | todos | detalhe; o gestor muda preço, stock e "à venda" com erros por campo |
| `/login` | todos | entrar; volta à rota pedida (`?next=`) |
| `/orders`, `/orders/new` | autenticado | as minhas encomendas (pagar, apagar, 409); nova encomenda com várias linhas e erros por linha |
| `/deliveries`, `/deliveries/new` | autenticado · gestor | entregas (Diogo); o gestor vê o resumo por estado e as em atraso (`?overdue=true`) |
| `/reviews`, `/reviews/moderation` | autenticado · gestor | avaliações (Filipe) |
| `/test-drives` | autenticado | test drives (Rúben) |

A sessão sobrevive a um F5 (o refresh fica no `localStorage`, o access só em memória); uma rota privada sem sessão leva ao login e de volta; um cliente numa rota de gestor vai para `/forbidden` — e a API recusa na mesma (401/403/404).

## Qualidade (extras do M2)

Além dos pontos do enunciado, o CI garante em cada push:

| | Como | Onde se vê |
|---|---|---|
| Contrato API ↔ SPA | `schema.yaml` e `schema.d.ts` regenerados sem diferenças | jobs `test` e `frontend` |
| Cobertura de testes | backend ≥ 95% (`pytest --cov`), frontend com mínimos por métrica (`test:coverage`) | resumo de cada run · artefacto `cobertura-frontend` |
| Acessibilidade | regras no lint e testes axe-core (WCAG 2.1 AA); atalho "Saltar para o conteúdo" e foco ao mudar de ecrã | `check:lint`, `src/views/__tests__/a11y.spec.ts` |
| Arranque em contentores | clone limpo → `up --build` → `migrate` → `seed` → `check --deploy` (HTTPS) → testes por HTTP | job `docker` |
| Segurança | `Content-Security-Policy` na SPA, imagens com as correções de segurança, relatório do Trivy | job `docker` · `frontend/nginx/` |
| Percurso no browser | 3 testes Playwright num Chromium, contra os contentores: catálogo e F5; login, sessão e `/forbidden`; encomenda → pagamento → entrega com dois utilizadores. Falham com um erro de JavaScript ou da CSP | job `docker` · `frontend/e2e/` · artefacto `playwright-report` se falhar |

## A API

Tudo sob `/api/v1/`, com paginação (20 por página), filtros, pesquisa (`?search=`) e ordenação (`?ordering=`). Os erros seguem a RFC 9457 (`application/problem+json`, erros por campo em `errors`). O `schema.yaml` está commitado e o Swagger em `/api/docs/`.

| Recurso | Endpoints |
|---|---|
| Marcas e viaturas | `/brands/`, `/cars/` (ex.: `/cars/?fuel=electric&max_price=45000`) |
| Clientes | `/customers/` (o cliente vê e edita o seu perfil) |
| Encomendas | `/orders/` (criar com `items`), `/orders/{id}/pay/`, `/order-items/` |
| Pagamentos | `/payments/` (só leitura) |
| Autenticação | `/auth/token/`, `/auth/token/refresh/`, `/auth/logout/`, `/me/` |
| Entregas (Diogo) | `/deliveries/` (`?overdue=true`), `/deliveries/summary/`, `/deliveries/{id}/ship/`, `/deliveries/{id}/complete/` |
| Avaliações (Filipe) | `/reviews/` (`?customer=`), `/reviews/{id}/moderate/` |
| Test drives (Rúben) | `/test-drives/` (`?search=`), `/test-drives/{id}/confirm/`, `/decline/`, `/cancel/` |

## Declaração de IA

Usámos IA generativa (Claude, da Anthropic) como ferramenta de apoio no M1 e no M2:

- **M1:** o Diogo usou o Claude para preparar o guia do grupo — a divisão das tarefas e o código das partes 1 a 6 e dos três recursos individuais (Delivery, Review e TestDrive). Cada membro aplicou, leu, testou e fez commit da sua parte e do seu recurso, com o seu nome (ver [`docs/m1.md`](docs/m1.md)). O Filipe usou-o também para rever os diffs das partes 2 e 5, e o Claude Code fez uma auditoria final em modo só de leitura.
- **M2:** o Diogo usou o Claude para preparar o guião do M2 — a escolha do branch, a divisão por commits e o código de cada passo: a adaptação do frontend da Ficha 04 ao DriveNow, os ecrãs dos três recursos, as correções ao M1, os contentores, o CI e os extras. Cada membro aplicou, leu, testou e fez commit dos seus passos, com o seu nome (ver [`docs/m2.md`](docs/m2.md)).
- **Como foi verificado:** em cada commit, `ruff`, `pytest` (159 testes, cobertura ≥ 95%), `spectacular --validate --fail-on-warn` sem diferenças no `schema.yaml`, `gen:api` sem diferenças no `schema.d.ts`, `type-check`, `oxlint` + `eslint`, `prettier --check`, Vitest (53 testes, com cobertura mínima e axe-core) e `vite build`; no fim, o arranque num clone limpo com `docker compose -f compose.prod.yaml up --build`, `migrate` e `seed`, o `check --deploy` com HTTPS ligado (0 avisos), o Trivy nas duas imagens (0 vulnerabilidades HIGH/CRITICAL com correção), os 3 testes e2e (Playwright) e o percurso pela SPA no browser (catálogo, login com `?next=`, F5, encomenda com erro por linha, pagamento, rota de gestor → `/forbidden`, moderação, entregas e test drives), sem nenhuma violação da CSP na consola.
- **Limites:** a IA não substituiu a revisão: os erros encontrados ao testar no browser (o horário ocupado vinha em inglês e sem campo, a mensagem de entrega duplicada em inglês) foram corrigidos com testes novos.
