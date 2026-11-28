# Ficha 06 — Performance e observabilidade no DriveNow

Grupo: Diogo Pereira (entregas), Filipe Cardoso (avaliações), Rúben Afonso (test drives).
Ramo `ficha-06`, tag `ficha-06`. Referência: `aula-09/` em `dwfa-2627-solucoes`.

## Como se mediu

- **Volume:** `uv run python manage.py seed` e depois `uv run python manage.py seed_big`
  (`shop/management/commands/seed_big.py`): 50 030 encomendas, cerca de 30 000 entregas,
  20 000 avaliações, 20 000 test drives e 2 010 clientes. Estados desiguais de propósito
  (1 em cada 10 encomendas pendente, 4 em cada 10 entregues) e datas espalhadas por dois anos.
- **Medição:** `uv run python scripts/measure.py <url> --token <access do gestor> --row gestor`:
  três pedidos de aquecimento e depois 30, um de cada vez. Mediana e p95 do lado do cliente;
  queries e ms na BD vêm do cabeçalho `Server-Timing` do `core/middleware.py`.
- **Onde:** `runserver` em desenvolvimento, PostgreSQL 16 no Docker, no portátil do Diogo.
  As saídas completas estão em `docs/ficha-06/`.

## Medição de base (antes de qualquer correção)

Papel: gestor (é quem vê mais dados). Tempos em ms.

| Endpoint | Papel | Queries | ms na BD | Mediana | p95 |
|---|---|---|---|---|---|
| `GET /api/v1/orders/` | gestor | 5 | 216.1 | 234.4 | 298.3 |
| `GET /api/v1/deliveries/` | gestor | 4 | 35.5 | 51.8 | 63.6 |
| `GET /api/v1/reviews/` | gestor | 4 | 30.9 | 48.1 | 51.0 |
| `GET /api/v1/test-drives/` | gestor | 4 | 30.6 | 49.7 | 59.6 |
| `GET /api/v1/payments/` | gestor | 4 | 37.0 | 54.3 | 68.4 |
| `GET /api/v1/customers/` | gestor | 4 | 4.2 | 17.9 | 22.4 |
| `GET /api/v1/cars/` | gestor | 3 | 3.0 | 19.3 | 30.4 |
| `GET /api/v1/order-items/` | gestor | 4 | 8.9 | 25.0 | 30.4 |
| `GET /api/v1/deliveries/?overdue=true` | gestor | 4 | 17.1 | 35.0 | 47.2 |
| `GET /api/v1/deliveries/summary/` | gestor | 3 | 7.4 | 19.4 | 26.4 |

O mais lento é `GET /api/v1/orders/`: poucas queries, mas quase todo o tempo é passado na base
de dados. O total de cada encomenda vem de um `annotate(Sum(...))`, que faz um `GROUP BY`
sobre as 50 000 encomendas e as linhas delas em cada página, antes do `LIMIT 20` (o problema
da aula). Nenhuma lista tem N+1: as queries não passam de 5 em nenhum endpoint.

## Uma correção por elemento

| Elemento | Endpoint | Antes | Depois | O que mudou |
|---|---|---|---|---|
| Diogo Pereira | `GET /api/v1/deliveries/` (gestor) | 4 queries · 40.6 ms na BD · mediana 59.6 ms · p95 84.4 ms | 4 queries · 5.6 ms na BD · mediana 20.8 ms · p95 23.6 ms | Índice em `scheduled_for`, a ordenação da lista: o plano passou de juntar todas as entregas à encomenda e ao cliente e só depois ordenar (`Hash Join` + `Sort`) para ler as 20 primeiras pelo índice (`Index Scan using ix_delivery_scheduled_for`). [commit](https://github.com/diogofcpereira/isla-dwfa-ecommerce/commit/510daa40cbaf152d37c33e5e06249bac7519c53e) |
| Filipe Cardoso | `GET /api/v1/reviews/` | (a preencher pelo Filipe) | | |
| Rúben Afonso | `GET /api/v1/test-drives/` | (a preencher pelo Rúben) | | |

Cada correção tem um teste que conta queries (com 5 linhas e com 20, o mesmo número). O do
Diogo é `deliveries/tests/test_ficha06_performance.py`.

### Diogo: as entregas

- **O que o middleware dizia:** poucas queries (4) e muito tempo na base de dados. Pela
  tabela do Passo 4 da ficha, isto pede um `explain(analyze=True)`.
- **O que o plano mostrou** (`docs/ficha-06/explain-deliveries-antes.txt`): a página faz
  `Hash Join` das entregas com as encomendas e os clientes e um `Sort` por `scheduled_for`,
  sobre as 30 000 entregas, para ficar com 20. O índice que já existia, `(status,
  scheduled_for)`, começa pelo estado e só serve a lista filtrada por estado.
- **A alteração** (`deliveries/migrations/0002_delivery_scheduled_for_index.py`): um índice
  em `scheduled_for`. O plano passou a `Index Scan using ix_delivery_scheduled_for` com
  `Nested Loop`: lê as 20 primeiras pela ordem certa e só junta essas
  (`docs/ficha-06/explain-deliveries-depois.txt`).
- **As medições:** `docs/ficha-06/deliveries-antes.txt` e `docs/ficha-06/deliveries-depois.txt`,
  com o mesmo comando e os mesmos dados. O tempo que fica na base de dados é sobretudo o
  `COUNT(*)` da paginação.
