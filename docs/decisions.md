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

Endpoint                                      Anónimo   Cliente                         Gestor                    Mecanismo
--------------------------------------------  --------  -----------------------------  ------------------------  ----------------------------------------
GET /brands/                                  200       200                            200                       IsGestorOrReadOnly (leitura aberta)
POST/PATCH/DELETE /brands/                    401       403                            201/200/204               IsGestorOrReadOnly
GET /cars/                                    200       200                            200                       IsGestorOrReadOnly (leitura aberta)
POST /cars/                                   401       403                            201                       IsGestorOrReadOnly
PATCH/DELETE /cars/{id}/                     401       403                            200/204                   IsGestorOrReadOnly
GET /orders/                                  401       200, só as suas               200, todas               filtro no get_queryset
GET /orders/{id}/ (sua)                      401       200                            200                       filtro + IsOwnerOrGestor
GET /orders/{id}/ (de outro)                 401       404                            200                       filtro → 404
POST /orders/                                 401       201, dono = eu                 201, dono = eu            perform_create + customer read-only
PATCH /orders/{id}/ {"status": ...} (sua)    401       200, status ignorado           200, status ignorado      read_only_fields
POST /orders/{id}/pay/ (sua, pendente)       401       200                            200                       get_object + IsOwnerOrGestor
POST /orders/{id}/pay/ (de outro)            401       404                            200                       filtro → 404
GET /order-items/                             401       200, só das suas encomendas   200, todas               filtro no get_queryset
POST /order-items/ (encomenda sua)           401       201                            201                       validate_order
POST /order-items/ (encomenda de outro)      401       400                            201                       validate_order
GET /me/                                      401       200                            200                       IsAuthenticated


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

## Fichas 02–03 — Filipe

Decisões do fork individual que diferem das do Diogo:

- **JSONB em `Product.attributes`:** guardei os atributos que variam por categoria (cor, tamanho, voltagem) num JSONB, porque não têm um esquema fixo e não eram filtrados; rejeitei uma tabela EAV ou colunas por categoria, mais caras para nenhum ganho, e adiei um `GinIndex` até haver uma query que o justifique.
- **Índice composto `(customer, created_at)` em `Order`:** indexei a query mais frequente da loja, "as minhas encomendas, mais recentes primeiro"; rejeitei um índice só em `customer`, que obrigava a ordenar as encomendas à parte.
- **Erros no formato RFC 9457 desde a Ficha 02:** um `EXCEPTION_HANDLER` dá a todos os erros DRF o mesmo envelope (`type`, `title`, `status`, `errors`), para o cliente tratar 400, 404, 409 e 429 da mesma forma; rejeitei o formato por omissão do DRF, que muda de forma conforme o erro (no M1, a parte 5 adotou este formato para o grupo).
- **`cancel` além do `pay`, ambos em `services.py` com `select_for_update`:** as duas transições de estado bloqueiam a linha numa transação, para que dois pedidos concorrentes não mudem a mesma encomenda duas vezes; rejeitei mudar o estado na vista ou por `PATCH {"status": ...}`, sem bloqueio.
- **Tokens da SPA só em memória, incluindo o refresh:** o `localStorage` é legível por qualquer script da página e fica exposto a XSS, por isso aceitei o custo de um novo login ao recarregar; rejeitei o refresh no `localStorage` e deixei como evolução um cookie HttpOnly, Secure e SameSite, com proteção CSRF.
- **Filtro por dono também em `Customer`, `OrderItem` e `Payment`:** apliquei o padrão das encomendas (gestor vê tudo, cliente só os seus, 404 nos alheios), porque estes endpoints expunham dados de outros clientes; rejeitei protegê-los só com a permissão por objeto, que deixa a lista aberta e responde 403.
- **Linha numa encomenda alheia → 404:** um cliente que tenta acrescentar uma linha à encomenda de outro recebe 404, como em qualquer objeto alheio, para não confirmar que a encomenda existe; rejeitei um erro de validação 400.
- **`POST /orders/` de um gestor sem perfil de cliente → 400:** uma encomenda pertence sempre a um cliente, e um gestor não é cliente; rejeitei criar automaticamente um perfil de cliente para o gestor.
- **`MeSerializer` para documentar `/me/`:** a resposta passa a ter um esquema no Swagger, o que elimina o aviso `drf_spectacular.W002` do `check --deploy`; rejeitei deixar a resposta sem esquema e silenciar o aviso.

