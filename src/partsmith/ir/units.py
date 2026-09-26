"""Explicit source units with exact decimal conversion to mm/degrees."""

from decimal import Decimal, localcontext

from partsmith.ir.canonical import decimal_number
from partsmith.ir.errors import fail

UNITS = {
    "mm": ("mm", Decimal("1")),
    "mil": ("mm", Decimal("0.0254")),
    "inch": ("mm", Decimal("25.4")),
    "um": ("mm", Decimal("0.001")),
    "µm": ("mm", Decimal("0.001")),
    "μm": ("mm", Decimal("0.001")),
    "deg": ("deg", Decimal("1")),
    "degree": ("deg", Decimal("1")),
    "degrees": ("deg", Decimal("1")),
}


def normalize_quantity(value, unit: str) -> tuple[Decimal, str]:
    """Return normalized value/unit without guessing or rounding."""
    if not isinstance(unit, str) or unit not in UNITS:
        fail("", "IR_UNIT", "Unsupported or missing source unit")
    target, factor = UNITS[unit]
    with localcontext() as context:
        context.prec = 256
        return decimal_number(decimal_number(value) * factor), target
