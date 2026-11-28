"""Ficha 06 · Passo 2: dados em volume, para medir.

    uv run python manage.py seed          # primeiro o seed de demonstração (viaturas, contas)
    uv run python manage.py seed_big      # depois o volume: 50 000 encomendas e as filhas

Só para desenvolvimento, nunca em produção, e à parte do seed do M2 (que fica igual).
Cria, com bulk_create em lotes de 5 000 (nunca um create() por linha):
  - 2 000 clientes (utilizadores big-00000…, com a password do seed de demonstração);
  - 50 000 encomendas com 1 ou 2 linhas, distribuídas de forma desigual pelos estados;
  - um pagamento por encomenda paga ou entregue, com o total das linhas;
  - as entregas (recurso do Diogo): todas as encomendas entregues e 2 em cada 3 pagas;
  - 20 000 avaliações (recurso do Filipe) e 20 000 test drives (recurso do Rúben).
As datas ficam espalhadas por dois anos: o auto_now_add põe tudo com a hora de agora, por
isso um UPDATE no fim (em SQL, com random()) muda o created_at das encomendas e das entregas.
"""

import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from deliveries.models import Delivery
from reviews.models import Review
from shop.management.commands.seed import DEMO_PASSWORD
from shop.models import Car, Customer, Order, OrderItem, Payment
from testdrives.models import TestDrive

BATCH = 5_000
PREFIX = "big-"

# 1 em cada 10 pendente, 2 canceladas, 3 pagas e 4 entregues: os índices notam-se nos
# estados com poucas linhas.
ORDER_STATUS = ["pending", "cancelled", "cancelled", "paid", "paid", "paid"] + ["delivered"] * 4
REVIEW_STATUS = ["pending"] + ["approved"] * 8 + ["hidden"]
TESTDRIVE_STATUS = ["requested"] + ["confirmed"] * 5 + ["declined"] * 2 + ["cancelled"] * 2
METHODS = [m for m, _ in Payment.Method.choices]