## Fichas 02–03 — Rúben

Decisões do meu fork individual (escritas na altura com os nomes da loja: `Product`, `Category`).

### Ficha 02 — Modelos e API

- **`Product.category` com `PROTECT`:** impede apagar uma categoria que ainda tem produtos, para não perder o catálogo por engano. Rejeitei `CASCADE` porque apagava os produtos todos de uma vez.
- **`UniqueConstraint` no `sku` e `CheckConstraint` no `price`:** a base de dados garante SKUs únicos e preços não negativos, mesmo quando a escrita não passa por um formulário ou por um serializer.
- **Sem JSONB:** os dados da loja (produtos, categorias, encomendas, pagamentos) têm estrutura fixa e relações claras, por isso usei colunas tipadas e chaves estrangeiras. Rejeitei JSONB porque perdia as constraints e a validação da base de dados.
- **Campos só de leitura:** IDs, datas, estado da encomenda, total e preço unitário são definidos pelo servidor, para o cliente não poder alterar dados derivados.
- **Paginação com `PageNumberPagination` (20 por página):** evita devolver todos os registos numa só resposta. Para listas muito grandes eu escolheria `CursorPagination`, que não conta todos os registos mas precisa de uma ordenação estável (por exemplo `created_at` e `id`).
- **Versionamento com o prefixo `/api/v1/`:** fica claro nos URLs e permite lançar uma `v2` com alterações incompatíveis sem partir quem usa a `v1`.
- **N+1 na listagem de encomendas:** uso `select_related`, `prefetch_related` e `annotate`, e o teste limita a listagem a 3 queries.
- **Validação em duas camadas:** o serializer dá erros claros antes de escrever, e as constraints da base de dados mantêm a integridade por qualquer caminho (ORM, scripts, admin).
- **Stock concorrente:** uma `CheckConstraint` não compara o stock de outra tabela, por isso o produto deve ser bloqueado com `select_for_update()` numa transação e o stock revalidado antes de o atualizar.

### Ficha 03 — Autenticação e autorização

- **JWT com access de 30 minutos e refresh de 1 dia, rotativo, com o token antigo na blacklist:** um token roubado dura pouco, e um refresh já usado deixa de servir.
- **Tokens na SPA:** o access fica em memória e o refresh no `localStorage`. Evito guardar o access em armazenamento persistente, mas a proteção contra XSS continua a ser necessária.
- **Papéis pelo grupo `gestores`, criado por migração de dados:** o grupo existe em qualquer base de dados nova, sem passos manuais. Rejeitei um campo `is_manager` no utilizador para não duplicar o que os grupos do Django já fazem.
- **Catálogo público para leitura:** só a escrita é reservada aos gestores.
- **Cliente da encomenda definido pelo servidor:** o cliente não escolhe a quem pertence a encomenda, e só vê e paga as suas.
- **`404` para uma encomenda alheia:** o `get_queryset` filtra por utilizador. Com `403` a resposta confirmaria que a encomenda existe, e assim evita-se a enumeração de IDs.
- **`401` vs `403`:** `401` quando não há autenticação válida, `403` quando há autenticação mas falta autorização.
- **CORS não é segurança:** é aplicado pelo browser e não bloqueia `curl` nem scripts. A proteção real vem da autenticação, das permissões por papel e por objeto, do queryset filtrado e da validação dos dados.

