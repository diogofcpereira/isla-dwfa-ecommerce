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

<!-- -->
