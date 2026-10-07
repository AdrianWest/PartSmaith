"""@package partsmith.integration.units
@brief Converts exact engineering coordinates to pinned KiCad PCB units.
@details Adapter 1.0 maps engineering millimeters/Y-up to integer native
nanometers/Y-down. Positive degree angles retain their physical direction.
Bottom-side and general affine placement are separate explicit transforms.
"""

from decimal import Decimal, InvalidOperation, localcontext
from math import isfinite

COORDINATE_ADAPTER_VERSION = "kicad-pcb-units-1.0"
ENGINEERING_CONVENTION_VERSION = "1.1"
NANOMETERS_PER_MM = 1_000_000
NATIVE_MIN = -(2**31)
NATIVE_MAX = 2**31 - 1


class UnitConversionError(ValueError):
    """@brief Reports unsupported precision, units or native ranges.
    @details Diagnostics are value-free and never silently round or truncate.
    """


def _decimal(value: Decimal | str | int) -> Decimal:
    """@brief Validates one bounded exact decimal engineering value.
    @param value Decimal, decimal text or integer engineering scalar.
    @return Finite Decimal with a bounded representation.
    @details Floats and booleans are rejected before exact conversions.
    """
    if type(value) not in (Decimal, str, int):
        raise UnitConversionError("EXACT_DECIMAL_REQUIRED")
    if isinstance(value, str) and len(value) > 128:
        raise UnitConversionError("DECIMAL_RESOURCE_LIMIT")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise UnitConversionError("INVALID_DECIMAL") from None
    if not number.is_finite():
        raise UnitConversionError("NONFINITE_DECIMAL")
    parts = number.as_tuple()
    if len(parts.digits) > 64 or abs(parts.exponent) > 64:
        raise UnitConversionError("DECIMAL_RESOURCE_LIMIT")
    return number


def _native(value: int) -> int:
    """@brief Checks one signed native PCB coordinate.
    @param value Integer distance in nanometers.
    @return Original integer after range validation.
    @details VECTOR2I bounds apply even though protobuf uses int64.
    """
    if type(value) is not int or not NATIVE_MIN <= value <= NATIVE_MAX:
        raise UnitConversionError("NATIVE_COORDINATE_RANGE")
    return value


def millimeters_to_nanometers(value: Decimal | str | int) -> int:
    """@brief Converts an exactly representable distance to nanometers.
    @param value Engineering millimeters as an exact decimal value.
    @return Signed native integer nanometers.
    @details Rejects sub-nanometer precision and overflow rather than rounding.
    """
    with localcontext() as context:
        context.prec = 80
        scaled = _decimal(value) * NANOMETERS_PER_MM
        if scaled != scaled.to_integral_value():
            raise UnitConversionError("SUB_NANOMETER_PRECISION")
        if not NATIVE_MIN <= scaled <= NATIVE_MAX:
            raise UnitConversionError("NATIVE_COORDINATE_RANGE")
        return int(scaled)


def nanometers_to_millimeters(value: int) -> Decimal:
    """@brief Converts a native distance to exact engineering millimeters.
    @param value Signed native integer nanometers.
    @return Exact finite Decimal millimeters.
    @details Conversion is independent of the caller's decimal context.
    """
    with localcontext() as context:
        context.prec = 80
        return Decimal(_native(value)) / NANOMETERS_PER_MM


def engineering_to_native(
    x_mm: Decimal | str | int, y_mm: Decimal | str | int
) -> tuple[int, int]:
    """@brief Maps an engineering top-view point into native PCB coordinates.
    @param x_mm Engineering positive-right millimeters.
    @param y_mm Engineering positive-up millimeters.
    @return Native positive-right/positive-down nanometer pair.
    @details The explicit Y-axis inversion introduces no implicit side mirror.
    """
    with localcontext() as context:
        context.prec = 80
        return (
            millimeters_to_nanometers(x_mm),
            millimeters_to_nanometers(-_decimal(y_mm)),
        )


def native_to_engineering(x_nm: int, y_nm: int) -> tuple[Decimal, Decimal]:
    """@brief Maps a native PCB point into the engineering top-view frame.
    @param x_nm Native positive-right integer nanometers.
    @param y_nm Native positive-down integer nanometers.
    @return Engineering positive-right/positive-up Decimal millimeter pair.
    @details Preserves all native coordinate precision and signed limits.
    """
    with localcontext() as context:
        context.prec = 80
        return (
            nanometers_to_millimeters(x_nm),
            -nanometers_to_millimeters(y_nm),
        )


def engineering_angle_to_native(value: Decimal | str | int) -> float:
    """@brief Converts exact engineering degree orientation to native degrees.
    @param value Active right-hand-positive engineering degree angle.
    @return Native degree float preserving decimal round-trip identity.
    @details Native positive rotation already accounts for its Y-down frame;
    angle sign remains unchanged. Unsupported floating precision is rejected.
    """
    number = _decimal(value)
    result = float(number)
    if not isfinite(result) or Decimal(str(result)) != number:
        raise UnitConversionError("NATIVE_ANGLE_PRECISION")
    return result


def native_angle_to_engineering(value: float) -> Decimal:
    """@brief Reads native degree orientation into an explicit decimal angle.
    @param value Finite native IEEE-754 degree value.
    @return Decimal of the float's shortest exact round-trip representation.
    @details No axis sign change or normalization is hidden in this conversion.
    """
    if type(value) is not float or not isfinite(value):
        raise UnitConversionError("INVALID_NATIVE_ANGLE")
    return _decimal(str(value))