## M1 — Domínio DriveNow (stand de carros)

1. **Domínio:** O projeto representa o DriveNow, um stand de automóveis onde os clientes podem encomendar e pagar viaturas, enquanto os gestores ficam responsáveis pela gestão de marcas, viaturas e encomendas. Foi rejeitada a manutenção da loja genérica das fichas, optando-se por um domínio próprio com as mesmas seis entidades.

2. **Entidades:** `Category` foi substituída por `Brand` e `Product` por `Car`, que inclui marca, código, modelo, versão, ano, combustível, preço e stock. As restantes entidades (`Customer`, `Order`, `OrderItem` e `Payment`) mantiveram-se. Os nomes continuam em inglês e a aplicação mantém-se como `shop`, conforme permitido pelo enunciado.

3. **Migrações:** Foi eliminada a migração `0001_initial_domain` e criada uma nova `0001_initial`, uma vez que não existiam dados a preservar (FAQ do M1). A `0002_group_gestores` foi atualizada para depender da nova migração. Quem tiver uma base de dados antiga deverá recriá-la com `docker compose down -v`.

4. **Stock das viaturas:** `Car.stock` representa as unidades disponíveis de uma versão, e não viaturas individuais identificadas por VIN. Assim, são possíveis encomendas de várias unidades, como frotas empresariais, aproveitando o mecanismo `add_item` com `select_for_update`. Foi rejeitada a abordagem de uma linha por viatura física, que obrigaria a quantidades iguais a 1.

5. **Regras na base de dados:** Foram criadas as restrições `ck_car_price_gte_0`, `ck_car_year_gte_1990`, `uq_orderitem_order_car` e `ck_orderitem_quantity_gte_1`, para garantir a validade dos preços, anos, quantidades e evitar viaturas repetidas na mesma encomenda. Foram também adicionados os índices `ix_car_brand_active` e `ix_car_fuel_price`, para otimizar pesquisas por marca, combustível e preço.

6. **Estados e pagamentos:** As encomendas seguem o fluxo pendente → paga → entregue, podendo também ser canceladas. Os métodos de pagamento disponíveis são transferência bancária, financiamento, cartão e MB WAY.

7. **Gestão de marcas:** O endpoint `/brands/` passou a utilizar `IsGestorOrReadOnly`, permitindo aos gestores adicionar marcas, enquanto a consulta continua pública.

8. **Viaturas retiradas:** Uma viatura com `is_active=False` deixa de poder ser encomendada. Esta validação é feita em `OrderItemSerializer.validate_car`, devolvendo erro 400. A viatura mantém-se nas encomendas antigas graças ao `PROTECT`, preservando o histórico.

## M1 — Núcleo (fluxo, API completa, erros, auth e dados)

