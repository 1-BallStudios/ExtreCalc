from dataclasses import dataclass
import re
import math

DEFAULT_PRECISION = 30
DEFAULT_ROUNDING = "half_up"

SUPPORTED_ROUNDING = {
    "down",
    "up",
    "half_up",
    "half_down",
    "half_even",
    "ceiling",
    "floor",
}

@dataclass(frozen=True)
class BigDecimal:
    # value = sign * coefficient * 10**exponent
    sign: int
    coefficient: int
    exponent: int

    def __post_init__(self):
        if self.sign not in (-1, 0, 1):
            raise ValueError("sign must be -1, 0, or 1")
        if self.coefficient < 0:
            raise ValueError("coefficient must be nonnegative")
        if self.coefficient == 0:
            object.__setattr__(self, "sign", 0)
            object.__setattr__(self, "exponent", 0)
        else:
            object.__setattr__(self, "sign", 1 if self.sign > 0 else -1)
            # Remove trailing decimal zeroes from the coefficient.
            c, e = self.coefficient, self.exponent
            while c % 10 == 0:
                c //= 10
                e += 1
            object.__setattr__(self, "coefficient", c)
            object.__setattr__(self, "exponent", e)

    @classmethod
    def parse(cls, text):
        text = text.strip().lower()
        match = re.fullmatch(
            r"([+-]?)(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?",
            text
        )
        if not match:
            raise ValueError(f"Invalid decimal: {text!r}")

        sign_text, whole, fraction, exp_text = match.groups()
        fraction = fraction or ""
        whole = whole or ""

        if not whole and not fraction:
            raise ValueError("No digits supplied")

        digits = (whole + fraction).lstrip("0")
        if not digits:
            return cls(0, 0, 0)

        sign = -1 if sign_text == "-" else 1
        exponent = int(exp_text or "0") - len(fraction)
        return cls(sign, int(digits), exponent)

    def __str__(self):
        if self.sign == 0:
            return "0"

        digits = str(self.coefficient)
        point = len(digits) + self.exponent

        if -6 <= point <= 21:
            if point <= 0:
                body = "0." + "0" * (-point) + digits
            elif point >= len(digits):
                body = digits + "0" * (point - len(digits))
            else:
                body = digits[:point] + "." + digits[point:]
        else:
            body = digits[0]
            if len(digits) > 1:
                body += "." + digits[1:]
            body += f"e{self.exponent + len(digits) - 1}"

        return ("-" if self.sign < 0 else "") + body

    def _signed_coefficient(self):
        return self.sign * self.coefficient

    def __add__(self, other):
        if not isinstance(other, BigDecimal):
            other = BigDecimal.parse(str(other))

        exponent = min(self.exponent, other.exponent)
        a = self._signed_coefficient() * 10 ** (
            self.exponent - exponent
        )
        b = other._signed_coefficient() * 10 ** (
            other.exponent - exponent
        )
        total = a + b

        return BigDecimal(
            0 if total == 0 else (1 if total > 0 else -1),
            abs(total),
            exponent
        )

    def __sub__(self, other):
        if not isinstance(other, BigDecimal):
            other = BigDecimal.parse(str(other))
        return self + BigDecimal(
            -other.sign, other.coefficient, other.exponent
        )

    def __mul__(self, other):
        if not isinstance(other, BigDecimal):
            other = BigDecimal.parse(str(other))

        sign = self.sign * other.sign
        return BigDecimal(
            sign,
            self.coefficient * other.coefficient,
            self.exponent + other.exponent
        )
    
    
    def __truediv__(
        self,
        other,
        precision=DEFAULT_PRECISION,
        rounding=DEFAULT_ROUNDING,
    ):
        if not isinstance(other, BigDecimal):
            other = BigDecimal.parse(str(other))

        if other.sign == 0:
            raise ZeroDivisionError("Cannot divide by zero")

        if not isinstance(precision, int) or isinstance(precision, bool):
            raise TypeError("Precision must be an integer")

        if precision < 1:
            raise ValueError("Precision must be at least 1")

        if rounding not in SUPPORTED_ROUNDING:
            raise ValueError(f"Unsupported rounding mode: {rounding}")

        if self.sign == 0:
            return BigDecimal(0, 0, 0)

        numerator = self.coefficient
        denominator = other.coefficient
        exponent_difference = self.exponent - other.exponent

        # Find floor(log10(numerator / denominator)).
        digit_difference = len(str(numerator)) - len(str(denominator))

        if digit_difference >= 0:
            if numerator < denominator * 10**digit_difference:
                digit_difference -= 1
        elif numerator * 10**(-digit_difference) < denominator:
            digit_difference -= 1

        quotient_exponent = exponent_difference + digit_difference
        shift = precision - 1 - digit_difference

        if shift >= 0:
            scaled_numerator = numerator * 10**shift
            scaled_denominator = denominator
        else:
            scaled_numerator = numerator
            scaled_denominator = denominator * 10**(-shift)

        quotient, remainder = divmod(
            scaled_numerator, scaled_denominator
        )

        # Determine rounding using the magnitude of the remainder.
        twice_remainder = 2 * remainder
        comparison = (
            1 if twice_remainder > scaled_denominator
            else -1 if twice_remainder < scaled_denominator
            else 0
        )

        is_exact = remainder == 0
        result_sign = self.sign * other.sign
        increment = False

        if not is_exact:
            if rounding == "up":
                increment = True
            elif rounding == "down":
                increment = False
            elif rounding == "ceiling":
                increment = result_sign > 0
            elif rounding == "floor":
                increment = result_sign < 0
            elif rounding == "half_up":
                increment = comparison >= 0
            elif rounding == "half_down":
                increment = comparison > 0
            elif rounding == "half_even":
                increment = (
                    comparison > 0
                    or (comparison == 0 and quotient % 2 == 1)
                )

        if increment:
            quotient += 1

        return BigDecimal(
            result_sign,
            quotient,
            quotient_exponent - (precision - 1),
        )

    def __pow__(self, exponent, precision=DEFAULT_PRECISION):
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            raise TypeError("Exponent must be an integer.")
        if exponent < 0:
            raise ValueError("Negative exponents are not supported here.")

        result = BigDecimal.parse("1")
        base = self
        n = exponent

        while n:
            if n & 1:
                result = result * base
            n >>= 1
            if n:
                base = base * base

        return result.round_significant(precision)

    def round_significant(
        self,
        precision=None,
        rounding=None,
        *,
        context=None,
    ):
        if context is not None:
            if precision is not None or rounding is not None:
                raise ValueError(
                    "Pass either context or explicit settings, not both"
                )
            precision = context.precision
            rounding = context.rounding

        if precision is None:
            precision = DEFAULT_PRECISION

        if rounding is None:
            rounding = DEFAULT_ROUNDING

        if not isinstance(precision, int) or isinstance(precision, bool):
            raise TypeError("Precision must be an integer")

        if precision < 1:
            raise ValueError("Precision must be at least 1")

        if rounding not in SUPPORTED_ROUNDING:
            raise ValueError(f"Unsupported rounding mode: {rounding}")

        if self.sign == 0:
            return self

        digits = len(str(self.coefficient))

        # Number of coefficient digits to discard.
        discarded = digits - precision

        # Already has few enough digits.
        if discarded <= 0:
            return self

        divisor = 10 ** discarded
        quotient, remainder = divmod(self.coefficient, divisor)

        if remainder == 0:
            increment = False
        else:
            twice_remainder = 2 * remainder
            comparison = (
                1 if twice_remainder > divisor
                else -1 if twice_remainder < divisor
                else 0
            )

            increment = False

            if rounding == "up":
                increment = True
            elif rounding == "down":
                increment = False
            elif rounding == "ceiling":
                increment = self.sign > 0
            elif rounding == "floor":
                increment = self.sign < 0
            elif rounding == "half_up":
                increment = comparison >= 0
            elif rounding == "half_down":
                increment = comparison > 0
            elif rounding == "half_even":
                increment = (
                    comparison > 0
                    or (comparison == 0 and quotient % 2 == 1)
                )

        if increment:
            quotient += 1

        return BigDecimal(
            self.sign,
            quotient,
            self.exponent + discarded,
        )

    def log10(value, precision=30):
        """Approximate log10(BigDecimal) and return a BigDecimal."""
        if not isinstance(value, BigDecimal):
            value = BigDecimal.parse(str(value))

        if value.sign <= 0:
            raise ValueError("log10 requires a positive BigDecimal.")

        coefficient_text = str(value.coefficient).lstrip("0")
        if not coefficient_text:
            raise ValueError("log10(0) is undefined.")

        digits = coefficient_text[:precision]
        leading = int(digits)

        # Normalize leading digits to [1, 10).
        mantissa = leading / (10 ** (len(digits) - 1))
        coefficient_log = (
            len(coefficient_text) - 1 + math.log10(mantissa)
        )

        # Convert the approximation into BigDecimal and add the exponent.
        result = BigDecimal.parse(str(coefficient_log))
        return result + BigDecimal.parse(str(value.exponent))

    def compare(self, other):
        if self.round_significant().coefficient < other.round_significant().coefficient:
            return -1
        elif self.round_significant().coefficient == other.round_significant().coefficient:
            return 0
        else:
            return 1