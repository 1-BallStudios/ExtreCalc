import re
from bigdecimal import BigDecimal


class PowerTower:
    """Stores xPTy as a power tower of x tens ending in y.

    Examples:
        0PT4 = 4
        1PT4 = 10^4
        2PT4 = 10^(10^4)
        3PT4 = 10^(10^(10^4))
    """

    def __init__(self, height, top):
        self.height = self._parse_integer(height, "height")
        self.top = self._parse_decimal(top)

        if self.height < 0:
            raise ValueError("Tower height cannot be negative.")

        if self.top.sign < 0:
            raise ValueError("The top exponent cannot be negative.")

    @staticmethod
    def _parse_integer(value, name):
        if isinstance(value, bool):
            raise TypeError(f"{name} must be an integer, not bool.")

        if isinstance(value, int):
            return value

        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"[+]?\d+", text):
                return int(text)

        raise TypeError(f"{name} must be a non-negative integer.")

    @staticmethod
    def _parse_decimal(value):
        if isinstance(value, BigDecimal):
            return value

        if isinstance(value, bool) or isinstance(value, float):
            raise TypeError(
                "top must be a BigDecimal, integer, or decimal string."
            )

        if isinstance(value, int):
            value = str(value)

        if isinstance(value, str):
            return BigDecimal.parse(value)

        raise TypeError(
            "top must be a BigDecimal, integer, or decimal string."
        )

    @classmethod
    def parse(cls, text):
        """Parse strings such as '3PT4', '2PT3.75', or '1PT1e6'."""
        if not isinstance(text, str):
            raise TypeError("PowerTower.parse expects a string.")

        match = re.fullmatch(
            r"\s*(\d+)\s*PT\s*"
            r"([+]?(?:\d+(?:\.\d*)?|\.\d+)"
            r"(?:[eE][+-]?\d+)?)\s*",
            text,
            re.IGNORECASE,
        )

        if match is None:
            raise ValueError(f"Invalid power-tower notation: {text!r}")

        return cls(int(match.group(1)), match.group(2))
    
    def __add__(self, other):
        if not isinstance(other, PowerTower):
            other = PowerTower(0, BigDecimal.parse(str(other)))


        if self.height == 0 and other.height == 0:
            return PowerTower(
                0, self.top + other.top
            )

        if self.is_zero():
            return other
        if other.is_zero():
            return self


        raise NotImplementedError(
            "This sum cannot yet be represented exactly "
            "as a single PowerTower."
        )


    def __sub__(self, other):
        if not isinstance(other, PowerTower):
            other = PowerTower(0, BigDecimal.parse(str(other)))


        if self == other:
            return PowerTower(0, BigDecimal.parse("0"))


        if other.is_zero():
            return self


        if self.height == 0 and other.height == 0:
            return PowerTower(
                0, self.top - other.top
            )


        raise NotImplementedError(
            "This difference cannot yet be represented exactly "
            "as a single PowerTower."
        )


    def __mul__(self, other):
        if not isinstance(other, PowerTower):
            other = PowerTower(0, BigDecimal.parse(str(other)))


        if self.is_zero() or other.is_zero():
            return PowerTower(0, BigDecimal.parse("0"))


        if self.height == 0 and other.height == 0:
            return PowerTower(
                0, self.top * other.top
            )


        if self == PowerTower(0, BigDecimal.parse("1")):
            return other
        if other == PowerTower(0, BigDecimal.parse("1")):
            return self


        raise NotImplementedError(
            "This product cannot yet be represented exactly "
            "as a single PowerTower."
        )


    def __truediv__(self, other):
        if not isinstance(other, PowerTower):
            other = PowerTower(0, BigDecimal.parse(str(other)))

        if other.is_zero():
            raise ZeroDivisionError("Cannot divide by zero.")

        if self.is_zero():
            return PowerTower(0, BigDecimal.parse("0"))

        if self == other:
            return PowerTower(0, BigDecimal.parse("1"))

        # Ordinary arithmetic on height-zero towers.
        if self.height == 0 and other.height == 0:
            return PowerTower(
                0,
                self.top / other.top,
            )

        # Divide powers of ten: 10^a / 10^b = 10^(a-b).
        if self.height == 1 and other.height == 1:
            if self.top.exponent >= 0 and other.top.exponent >= 0:
                a = self.top.coefficient * 10 ** self.top.exponent
                b = other.top.coefficient * 10 ** other.top.exponent

                if a.denominator == 1 and b.denominator == 1:
                    difference = a - b
                    return PowerTower(
                        0,
                        BigDecimal.parse(f"1e{difference}"),
                    )

        raise NotImplementedError(
            "This quotient cannot yet be represented exactly "
            "as a single PowerTower."
        )
    
    def __str__(self):
        return f"{self.height}PT{self.top}"

    def __repr__(self):
        return f"PowerTower({self.height}, {str(self.top)!r})"

    def is_zero(self):
        return self.height == 0 and self.top.sign == 0

    def __eq__(self, other):
        return (self.height == other.height) and (self.top == other.top)

    def to_int(self, max_digits=1000):
        """Evaluate only when the exact integer fits the digit limit."""
        if not isinstance(max_digits, int) or isinstance(max_digits, bool):
            raise TypeError("max_digits must be an integer.")

        if max_digits < 1:
            raise ValueError("max_digits must be positive.")

        if self.height == 0:
            if self.top.exponent < 0:
                raise ValueError("A fractional top cannot be converted to int.")

            value = self.top.coefficient * 10 ** self.top.exponent

            if len(str(value)) > max_digits:
                raise OverflowError("Result exceeds the digit limit.")

            return value

        if self.top.exponent < 0:
            raise ValueError(
                "A fractional exponent generally produces a non-integer."
            )

        exponent = self.top.coefficient * 10 ** self.top.exponent

        if self.height == 1:
            if exponent + 1 > max_digits:
                raise OverflowError("Result exceeds the digit limit.")

            return 10 ** exponent

        raise OverflowError(
            "Tower is too tall to evaluate safely with to_int()."
        )
    
    