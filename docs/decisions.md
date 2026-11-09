# Decisões · Decisions

PT: uma linha por decisão — o quê, porquê, alternativa rejeitada. Cresce ficha a ficha; o M1/M2/M3 avaliam este ficheiro.
EN: one line per decision — what, why, rejected alternative. Grows ficha by ficha; M1/M2/M3 grade this file.

## Esqueleto · Skeleton

- **`AUTH_USER_MODEL = "accounts.User"` desde o dia zero** — trocar depois da primeira migração obriga a reescrever o histórico; um `AbstractUser` vazio não custa nada. · Declared on day zero; swapping later means rewriting migration history; an empty `AbstractUser` is free.
- **Settings por ambiente (`base/dev/test/prod`) com `django-environ`** — o mesmo código em todos os ambientes, só as variáveis mudam (12-factor); segredos fora do git. · Same code everywhere, only env vars change; secrets stay out of git.
- **`/api/health/` devolve 503, não 500, com a base de dados em baixo** — é o código que um load balancer lê como "tira esta instância de rotação". · 503 is what a load balancer reads as "take this instance out of rotation".

## Ficha 02 — modelos · models

1. **on_delete:** Em `OrderItem.product` usei PROTECT. Se um produto já foi vendido, não pode ser apagado, senão as encomendas antigas ficavam com linhas sem produto. Para tirar um produto da loja usar `is_active=False`.

2. **Constraint:** Criámos `uq_orderitem_order_product` para não haver duas linhas com o mesmo produtto na mesma encomenda. Se o cliente quer mais unidades, aumenta-se a `quantity`. Assim o total e o stock não são contados duas vezes.

3. **JSONB:** Usei so num campo, `Payment.gateway_response`. Guarda a resposta do serviço de pagamento (MB WAY, cartão), que muda de formato conforme o serviço. So serve para consultar em caso de problema e nunca filtramos por ele. O resto dos dados ficou em colunas normais.

## Ficha 02 — API

<!-- --> Ao comentar a linha de prefetch_related, o valor retornado foram 82 queries
1. **Campo só de leitura** : unit_price é read-only porque o servidor copia o preço do produto no momento da compra; o cliente não pode escolher quanto paga.

2. **Paginação**: PageNumberPagination com 20 por página, porque as listas são pequenas e o frontend precisa do total para mostrar o número de páginas.

3. **Versionamento**: a versão vai no caminho (/api/v1/), para uma versão 2 poder conviver com a 1 sem partir clientes antigos.

**Lista de encomendas** (20 por página): 3 queries com prefetch_related; 82 queries sem prefetch_related

## Ficha 03 - Papéis e propriedade

## Parte 1 

1. Tempos de vida: access 30 min, refresh 1 dia, com rotação e blacklist — o access é curto
porque a expiração é a única revogação gratuita de um JWT; o refresh dura um dia para o
utilizador não ter de fazer login a cada meia hora; cada refresh devolve um novo e o antigo vai
para a blacklist, por isso um refresh já usado deixa de servir (repetido → 401).
Rejeitado: access de 1 dia — um token roubado valeria um dia inteiro.

2. Onde a SPA guarda os tokens: access em memória, refresh no localStorage — a SPA
(localhost:5173) e a API (localhost:8000) estão em origens diferentes e o token vai no
cabeçalho Authorization, por isso não há CSRF; o access em memória desaparece ao fechar o
separador; o risco de um XSS roubar o refresh é reduzido pelo tempo de vida curto, pela
rotação e pela CSP. Rejeitado: cookie HttpOnly — protege do XSS, mas traz de volta o CSRF e
obriga a configurar cookies entre origens.

## Parte 2

1. Papéis com Group, não com campos no User — o grupo gestores é criado pela migração "shop/0002_group_gestores", por isso existe em todos os ambientes; promover alguém a gestor
faz-se no admin, sem deploy. Rejeitado: is_staff, que é para o admin, não para o negócio.

2. Catálogo público — categorias e produtos leem-se sem login (AllowAny /
IsGestorOrReadOnly com leitura aberta), porque a loja tem de mostrar produtos a visitantes.

3. Encomenda alheia dá 404, não 403 — o get_queryset filtra por dono, por isso a encomenda
nem é encontrada; um 403 confirmaria que ela existe.

4. O dono vem do login — customer é só de leitura no OrderSerializer e é preenchido no
perform_create; nas linhas, validate_order recusa encomendas de outros clientes.

Lista de encomendas: 4 queries (eram 3 na Ficha 02) — a quarta é a verificação do grupo
em is_gestor(); não cresce com o número de encomendas.

**Matriz endpoint × papel**

