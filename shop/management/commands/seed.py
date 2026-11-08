import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify

from accounts.factories import UserFactory
from deliveries.models import Delivery
from deliveries.services import complete_delivery, ship_delivery
from shop.factories import BrandFactory, CarFactory, CustomerFactory
from shop.models import Brand, Car, Customer, Order, Payment
from shop.permissions import GESTORES
from shop.services import create_order, pay_order

# Catálogo de demonstração do DriveNow: (marca, modelo, versão, combustível, preço base).
CATALOGUE = [
    ("Volkswagen", "Golf", "1.5 eTSI Life", Car.Fuel.PETROL, "32500"),
    ("Volkswagen", "ID.3", "Pro 58 kWh", Car.Fuel.ELECTRIC, "39900"),
    ("Volkswagen", "Polo", "1.0 TSI Style", Car.Fuel.PETROL, "24900"),
    ("Renault", "Clio", "1.5 Blue dCi Evolution", Car.Fuel.DIESEL, "22800"),
    ("Renault", "Mégane E-Tech", "EV60 Techno", Car.Fuel.ELECTRIC, "41500"),
    ("Renault", "Captur", "E-Tech Full Hybrid", Car.Fuel.HYBRID, "30900"),
    ("Peugeot", "208", "1.2 PureTech Allure", Car.Fuel.PETROL, "23400"),
    ("Peugeot", "3008", "Hybrid 136 GT", Car.Fuel.HYBRID, "42700"),
    ("BMW", "Série 1", "118d M Sport", Car.Fuel.DIESEL, "38900"),
    ("BMW", "iX1", "eDrive20", Car.Fuel.ELECTRIC, "52300"),
    ("Mercedes-Benz", "Classe A", "A 180 d Progressive", Car.Fuel.DIESEL, "39600"),
    ("Mercedes-Benz", "GLA", "250 e AMG Line", Car.Fuel.HYBRID, "54900"),
    ("Toyota", "Yaris", "1.5 Hybrid Comfort", Car.Fuel.HYBRID, "23900"),
    ("Toyota", "Corolla", "1.8 Hybrid Exclusive", Car.Fuel.HYBRID, "33200"),
    ("Toyota", "C-HR", "2.0 Hybrid GR Sport", Car.Fuel.HYBRID, "41900"),
    ("Tesla", "Model 3", "RWD", Car.Fuel.ELECTRIC, "42990"),
    ("Tesla", "Model Y", "Long Range AWD", Car.Fuel.ELECTRIC, "52990"),
    ("SEAT", "Ibiza", "1.0 TSI FR", Car.Fuel.PETROL, "21900"),
    ("SEAT", "Leon", "2.0 TDI Xcellence", Car.Fuel.DIESEL, "33800"),
    ("Dacia", "Sandero", "1.0 TCe Expression", Car.Fuel.PETROL, "16200"),
]

# Contas de demonstração (também no README). Só para dev: o seed nunca corre em produção.
DEMO_PASSWORD = "drivenow-demo-2026"
DEMO_GESTOR = "gestor"
DEMO_CUSTOMERS = ["ana", "bruno", "carla"]
STATES = [Order.Status.PENDING, Order.Status.PAID, Order.Status.DELIVERED, Order.Status.CANCELLED]


class Command(BaseCommand):
    help = "Preenche a BD com dados de demonstração do DriveNow. Pode correr várias vezes."

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=10)
        parser.add_argument("--orders", type=int, default=30)

    @transaction.atomic
    def handle(self, *args, **opts):
        self.catalogue()
        self.demo_accounts()

        # Idempotente: só cria o que falta para chegar aos totais pedidos.
        missing = opts["customers"] - Customer.objects.count()
        CustomerFactory.create_batch(max(missing, 0))
        customers = list(Customer.objects.all())
        missing = opts["orders"] - Order.objects.count()
        for _ in range(max(missing, 0)):
            self.order(random.choice(customers), random.choice(STATES))

        self.stdout.write(
            self.style.SUCCESS(
                f"{Brand.objects.count()} marcas, "
                f"{Car.objects.count()} viaturas, "
                f"{Customer.objects.count()} clientes, "
                f"{Order.objects.count()} encomendas, "
                f"{Payment.objects.count()} pagamentos. "
                f"Contas: {DEMO_GESTOR} (gestor) e {', '.join(DEMO_CUSTOMERS)} (clientes), "
                f"password {DEMO_PASSWORD}"
            )
        )

    def catalogue(self):
        # Catálogo fixo: get_or_create pelo slug/código, por isso correr de novo não duplica.
        for i, (brand_name, model, version, fuel, price) in enumerate(CATALOGUE, start=1):
            brand = BrandFactory(name=brand_name, slug=slugify(brand_name))
            CarFactory(
                code=f"DN-{i:04d}",
                brand=brand,
                model=model,
                version=version,
                fuel=fuel,
                year=2024 + i % 3,  # 2024, 2025 ou 2026
                price=Decimal(price),
                stock=10 + i % 6 * 2,  # 10 a 20 unidades
            )
        # Uma viatura retirada de venda, para se ver o is_active=False no catálogo.
        Car.objects.filter(code="DN-0020").update(is_active=False)

    def demo_accounts(self):
        gestor = UserFactory(username=DEMO_GESTOR, password=DEMO_PASSWORD)
        gestor.groups.add(Group.objects.get(name=GESTORES))  # o grupo vem da migração 0002
        for username in DEMO_CUSTOMERS:
            user = UserFactory(username=username, password=DEMO_PASSWORD)
            customer = CustomerFactory(user=user)
            if not customer.orders.exists():
                for status in STATES:  # uma encomenda em cada estado
                    self.order(customer, status)

    def order(self, customer, status):
        """Cria uma encomenda pelos mesmos serviços da API e leva-a até `status`."""
        cars = list(Car.objects.filter(is_active=True, stock__gte=2))
        lines = [
            {"car": car, "quantity": random.randint(1, 2)}
            for car in random.sample(cars, k=min(len(cars), random.randint(1, 2)))
        ]
        if not lines:
            return None  # stock esgotado: não inventa encomendas impossíveis
        order = create_order(customer, lines)
        if status in (Order.Status.PAID, Order.Status.DELIVERED):
            pay_order(order, random.choice(Payment.Method.values))
        if status == Order.Status.PAID and random.random() < 0.5:
            # Metade das pagas já tem a entrega marcada; algumas já saíram do stand.
            delivery = self.delivery(order, days=random.randint(1, 14))
            if random.random() < 0.5:
                ship_delivery(delivery)
        if status == Order.Status.DELIVERED:
            # Como na API: é o complete_delivery que passa a encomenda a "entregue".
            complete_delivery(self.delivery(order, days=-random.randint(1, 10)))
        if status == Order.Status.CANCELLED:
            for item in order.items.all():  # devolve as unidades ao stock
                Car.objects.filter(pk=item.car_id).update(stock=F("stock") + item.quantity)
            Order.objects.filter(pk=order.pk).update(status=Order.Status.CANCELLED)
        return order

    def delivery(self, order, days):
        """Agenda a entrega a `days` dias de hoje (negativo: no passado)."""
        delivery, _ = Delivery.objects.get_or_create(
            order=order,
            defaults={
                "scheduled_for": timezone.now() + timedelta(days=days),
                "address": order.customer.address or "Rua da Demonstração, 1, Porto",
            },
        )
        return delivery