9. **Encomenda criada com as linhas no mesmo pedido:** `POST /orders/` recebe `items` e o `services.create_order` cria tudo numa transação; se uma linha falha (viatura retirada, sem stock), nada fica gravado e o stock volta ao que era (`test_create_order_rolls_back_when_stock_runs_out`). Uma encomenda sem linhas ou com a mesma viatura em duas linhas é recusada com 400. Rejeitado: criar a encomenda vazia e acrescentar linhas depois — deixava encomendas a meio se a segunda chamada falhasse.
10. **Pagar cria o `Payment`:** `POST /orders/{id}/pay/ {"method": ...}` bloqueia a encomenda (`select_for_update`), confirma que está pendente e tem linhas, grava o pagamento com o total e passa a encomenda a paga; pagar de novo dá 409. Rejeitado: só mudar o estado — o pagamento ficava sem registo e o `/payments/` vazio.
11. **Falta de stock é 409, não 500:** `OutOfStock` passou a ser um `Conflict`; o serializer dá 400 no caso normal e o serviço, com a viatura bloqueada, dá 409 no caso concorrente (dois clientes a comprar a última unidade).
12. **O stock acompanha as encomendas:** mudar a quantidade de uma linha acerta o stock pela diferença, apagar uma linha ou uma encomenda pendente devolve as unidades. Numa linha que já existe só a quantidade muda (trocar de viatura = apagar e criar).
13. **Encomenda paga não muda:** apagar, acrescentar ou alterar linhas de uma encomenda que já não está pendente dá 409. Sem isto, apagar uma encomenda paga rebentava com um 500 (o `Payment` protege-a com `PROTECT`).
14. **Um viewset por entidade:** `/customers/` (listar, ver e editar o próprio perfil; sem POST nem DELETE, porque o perfil nasce com a primeira encomenda) e `/payments/` (só leitura; um pagamento só nasce no `pay`). O `gateway_response` não sai na API: é diagnóstico interno.
15. **Erros com a forma da RFC 9457:** `core.exceptions.problem_details_handler` responde `application/problem+json` com `type`, `title`, `status`, `detail` e `instance`; os erros de validação vão em `errors`, campo a campo, e o `code` do simplejwt mantém-se. Rejeitado: o formato por omissão do DRF, que muda de forma conforme o erro.
16. **Logout:** `POST /auth/logout/ {"refresh": ...}` põe o refresh na blacklist (`TokenBlacklistView`); o access ainda vale até expirar, por isso tem só 30 minutos. Não exige o access token: quem tem o refresh pode sempre desistir dele.
17. **Dados de demonstração:** `manage.py seed` cria o catálogo de 20 viaturas (uma retirada de venda), o gestor `gestor`, os clientes `ana`, `bruno` e `carla` com uma encomenda em cada estado, e mais clientes e encomendas ao acaso. Usa os mesmos serviços da API, por isso o stock e os pagamentos ficam coerentes; pode correr várias vezes sem duplicar. A password de demonstração (`drivenow-demo-2026`) só existe em dev.
18. **Sem N+1:** cada lista tem um teste em `shop/tests/test_queries.py` com 25 objetos: catálogo em ≤ 3 queries (count + lista), listas autenticadas em ≤ 3 ou 4 (mais a query do `is_gestor()` e, nas encomendas, a das linhas).

## M1 — Matriz endpoint × papel

Cada linha está testada em `shop/tests/test_auth.py` (por papel) ou nos testes indicados. 401 = quem és? · 403 = podes? · 404 = existe para ti? · 409 = o estado não deixa.

