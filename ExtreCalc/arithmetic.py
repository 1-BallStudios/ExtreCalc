from biginteger import BigInt
from bigdecimal import BigDecimal
from decimal import Decimal
from scinot import SciNot
from powertower import PowerTower
from context import DEFAULT_CONTEXT, ArithmeticContext

MAX_BIGINT_SCINOT_CONVERSION_DIGITS = 4000
SCINOT_CONVERSION_PRECISION = 30

from decimal import Decimal, localcontext
from scinot import SciNot


def integer_power_to_scinot(base, exponent, precision=28):
    """Approximate an integer power directly as SciNot, without building it."""
    if isinstance(base, bool) or not isinstance(base, int):
        raise TypeError("Base must be an integer.")
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("Exponent must be an integer.")
    if exponent < 0:
        raise ValueError("Exponent must be nonnegative.")
    if base == 0:
        return SciNot(0)
    if exponent == 0:
        return SciNot(1)

    negative = base < 0 and exponent % 2 == 1
    base = abs(base)

    if base == 1:
        return SciNot(-1 if negative else 1)

    with localcontext() as ctx:
        ctx.prec = precision + 10

        log_value = Decimal(base).log10() * exponent
        sci_exponent = int(log_value // 1)
        fractional_part = log_value - sci_exponent
        coefficient = Decimal(10) ** fractional_part

        if negative:
            coefficient = -coefficient

        ctx.prec = precision
        return SciNot(+coefficient, sci_exponent)

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

def _scinot_to_powertower(value):
    """Convert sufficiently large exact powers of ten to PowerTower."""
    if value.exponent <= MAX_BIGINT_SCINOT_CONVERSION_DIGITS:
        return None

    if value.coefficient != 1:
        return None

    return PowerTower(1, value.exponent)

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

    if isinstance(a, PowerTower) or isinstance(b, PowerTower):
        def convert(value):
            if isinstance(value, PowerTower):
                return value
            if isinstance(value, BigInt):
                return PowerTower(0, str(value))
            if isinstance(value, int) and not isinstance(value, bool):
                return PowerTower(0, str(value))
            if isinstance(value, str):
                return PowerTower(0, value)
            raise TypeError(
                f"Cannot mix PowerTower with {type(value).__name__}"
            )

        return convert(a), convert(b), "powertower"
    
    if isinstance(a, SciNot) or isinstance(b, SciNot):
        if isinstance(a, BigDecimal) or isinstance(b, BigDecimal):
            raise TypeError(
                "Mixed SciNot and BigDecimal operations "
                "are not supported yet."
            )
    
        def convert(value):
            if isinstance(value, SciNot):
                tower = _scinot_to_powertower(value)
                return tower if tower is not None else value

            if isinstance(value, BigInt):
                return _bigint_to_scinot(value)

            return SciNot.parse(str(value))

        a_converted = convert(a)
        b_converted = convert(b)

        if isinstance(a_converted, PowerTower) or isinstance(
            b_converted, PowerTower
        ):
            return a_converted, b_converted, "powertower"

        return a_converted, b_converted, "scinot"
    
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

    a, b, kind = _prepare_pair(a, b)

    if kind == "powertower":
        return a / b

    if kind == "bigdecimal":
        return a.__truediv__(
            b,
            precision=context.precision,
            rounding=context.rounding,
        )

    if kind == "scinot":
        return a / b

    if kind == "bigint":
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return a / b

    raise TypeError(f"Unsupported division type: {kind}")


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

def power(a, b):
    a = to_bigint_exact(a)
    b = to_bigint_exact(b)
        # Extract the underlying Python integers from BigInt.
    base = a.value
    exponent = b.value

    if (
        exponent >= 0
        and abs(base) > 1
        and exponent * abs(base).bit_length()
            > MAX_BIGINT_SCINOT_CONVERSION_DIGITS * 3.322
    ):
        return integer_power_to_scinot(base, exponent)

    return a**b

def negate(a):
    a, b, kind = _prepare_pair(a, -1)

    if kind == "scinot":
        return a * -1

    return a * -1