class Command(BaseCommand):
    help = "Ficha 06: dados em volume (50 000 encomendas e as filhas). Só em desenvolvimento."

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=2_000)
        parser.add_argument("--orders", type=int, default=50_000)
        parser.add_argument("--reviews", type=int, default=20_000)
        parser.add_argument("--test-drives", type=int, default=20_000)

    @transaction.atomic
    def handle(self, *args, **opts):
        cars = list(Car.objects.order_by("id"))
        if not cars:
            raise CommandError("Sem viaturas: corre primeiro o seed de demonstração (seed).")
        User = get_user_model()
        if User.objects.filter(username__startswith=PREFIX).exists():
            self.stdout.write("O volume já lá está (utilizadores big-…): nada a fazer.")
            return
        started = time.perf_counter()
        customers = self.customers(User, opts["customers"])
        orders = self.orders(customers, cars, opts["orders"])
        deliveries = self.deliveries(orders)
        reviews = self.reviews(customers, cars, opts["reviews"])
        test_drives = self.test_drives(customers, cars, opts["test_drives"])
        self.spread_dates()
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_big: +{len(customers)} clientes, +{len(orders)} encomendas, "
                f"+{deliveries} entregas, +{reviews} avaliações, +{test_drives} test drives "
                f"em {time.perf_counter() - started:.1f} s. "
                f"Total: {Order.objects.count()} encomendas, {Delivery.objects.count()} entregas."
            )
        )

    def customers(self, User, n):
        password = make_password(DEMO_PASSWORD)  # um hash só: o Argon2 leva ~0,1 s por hash
        users = User.objects.bulk_create(
            [
                User(
                    username=f"{PREFIX}{i:05d}",
                    email=f"{PREFIX}{i:05d}@example.com",
                    password=password,
                )
                for i in range(n)
            ],
            batch_size=BATCH,
        )
        return Customer.objects.bulk_create(
            [Customer(user=u, address=f"Rua do Volume, {i}, Porto") for i, u in enumerate(users)],
            batch_size=BATCH,
        )

    def orders(self, customers, cars, n):
        orders = Order.objects.bulk_create(
            [
                Order(customer=customers[i % len(customers)], status=ORDER_STATUS[i % 10])
                for i in range(n)
            ],
            batch_size=BATCH,
        )
        items, payments = [], []
        for i, order in enumerate(orders):
            # 1 linha em 2 de cada 3 encomendas, 2 linhas na outra (viaturas diferentes).
            lines = [cars[i % len(cars)]]
            if i % 3 == 0:
                lines.append(cars[(i + 7) % len(cars)])
            items += [OrderItem(order=order, car=c, quantity=1, unit_price=c.price) for c in lines]
            if order.status in ("paid", "delivered"):
                amount = sum(c.price for c in lines)
                payments.append(
                    Payment(order=order, method=METHODS[i % len(METHODS)], amount=amount)
                )
        OrderItem.objects.bulk_create(items, batch_size=BATCH)
        Payment.objects.bulk_create(payments, batch_size=BATCH)
        return orders

    def deliveries(self, orders):
        now = timezone.now()
        rows = []
        for i, order in enumerate(orders):
            if order.status == "delivered":
                when = now - timedelta(days=1 + i % 700)
                rows.append(
                    Delivery(
                        order=order,
                        status="delivered",
                        scheduled_for=when,
                        delivered_at=when,
                        address="Rua do Volume, Porto",
                    )
                )
            elif order.status == "paid" and i % 3:
                # 1 em cada 10 já passou a data sem ser entregue: em atraso.
                days = -(1 + i % 20) if i % 10 == 4 else 1 + i % 30
                status = "in_transit" if i % 2 else "scheduled"
                rows.append(
                    Delivery(
                        order=order,
                        status=status,
                        scheduled_for=now + timedelta(days=days),
                        address="Rua do Volume, Porto",
                    )
                )
        Delivery.objects.bulk_create(rows, batch_size=BATCH)
        return len(rows)

    def reviews(self, customers, cars, n):
        # Uma por (viatura, cliente): a restrição única leva o i (cliente i // n.º de viaturas).
        n = min(n, len(customers) * len(cars))
        rows = [
            Review(
                car=cars[i % len(cars)],
                customer=customers[i // len(cars)],
                rating=1 + i % 5,
                comment="Avaliação de volume.",
                status=REVIEW_STATUS[i % 10],
            )
            for i in range(n)
        ]
        Review.objects.bulk_create(rows, batch_size=BATCH)
        return n

    def test_drives(self, customers, cars, n):
        # Uma hora diferente por marcação, sempre às :30 (as do seed de demonstração são às
        # horas certas): nunca duas ativas na mesma viatura e horário.
        start = timezone.now().replace(minute=30, second=0, microsecond=0) - timedelta(days=365)
        rows = [
            TestDrive(
                car=cars[i % len(cars)],
                customer=customers[i % len(customers)],
                scheduled_for=start + timedelta(hours=i),
                status=TESTDRIVE_STATUS[i % 10],
            )
            for i in range(n)
        ]
        TestDrive.objects.bulk_create(rows, batch_size=BATCH)
        return n

    def spread_dates(self):
        """O auto_now_add pôs tudo com a hora de agora: datas espalhadas por dois anos."""
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE shop_order SET created_at = now() - random() * interval '730 days' "
                "WHERE customer_id IN (SELECT c.id FROM shop_customer c "
                "JOIN accounts_user u ON u.id = c.user_id WHERE u.username LIKE %s)",
                [PREFIX + "%"],
            )
            cursor.execute(
                "UPDATE deliveries_delivery d SET created_at = o.created_at "
                "FROM shop_order o WHERE o.id = d.order_id AND d.created_at > o.created_at"
            )