| Endpoint | anónimo | cliente | gestor | Mecanismo |
|---|---|---|---|---|
| `GET /brands/`, `GET /cars/` | 200 | 200 | 200 | `IsGestorOrReadOnly` (leitura aberta) |
| `POST/PATCH/DELETE /brands/` | 401 | 403 | 201/200/204 | `IsGestorOrReadOnly` |
| `POST/PATCH/DELETE /cars/` | 401 | 403 | 201/200/204 | `IsGestorOrReadOnly` |
| `GET /customers/` | 401 | 200, só o seu | 200, todos | filtro no `get_queryset` |
| `GET/PATCH /customers/{id}/` (seu) | 401 | 200 (`user` ignorado) | 200 | filtro + `IsProfileOwnerOrGestor` |
| `GET /customers/{id}/` (de outro) | 401 | 404 | 200 | filtro → 404 |
| `POST/DELETE /customers/` | 401 | 405 | 405 | sem create/destroy no viewset |
| `GET /orders/` | 401 | 200, só as suas | 200, todas | filtro no `get_queryset` |
| `GET /orders/{id}/` (de outro) | 401 | 404 | 200 | filtro → 404 |
| `POST /orders/` com `items` | 401 | 201, dono = eu | 201, dono = eu | `perform_create` + `create_order` |
| `POST /orders/` com uma linha inválida | 401 | 400, nada criado | 400, nada criado | transação (`test_flow.py`) |
| `PATCH /orders/{id}/ {"status": ...}` (sua) | 401 | 200, status ignorado | 200, status ignorado | `read_only_fields` |
| `DELETE /orders/{id}/` (pendente) | 401 | 204 (sua) / 404 (de outro) | 204 | filtro + `delete_order` |
| `DELETE /orders/{id}/` (paga) | 401 | 409 | 409 | `ensure_pending` (`test_stock.py`) |
| `POST /orders/{id}/pay/` (sua, pendente) | 401 | 200, cria o Payment | 200 | `pay_order` |
| `POST /orders/{id}/pay/` (já paga) | 401 | 409 | 409 | `pay_order` |
| `POST /orders/{id}/pay/` (de outro) | 401 | 404 | 200 | filtro → 404 |
| `GET /order-items/` | 401 | 200, só das suas encomendas | 200, todas | filtro no `get_queryset` |
| `POST /order-items/` (encomenda de outro) | 401 | 400 | 201 | `validate_order` |
| `PATCH/DELETE /order-items/{id}/` (pendente) | 401 | 200/204, stock acertado | 200/204 | `change_quantity` / `remove_item` |
| `POST/PATCH/DELETE /order-items/` (encomenda paga) | 401 | 409 | 409 | `ensure_pending` |
| `GET /payments/` | 401 | 200, só os seus | 200, todos | filtro no `get_queryset` |
| `GET /payments/{id}/` (de outro) | 401 | 404 | 200 | filtro → 404 |
| `POST /payments/` | 401 | 405 | 405 | `ReadOnlyModelViewSet` |
| `GET /me/` | 401 | 200 | 200 | `IsAuthenticated` |
| `POST /auth/logout/` | 200 com um refresh válido | 200 | 200 | `TokenBlacklistView` |

## M1 — Recursos individuais

Um recurso por membro, cada um na sua app Django (`deliveries`, `reviews`, `testdrives`), para cada app ter as suas migrações e não haver conflitos no `shop`. Cada subsecção tem as decisões do recurso e as suas linhas da matriz endpoint × papel, testadas em `<app>/tests/`.

### Delivery — entrega da viatura (Diogo)

19. **Só encomendas pagas, uma entrega por encomenda:** `Delivery.order` é um `OneToOneField` com `PROTECT`, e o `validate_order` recusa encomendas que não estejam pagas (400). Rejeitado: uma FK com várias entregas por encomenda, que complicava saber quando a encomenda fica entregue.
20. **O estado só muda por ações:** `POST /deliveries/{id}/ship/` (agendada → em trânsito) e `/complete/` (→ entregue) são serviços com `select_for_update`, e repetir dá 409. O `complete` passa a encomenda a `delivered` na mesma transação. Rejeitado: `PATCH {"status": ...}`, que deixava saltar estados e esquecer a encomenda.
21. **`ck_delivery_delivered_at_matches_status`:** a base de dados garante que só uma entrega concluída tem `delivered_at`, e que todas as concluídas o têm.
22. **Leitura para o cliente, escrita para o gestor:** `IsAuthenticated` + `IsGestorOrReadOnly` + `IsDeliveryOwnerOrGestor`, com o filtro no `get_queryset` (404 nas entregas de outros). Não há DELETE: a entrega fica no histórico da encomenda.

| Endpoint | anónimo | cliente | gestor | Mecanismo |
|---|---|---|---|---|
| `GET /deliveries/` | 401 | 200, só as das suas encomendas | 200, todas | filtro no `get_queryset` |
| `GET /deliveries/{id}/` (de outro) | 401 | 404 | 200 | filtro → 404 |
| `POST/PATCH /deliveries/` | 401 | 403 | 201/200; 400 se a encomenda não estiver paga ou já tiver entrega | `IsGestorOrReadOnly` + `validate_order` |
| `POST /deliveries/{id}/ship/`, `/complete/` | 401 | 403 | 200; 409 se repetido | `IsGestorOrReadOnly` + serviços |