Endpoint	                                  anónimo	cliente	                      gestor	              Mecanismo
GET /categories/	                            200	      200	                        200	                  AllowAny
GET /products/	                                200	      200	                        200	                  IsGestorOrReadOnly (leitura aberta)
POST /products/	                                401	      403	                        201	                  IsGestorOrReadOnly
PATCH/DELETE /products/{id}/	                401	      403	                        200/204	              IsGestorOrReadOnly
GET /orders/	                                401	      200, só as suas	            200, todas	          filtro no get_queryset
GET /orders/{id}/ (sua)	                        401	      200	                        200	                  filtro + IsOwnerOrGestor
GET /orders/{id}/ (de outro)	                401	      404	                        200	                  filtro → 404
POST /orders/	                                401	      201, dono = eu	            201, dono  = eu   	  perform_create + customer read-only
PATCH /orders/{id}/ {"status": ...} (sua)	    401	      200, status ignorado	        200, status ignorado  read_only_fields
POST /orders/{id}/pay/ (sua, pendente)	        401	      200	                        200	                  get_object + IsOwnerOrGestor
POST /orders/{id}/pay/ (de outro)	            401	      404	                        200	                  filtro → 404
GET /order-items/	                            401	      200, só das suas encomendas	200, todas	          filtro no get_queryset
POST /order-items/ (encomenda sua)	            401	      201	                        201                   validate_order
POST /order-items/ (encomenda de outro)	        401	      400	                        201	                  validate_order
GET /me/	                                    401	      200	                        200	                  IsAuthenticated


## Parte 3

