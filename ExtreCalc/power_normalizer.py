from decimal import Decimal, localcontext
from bigdecimal import BigDecimal
from powertower import PowerTower
from scinot import SciNot
from biginteger import BigInt
import sys
import arithmetic
sys.set_int_max_str_digits(0)

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

def _bounded_exact_power_chain(bases, max_bits):
    """Evaluate a right-associative power chain within a bit budget."""
    result = bases[-1]


    for base in reversed(bases[:-1]):
        # Conservative estimate: check before constructing the power.
        if result * base.bit_length() > max_bits:
            raise OverflowError("Exact power-chain limit reached.")


        result = pow(base, result)


        if result.bit_length() > max_bits:
            raise OverflowError("Exact power-chain limit reached.")


    return result

def _approximate_chain_tower(bases, precision, max_bits):
    """
    Approximate a power chain as a base-10 PowerTower.


    Uses exact evaluation for manageable subchains and logarithmic
    identities for larger ones.
    """
    try:
        exact = _bounded_exact_power_chain(bases, max_bits)
        return PowerTower(0, str(exact))
    except OverflowError:
        pass


    if len(bases) == 1:
        return PowerTower(0, str(bases[0]))


    # Approximate the exponent first.
    exponent = _approximate_chain_tower(
        bases[1:], precision, max_bits
    )


    with localcontext() as ctx:
        ctx.prec = precision


        log_base = Decimal(bases[0]).log10()


        if exponent.height == 0:
            # b^E = 10^(E * log10(b))
            top = Decimal(str(exponent.top)) * log_base
            return PowerTower(1, str(+top))


        if exponent.height == 1:
            # E = 10^x
            # b^E = 10^(10^(x + log10(log10(b))))
            top = (
                Decimal(str(exponent.top))
                + log_base.log10()
            )
            return PowerTower(2, str(+top))


        # At this scale, multiplying the exponent by log10(b)
        # has a negligible effect at the requested precision.
        return PowerTower(
            exponent.height + 1,
            str(exponent.top),
        )

def normalize_power_chain(bases, precision=40):
    """
    Hybrid normalization of a right-associative integer power chain.


    Small chains use exact evaluation followed by logarithmic conversion.
    Large chains use recursive PowerTower approximation.
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


    if precision < 1:
        raise ValueError("Precision must be positive.")


    max_bits = 100_000


    # Preserve the existing normalization format for manageable chains.
    try:
        exact = _bounded_exact_power_chain(bases, max_bits)


        with localcontext() as ctx:
            ctx.prec = precision
            top = Decimal(exact).log10()
            return PowerTower(1, str(+top))


    except OverflowError:
        # Unlike the previous hybrid, this is a real approximation path.
        return _approximate_chain_tower(
            bases, precision, max_bits
        )
    
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
    if value.height == 1 and BigDecimal.compare(value.top, BigDecimal(1, 10**arithmetic.MAX_BIGINT_SCINOT_CONVERSION_DIGITS, 0)) == -1:
        with localcontext() as ctx:
            ctx.prec = precision
            x = Decimal(str(value.top))

            whole = int(x)
            fraction = x - Decimal(whole)
            coefficient = Decimal(10) ** fraction

            return SciNot(coefficient, whole)

    return value   