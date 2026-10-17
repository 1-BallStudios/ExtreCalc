from decimal import Decimal, localcontext

from powertower import PowerTower
from scinot import SciNot

MAX_EXACT_BITS = 100_000


def _eval_power_chain(bases):
    """Evaluate a right-associated power chain when it stays manageable."""
    if not bases:
        raise ValueError("Power chain cannot be empty.")

    result = bases[-1]

    for base in reversed(bases[:-1]):
        if not isinstance(base, int) or isinstance(base, bool):
            raise TypeError("This version requires integer bases.")

        if not isinstance(result, int) or isinstance(result, bool):
            raise TypeError("This version requires integer exponents.")

        if result < 0:
            raise ValueError("Negative exponents are not supported.")

        if base < 0:
            raise ValueError("Negative bases are not supported.")

        if base in (0, 1):
            result = base
            continue

        # Avoid calculating a result that would exceed our safety bound.
        if result > MAX_EXACT_BITS:
            raise OverflowError(
                "Power chain exceeds the exact-evaluation limit."
            )

        if result * max(1, base.bit_length() - 1) > MAX_EXACT_BITS:
            raise OverflowError(
                "Power chain exceeds the exact-evaluation limit."
            )

        result = base ** result

        if result.bit_length() > MAX_EXACT_BITS:
            raise OverflowError(
                "Power chain exceeds the exact-evaluation limit."
            )

    return result

def normalize_number(value, precision=30):
    """Approximate a positive number using PowerTower notation."""
    value = Decimal(str(value))

    if not value.is_finite() or value < 0:
        raise ValueError("Value must be finite and non-negative.")

    if value == 0:
        return PowerTower(0, "0")

    if value == 1:
        return PowerTower(0, "1")

    with localcontext() as ctx:
        ctx.prec = precision

        height = 0

        # Repeated logarithms reduce the magnitude without
        # constructing an expanded power tower.
        while value >= 10:
            value = value.log10()
            height += 1

        # Undo the final logarithm count in the representation:
        # hPTx means h nested powers of ten ending in x.
        return PowerTower(height, str(value))
    
def normalize_power_chain(bases, precision=40):
    """
    Approximate a right-associative integer power chain as PowerTower.

    Example:
        [20, 19, 18, ..., 11, 10]
    """
    if not bases or any(
        isinstance(n, bool) or not isinstance(n, int)
        for n in bases
    ):
        raise TypeError("Power-chain bases must be integers.")

    if any(n <= 1 for n in bases):
        raise ValueError(
            "This normalizer currently requires every base to exceed 1."
        )

    if len(bases) < 3:
        raise ValueError("A chain must contain at least three bases.")

    with localcontext() as ctx:
        ctx.prec = precision

        # Each logarithm removes one outer power.
        # Stop with the final two bases, whose power is manageable.
        remaining = len(bases) - 2
        coefficient = Decimal(0)
        correction = Decimal(0)

        for i in range(remaining):
            previous_coefficient = coefficient
            coefficient = Decimal(bases[i]).log10()

            if i > 0:
                correction = previous_coefficient.log10()

        # Evaluate only the final, small power.
        tail = Decimal(bases[-2]) ** bases[-1]
        top = coefficient * tail + correction
        return PowerTower(remaining, str(+top))

def normalize_powertower(value, max_digits=1000, precision=30):
    """Convert a PowerTower to BigInt or SciNot when practical."""
    if not isinstance(value, PowerTower):
        return value

    # Reuse the existing exact conversion.
    try:
        integer = value.to_int(max_digits=max_digits)
        return BigInt(integer)
    except (OverflowError, ValueError):
        pass

    # A 1PTx tower means 10**x.
    if value.height == 1:
        with localcontext() as ctx:
            ctx.prec = precision
            x = Decimal(str(value.top))

            whole = int(x // 1)
            fraction = x - Decimal(whole)
            coefficient = Decimal(10) ** fraction

            return SciNot(coefficient, whole)

    return value