1. CORS com lista explícita — só CORS_ALLOWED_ORIGINS (lida do .env; em dev
http://localhost:5173) pode ler respostas da API num browser, e só em /api/.... O
CorsMiddleware é o primeiro do MIDDLEWARE, porque o preflight OPTIONS não traz token.
O CORS protege utilizadores num browser, não a API: quem a protege é o JWT e as permissões.
Rejeitado: CORS_ALLOW_ALL_ORIGINS = True — qualquer site podia ler a API em nome do utilizador.

2. Throttling no login: 10 tentativas por minuto por IP (ThrottledTokenView, scope auth) —
a 11.ª recebe 429 antes de a password ser verificada, o que torna a força bruta impraticável.
Rejeitado: bloquear a conta ao fim de N tentativas — um atacante podia trancar qualquer
utilizador só por saber o nome dele.

3. Passwords: Argon2, mínimo 12 caracteres — Argon2 é o algoritmo recomendado (lento e
exigente em memória, de propósito); o PBKDF2 fica em segundo para os hashes antigos
continuarem a funcionar e serem convertidos no próximo login. Nos testes fica o MD5, só por
ser rápido. Rejeitado: tirar o PBKDF2 — as contas existentes deixavam de conseguir entrar.

4. check --deploy com 0 avisos (com config.settings.prod) — havia dois: W021
(resolvido com SECURE_HSTS_PRELOAD = True) e drf_spectacular.W002 (resolvido descrevendo
a resposta da MeView com @extend_schema).Em produção, SECRET_KEY e ALLOWED_HOSTS não têm valor por omissão: sem elas a app não arranca.

5. Campos do servidor só de leitura — customer, status, created_at (encomendas),
total e unit_price nunca vêm do cliente; um PATCH {"status": "paid"} é aceite mas
ignorado (testado em test_owner_cannot_change_status).

## Parte 4

1. A matriz é testada — shop/tests/test_auth.py tem um teste parametrizado por linha da
matriz (@pytest.mark.parametrize com anónimo, cliente e gestor): 22 casos. Os utilizadores
são autenticados com force_authenticate, para os testes de permissões não dependerem do
login JWT (que tem os seus próprios testes). Total do projeto: 37 testes (eram 10 na Ficha 02).

2. Tirando o filtro do get_queryset, falham os seguintes 3 testes: 

================================================================================================= 
short test summary info 
=================================================================================================
FAILED shop/tests/test_auth.py::test_list_orders_by_role[customer-200-1] - assert 2 == 1
FAILED shop/tests/test_auth.py::test_other_customers_order_is_404[get-] - assert 403 == 404
FAILED shop/tests/test_auth.py::test_other_customers_order_is_404[post-pay/] - assert 403 == 404

Conclusão: o IsOwnerOrGestor sozinho ainda impede ver o detalhe e pagar a encomenda de
outro, mas responde 403, o que confirma que ela existe, e deixa a lista aberta. São precisas
as duas camadas: o filtro (404 e lista fechada) e a permissão por objeto (defesa extra). O
filtro foi reposto.

## Ficha 04 — Frontend (SPA Vue)

### Parte 1

1. **`frontend/` no mesmo repositório da API** — SPA e API mudam juntas (um tipo do frontend
   acompanha o serializer no mesmo commit) e o M2 entrega SPA, CI e Docker num só repositório.
   Rejeitado: um repositório só para o frontend — duas tags e dois PRs para cada mudança de
   contrato.

2. **CORS em vez do proxy do Vite** — a SPA (`localhost:5173`) chama a API (`localhost:8000`)
   diretamente; a API responde `Access-Control-Allow-Origin` porque a origem está em
   `CORS_ALLOWED_ORIGINS` (Ficha 03). É o mesmo mecanismo que em produção, por isso um erro de
   configuração aparece já em desenvolvimento. Rejeitado: `server.proxy` no `vite.config.ts` —
   só existe no servidor de dev e esconderia um CORS mal configurado até ao M2.

3. **O URL é o estado da lista** — pesquisa e página vivem em `?search=` e `?page=`
   (`computed` com `get`/`set` sobre `route.query`): recarregar mantém-nas, o link partilha-se e o
   Retroceder funciona. `router.replace` para a pesquisa, `router.push` para mudar de página.
   Rejeitado: `ref`s locais — perdiam-se no F5.

4. **Rotas *lazy*** — o detalhe, o login e as encomendas são `() => import(...)`: cada uma é um
   chunk à parte, descarregado só quando se abre; a lista, que é o primeiro ecrã, vai no bundle
   principal.

5. **Detalhe sem `attributes`** — o `Product` não tem JSONB, por isso o `<dl>` do detalhe mostra
   os campos do produto com o mesmo `v-for` sobre um objeto.

### Parte 2

6. **Onde vivem os tokens** — o access (30 min) só em memória, num `ref` da store; o refresh
   (1 dia, rodado a cada uso e posto na blacklist) no `localStorage`, para o F5 não obrigar a novo
   login. Um XSS que leia o storage só encontra o refresh, de vida curta e de uso único.
   Rejeitados: cookie `HttpOnly` — a API passaria a emitir cookies e a precisar de CSRF outra vez
   (e de CORS com credenciais); `sessionStorage` — um login por separador; refresh só em memória —
   login a cada F5.

7. **Como se renova** — um middleware do `openapi-fetch` põe `Authorization: Bearer` em todos os
   pedidos; num 401 chama `refreshAccess()` **uma vez** e repete o pedido com um `fetch` simples
   (um segundo 401 é a sério). Se a renovação falhar: `logout()` e o `App.vue` manda para
   `/login?next=`. Duas renovações em paralelo partilham a mesma promise (senão a segunda gastava um
   refresh já na blacklist), e o refresh é lido do `localStorage` (outro separador pode já o ter
   rodado). No arranque, `bootstrap()` renova e carrega `/me/` antes de montar a app.

8. **Tipos gerados do OpenAPI** — `openapi-typescript` gera `src/api/schema.d.ts` do `schema.yaml`
   e o `openapi-fetch` verifica URLs, parâmetros e corpos na compilação (`query: { foo: 1 }` não
   compila); `src/types.ts` ficou só com aliases. `COMPONENT_SPLIT_REQUEST: True` na API separa o
   pedido da resposta. O esquema foi corrigido onde mentia: `total` com `allow_null=True` (uma
   encomenda sem linhas). O `stock?` de `Product` (default no modelo) não foi estreitado — exigiria
   um `as` em cada vista; quem o usa faz `stock ?? 0`. O `openapi-typescript` 7 pede TypeScript 5:
   um `overrides` no `package.json` fá-lo usar o TypeScript 6 do projeto. Rejeitado: manter os tipos
   à mão — divergem do serializer sem ninguém dar por isso.

9. **O guard protege o ecrã, não os dados** — `meta.requiresAuth` + `beforeEach` (≈
   `@login_required` com `?next=`); a autorização continua na API (401/403/404 da Ficha 03). O
   `?next=` só aceita caminhos internos (começa por `/` e não por `//`), para não haver *open
   redirect*.

10. **Erros onde o utilizador está a olhar** — `ApiError.field()` lê os erros por campo no formato
    do DRF (`{"quantity": [...]}`, o desta API) e no de Problem Details (`errors.quantity`). 400 →
    debaixo da linha do formulário; 401/429 no login → frases próprias; 409 ao pagar → mensagem por
    cima da lista, que recarrega; rede/5xx → estado de erro com "Tentar outra vez".

11. **Nova encomenda sem escrita aninhada** — `POST /orders/` (sem corpo: o servidor decide
    `customer` e `status`) e um `POST /order-items/` por linha. Se uma linha falhar, a encomenda e
    as linhas já gravadas ficam; ao reenviar reutiliza-se a mesma encomenda e só se enviam as
    linhas em falta. O total no formulário é uma estimativa (em cêntimos inteiros); o que conta é o
    `total` da API, somado em `Decimal`.

12. **Testes sem rede** — 13 testes Vitest com `fetch` substituído (`vi.stubGlobal`): store
    (o refresh vai para o `localStorage`, o access não), middleware (401 → refresh → repetição com
    o Bearer novo; refresh falhado → logout sem loop), `LoginView` (401 → mensagem, sem navegar),
    `OrderStatusBadge` (`it.each` pelos quatro estados) e `ProductCard`.

13. **O token lido fora da reatividade** — o middleware lê o access com `auth.accessToken()` (uma
    cópia simples, atualizada por um `watch` com `flush: 'sync'`) e não com `auth.access`. Lido
    como `ref` dentro do pedido, o `watchEffect` do `useFetch` passava a depender do token, e
    cada renovação ou logout repetia os pedidos de todas as listas no ecrã. Um teste do
    middleware prova que mudar o token não volta a chamar a API.