### Review — avaliação da viatura (Filipe)

23. **Só avalia quem comprou:** o `ReviewSerializer.validate` procura uma linha dessa viatura numa encomenda paga ou entregue do cliente; sem compra, 400. Rejeitado: deixar qualquer cliente avaliar, que abria a porta a avaliações falsas.
24. **Uma avaliação por cliente e viatura:** `uq_review_car_customer` na base de dados e a mesma verificação no serializer, para responder 400 em vez de rebentar com um `IntegrityError`. A nota vai de 1 a 5 (`ck_review_rating_1_5`).
25. **Moderação:** as avaliações nascem pendentes e só o gestor as aprova ou oculta (`POST /reviews/{id}/moderate/`, `IsGestor`); uma avaliação editada volta a pendente. O público vê só as aprovadas; o cliente vê também as suas.
26. **Leitura pública, escrita do autor:** `IsAuthenticatedOrReadOnly` + `IsReviewAuthorOrGestor`. Numa avaliação aprovada de outro, o cliente leva 403 (ela é pública); numa pendente de outro, 404 (nem a vê).

| Endpoint | anónimo | cliente | gestor | Mecanismo |
|---|---|---|---|---|
| `GET /reviews/` | 200, só as aprovadas | 200, as aprovadas e as suas | 200, todas | filtro no `get_queryset` |
| `POST /reviews/` | 401 | 201 se comprou; 400 se não comprou ou se repetir | 201 se comprou | `validate` |
| `PATCH/DELETE /reviews/{id}/` (sua) | 401 | 200 (volta a pendente) / 204 | 200/204 | `IsReviewAuthorOrGestor` |
| `PATCH/DELETE /reviews/{id}/` (aprovada, de outro) | 401 | 403 | 200/204 | `IsReviewAuthorOrGestor` |
| `POST /reviews/{id}/moderate/` | 401 | 403 | 200 | `IsGestor` |

### TestDrive — marcação de test drive (Rúben)

27. **Horários de hora a hora, um por viatura:** o `validate_scheduled_for` exige uma data no futuro e à hora certa (hh:00), e a `uq_testdrive_car_slot_active` é uma `UniqueConstraint` condicional, só para pedidos e confirmados: cancelar ou recusar liberta o horário. Rejeitado: uma `UniqueConstraint` simples, que deixava o horário ocupado para sempre.
28. **Dois clientes ao mesmo tempo:** o serializer dá 400 no caso normal; se dois pedidos passarem juntos, a constraint apanha o segundo e o `book_test_drive` responde 409 em vez de 500.
29. **O estado só muda por ações:** confirmar e recusar (só o gestor, `IsGestor`) a partir de um pedido; cancelar (o dono ou o gestor) a partir de um pedido ou de um confirmado; o resto dá 409. Não há PUT/PATCH nem DELETE: muda-se de horário cancelando e marcando de novo.
30. **Cada um vê os seus:** filtro no `get_queryset` + `IsTestDriveOwnerOrGestor`, por isso as marcações de outros dão 404.

| Endpoint | anónimo | cliente | gestor | Mecanismo |
|---|---|---|---|---|
| `GET /test-drives/` | 401 | 200, só os seus | 200, todos | filtro no `get_queryset` |
| `POST /test-drives/` | 401 | 201; 400 no passado, fora da hora certa, viatura retirada ou horário ocupado | 201 | `validate` + `uq_testdrive_car_slot_active` |
| `POST /test-drives/{id}/confirm/`, `/decline/` | 401 | 403 | 200; 409 se já não estiver pedido | `IsGestor` + serviços |
| `POST /test-drives/{id}/cancel/` | 401 | 200 (seu) / 404 (de outro); 409 se já não estiver ativo | 200 | filtro + `IsTestDriveOwnerOrGestor` |

