from biginteger import BigInt
from bigdecimal import BigDecimal
from decimal import Decimal
from scinot import SciNot
from context import DEFAULT_CONTEXT, ArithmeticContext

MAX_BIGINT_SCINOT_CONVERSION_DIGITS = 1_000_000
SCINOT_CONVERSION_PRECISION = 30

def to_bigdecimal(value):
    """Convert an integer or supported value to BigDecimal exactly."""
    if isinstance(value, BigDecimal):
        return value

    if isinstance(value, BigInt):
        value = str(value)
    elif isinstance(value, int):
        value = str(value)
    elif isinstance(value, float):
        raise TypeError(
            "Float conversion is disabled to avoid precision loss."
        )

    return BigDecimal.parse(str(value))


def to_bigint_exact(value):
    """Convert to BigInt only when the value is an exact integer."""
    if isinstance(value, BigInt):
        return value

    if isinstance(value, int):
        return BigInt(value)

    decimal = to_bigdecimal(value)

    if decimal.sign == 0:
        return BigInt(0)

    if decimal.exponent >= 0:
        integer = decimal.coefficient * 10 ** decimal.exponent
    else:
        divisor = 10 ** (-decimal.exponent)

        if decimal.coefficient % divisor != 0:
            raise ValueError("Value is not an exact integer.")

        integer = decimal.coefficient // divisor

    return BigInt(decimal.sign * integer)

def _bigint_to_scinot(value):
    """Convert BigInt to SciNot, rounding to 30 significant digits."""
    integer = value.value if isinstance(value, BigInt) else int(value)

    if integer == 0:
        return SciNot(0)

    sign = -1 if integer < 0 else 1
    integer = abs(integer)

    # Convert to decimal text in chunks of nine digits.
    base = 1_000_000_000
    chunks = []

    while integer:
        integer, remainder = divmod(integer, base)
        chunks.append(remainder)

        # Avoid spending excessive time converting enormous integers.
        if len(chunks) * 9 > MAX_BIGINT_SCINOT_CONVERSION_DIGITS + 9:
            raise OverflowError("BigInt exceeds the SciNot conversion cap.")

    digits = str(chunks[-1]) + "".join(
        f"{chunk:09d}" for chunk in reversed(chunks[:-1])
    )

    if len(digits) > MAX_BIGINT_SCINOT_CONVERSION_DIGITS:
        raise OverflowError("BigInt exceeds the SciNot conversion cap.")

    precision = SCINOT_CONVERSION_PRECISION
    leading = digits[:precision]

    # Round half-up using the first discarded digit.
    if len(digits) > precision and digits[precision] >= "5":
        leading = str(int(leading) + 1)

    coefficient = Decimal(leading).scaleb(-(len(leading) - 1))
    return SciNot(sign * coefficient, len(digits) - 1)


def _prepare_pair(a, b):
    """Choose compatible representations for arithmetic operands."""

    if isinstance(a, float) or isinstance(b, float):
        raise TypeError("Float operands are not supported; use strings.")

    if isinstance(a, SciNot) or isinstance(b, SciNot):
        if isinstance(a, BigDecimal) or isinstance(b, BigDecimal):
            raise TypeError(
                "Mixed SciNot and BigDecimal operations "
                "are not supported yet."
            )

        def convert(value):
            if isinstance(value, SciNot):
                return value
            if isinstance(value, BigInt):
                return _bigint_to_scinot(value)
            return SciNot.parse(str(value))

        return convert(a), convert(b), "scinot"

    if any(
        isinstance(value, str)
        and ("e" in value.lower() or "* 10^" in value)
        for value in (a, b)
    ):
        return SciNot.parse(str(a)), SciNot.parse(str(b)), "scinot"

    if isinstance(a, BigDecimal) or isinstance(b, BigDecimal):
        return to_bigdecimal(a), to_bigdecimal(b), "bigdecimal"

    if any(
        isinstance(value, str) and "." in value
        for value in (a, b)
    ):
        return to_bigdecimal(a), to_bigdecimal(b), "bigdecimal"

    return BigInt(a), BigInt(b), "bigint"

def add(a, b):
    a, b, kind = _prepare_pair(a, b)
    return a + b


def subtract(a, b):
    a, b, kind = _prepare_pair(a, b)
    return a - b


def multiply(a, b):
    a, b, kind = _prepare_pair(a, b)

    if kind == "scinot":
        return a * b

    return a * b


def divide(a, b, context=None):
    if context is None:
        context = DEFAULT_CONTEXT

    if not isinstance(context, ArithmeticContext):
        raise TypeError("context must be an ArithmeticContext")

    a = to_bigdecimal(a)
    b = to_bigdecimal(b)

    return a.__truediv__(
        b,
        precision=context.precision,
        rounding=context.rounding,
    )


def integer_divide(a, b):
    a = to_bigint_exact(a)
    b = to_bigint_exact(b)

    if b.value == 0:
        raise ZeroDivisionError("Cannot divide by zero")

    quotient = abs(a.value) // abs(b.value)

    if (a.value < 0) != (b.value < 0):
        quotient = -quotient

    return BigInt(quotient)


def remainder(a, b):
    a = to_bigint_exact(a)
    b = to_bigint_exact(b)

    if b.value == 0:
        raise ZeroDivisionError("Cannot divide by zero")

    quotient = integer_divide(a, b).value
    return BigInt(a.value - quotient * b.value)