# frontend — SPA da Loja DWFA

SPA em **Vue 3 + TypeScript + Vite + Vue Router + Pinia** que consome a API Django deste
repositório (Fichas 02 e 03). Ficha 04:

- **Parte 1 (Aula 05):** catálogo público — lista com pesquisa e paginação no URL, e detalhe.
- **Parte 2 (Aula 06):** login com JWT, sessão numa store Pinia (access em memória, refresh no
  `localStorage`, renovado uma vez num 401), guard nas rotas privadas, "as minhas encomendas"
  com Pagar, e um formulário de nova encomenda com os erros do serializer por linha.

## Requisitos

- Node.js 22 ou mais recente (`node -v`)
- A API a correr em `http://localhost:8000`, com `http://localhost:5173` em
  `CORS_ALLOWED_ORIGINS` (ver `../.env`)

## Como correr

```bash
# na raiz do repositório: a API
docker compose up -d db
uv run manage.py migrate
uv run manage.py seed            # utilizadores user0000… com a password pass1234
uv run manage.py runserver

# noutro terminal: o frontend
cd frontend
cp .env.example .env             # VITE_API_URL=http://localhost:8000
npm install
npm run dev                      # → http://localhost:5173
```

Para ver a renovação do token a acontecer: `JWT_ACCESS_MINUTES=1` no `../.env` da API (o access
passa a durar 1 minuto; por omissão são 30).

## Comandos

| Comando | O que faz |
| --- | --- |
| `npm run dev` | Servidor de desenvolvimento com HMR em `http://localhost:5173` |
| `npm run type-check` | Verificação de tipos com `vue-tsc` (zero erros) |
| `npm run lint` | oxlint + ESLint |
| `npm run test:unit` | Testes Vitest (`npx vitest run` para correr uma vez e sair) |
| `npm run build` | `type-check` + build de produção para `dist/` |
| `npm run gen:api` | Regenera `src/api/schema.d.ts` a partir do `../schema.yaml` |

Depois de mudar um serializer na API: `uv run manage.py spectacular --file schema.yaml` (na
raiz) e `npm run gen:api` (aqui). Um campo renomeado aparece como erro no `type-check`.

## O que está cá

| Caminho | Para quê |
| --- | --- |
| `src/api/schema.d.ts` | Tipos **gerados** do `schema.yaml` (openapi-typescript). Nunca editar |
| `src/api/client.ts` | O cliente `api` (openapi-fetch), `unwrap()` e `ApiError` (`.detail`, `.field()`) |
| `src/api/auth.ts` | Middleware: `Authorization: Bearer` em todos os pedidos; 401 → renovar uma vez → repetir |
| `src/stores/auth.ts` | Store Pinia da sessão: `login`, `logout`, `refreshAccess`, `bootstrap` |
| `src/types.ts` | Nomes curtos para os tipos gerados (`Product`, `Order`, `OrderStatus`, `Me`…) |
| `src/composables/useFetch.ts` | Os três estados (a carregar · erro · dados) + `reload` |
| `src/router/index.ts` | Rotas, `meta.requiresAuth` e o guard `beforeEach` (→ `/login?next=`) |
| `src/views/ProductsView.vue` | Lista; pesquisa e página no URL (`?search=`, `?page=`) |
| `src/views/ProductView.vue` | Detalhe de um produto (rota lazy) |
| `src/views/LoginView.vue` | Login; 401 e 429 com mensagens próprias |
| `src/views/OrdersView.vue` | As minhas encomendas (a API filtra); Pagar; o 409 como mensagem |
| `src/views/NewOrderView.vue` | Nova encomenda: linhas, total estimado, erros 400 por linha |
| `src/views/NotFoundView.vue` | Página para URLs desconhecidos |
| `src/components/ProductCard.vue` | Cartão de produto com props e emits tipados |
| `src/components/OrderStatusBadge.vue` | Estado da encomenda com `switch` exaustivo (`satisfies never`) |
| `src/**/__tests__/` | 12 testes Vitest, sem rede (`fetch` substituído) |

## Ambiente

`VITE_API_URL` (em `.env`, ignorado pelo git) é o URL base da API. Só as variáveis `VITE_*`
chegam ao browser e ficam no bundle: nunca lá pôr segredos.
