"""Unit tests for the strict kitchen ticket state machine."""
import pytest

from app.models.kitchen import KitchenTicketStatus
from app.services.kitchen_service import validate_kitchen_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (KitchenTicketStatus.NEW, KitchenTicketStatus.ACCEPTED),
        (KitchenTicketStatus.ACCEPTED, KitchenTicketStatus.PREPARING),
        (KitchenTicketStatus.PREPARING, KitchenTicketStatus.READY),
    ],
)
def test_valid_kitchen_transitions(current, target):
    assert validate_kitchen_transition(current, target) == (current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (KitchenTicketStatus.NEW, KitchenTicketStatus.PREPARING),
        (KitchenTicketStatus.NEW, KitchenTicketStatus.READY),
        (KitchenTicketStatus.ACCEPTED, KitchenTicketStatus.READY),
        (KitchenTicketStatus.READY, KitchenTicketStatus.ACCEPTED),
        (KitchenTicketStatus.PREPARING, KitchenTicketStatus.NEW),
    ],
)
def test_invalid_kitchen_transitions_are_rejected(current, target):
    with pytest.raises(ValueError):
        validate_kitchen_transition(current, target)
