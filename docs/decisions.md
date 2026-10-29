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

