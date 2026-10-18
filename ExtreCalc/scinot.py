import re
from decimal import Decimal, localcontext
import math

class SciNot:
    """Scientific notation: coefficient * 10**exponent."""

    def __init__(self, coefficient, exponent=0):
        if isinstance(coefficient, bool) or isinstance(exponent, bool):
            raise TypeError("Boolean values are not valid numbers.")

        if not isinstance(exponent, int):
            raise TypeError("Exponent must be an integer.")

        if isinstance(coefficient, float):
            raise TypeError("Pass strings or Decimal values, not floats.")

        try:
            coefficient = Decimal(str(coefficient))
        except Exception as exc:
            raise ValueError("Invalid coefficient.") from exc

        if not coefficient.is_finite():
            raise ValueError("Coefficient must be finite.")

        self.coefficient = coefficient
        self.exponent = exponent
        self._normalize()

    @classmethod
    def parse(cls, text):
        """Parse forms such as '2.5e8', '2.5E8', or '2.5 * 10^8'."""
        if not isinstance(text, str):
            raise TypeError("SciNot.parse expects a string.")

        text = text.strip()

        match = re.fullmatch(
            r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
            r"(?:[eE]\s*([+-]?\d+)|"
            r"\*\s*10\s*\^\s*([+-]?\d+))",
            text,
        )

        if match:
            exponent = match.group(2) or match.group(3)
            return cls(match.group(1), int(exponent))

        # Also accept ordinary numbers, such as "123.45".
        try:
            return cls(text, 0)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid scientific notation: {text!r}")

    def _normalize(self):
        if self.coefficient.is_zero():
            self.coefficient = Decimal(0)
            self.exponent = 0
            return

        shift = self.coefficient.adjusted()
        self.coefficient = self.coefficient.scaleb(-shift)
        self.exponent += shift


    def __str__(self):
        if self.coefficient.is_zero():
            return "0"

        coefficient = format(self.coefficient.normalize(), "f")
        return f"{coefficient}e{self.exponent}"

    def __repr__(self):
        return f"SciNot('{self.coefficient}', {self.exponent})"

    def _coerce(self, other):
        if isinstance(other, SciNot):
            return other
        return SciNot(other)

    def __add__(self, other):
        other = self._coerce(other)

        if self.coefficient.is_zero():
            return other
        if other.coefficient.is_zero():
            return self

        exponent = max(self.exponent, other.exponent)
        a_shift = self.exponent - exponent
        b_shift = other.exponent - exponent

        # Align exponents exactly; very large gaps can be expensive.
        a = self.coefficient.scaleb(a_shift)
        b = other.coefficient.scaleb(b_shift)
        return SciNot(a + b, exponent)

    def __sub__(self, other):
        other = self._coerce(other)
        return self + SciNot(-other.coefficient, other.exponent)

    def __mul__(self, other):
        other = self._coerce(other)
        return SciNot(
            self.coefficient * other.coefficient,
            self.exponent + other.exponent,
        )

    def __truediv__(self, other):
        other = self._coerce(other)

        if other.coefficient.is_zero():
            raise ZeroDivisionError("Cannot divide by zero.")

        with localcontext() as context:
            context.prec = 30
            coefficient = self.coefficient / other.coefficient

        return SciNot(
            coefficient,
            self.exponent - other.exponent,
        )

    def __neg__(self):
        return SciNot(-self.coefficient, self.exponent)

    def __abs__(self):
        return SciNot(abs(self.coefficient), self.exponent)

    def __eq__(self, other):
        try:
            other = self._coerce(other)
        except (ValueError, TypeError):
            return NotImplemented

        return (
            self.coefficient == other.coefficient
            and self.exponent == other.exponent
        )
    
    def log(self):
        return math.log10(self.coefficient) + self.exponent