"""Marcar e mudar o estado de um test drive, com a linha bloqueada."""

from django.db import IntegrityError, transaction

from shop.services import Conflict

from .models import TestDrive


def book_test_drive(customer, car, scheduled_for, notes=""):
    """Cria a marcação. Se outro cliente ficou com o horário entretanto, dá 409."""
    try:
        with transaction.atomic():
            return TestDrive.objects.create(
                customer=customer, car=car, scheduled_for=scheduled_for, notes=notes
            )
    except IntegrityError:
        # A uq_testdrive_car_slot_active apanhou o caso concorrente que o serializer não viu.
        raise Conflict("Este horário acabou de ser marcado por outro cliente.") from None


@transaction.atomic
def change_status(test_drive, new_status, allowed_from):
    test_drive = TestDrive.objects.select_for_update().get(pk=test_drive.pk)
    if test_drive.status not in allowed_from:
        raise Conflict(
            f"O test drive está '{test_drive.get_status_display()}' e já não pode mudar assim."
        )
    test_drive.status = new_status
    test_drive.save(update_fields=["status"])
    return test_drive


def confirm(test_drive):
    return change_status(test_drive, TestDrive.Status.CONFIRMED, [TestDrive.Status.REQUESTED])


def decline(test_drive):
    return change_status(test_drive, TestDrive.Status.DECLINED, [TestDrive.Status.REQUESTED])


def cancel(test_drive):
    return change_status(test_drive, TestDrive.Status.CANCELLED, TestDrive.ACTIVE)
