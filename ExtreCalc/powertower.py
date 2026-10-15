import re

class PowerTower:
    """Stores xPTy as a power tower of x tens ending in y.

    Examples:
        1PT4 = 10^4
        2PT4 = 10^(10^4)
        3PT4 = 10^(10^(10^4))
    """

    def __init__(self, height, bottom):
        self.height = self._parse_integer(height, "height")
        self.bottom = self._parse_integer(bottom, "bottom")

        if self.height < 0:
            raise ValueError("Tower height cannot be negative.")
        if self.bottom < 0:
            raise ValueError("The bottom exponent cannot be negative.")

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

    @classmethod
    def parse(cls, text):
        """Parse a string such as '3PT4'."""
        if not isinstance(text, str):
            raise TypeError("PowerTower.parse expects a string.")

        match = re.fullmatch(
            r"\s*(\d+)\s*PT\s*(\d+)\s*",
            text,
            re.IGNORECASE,
        )

        if match is None:
            raise ValueError(f"Invalid power-tower notation: {text!r}")

        return cls(int(match.group(1)), int(match.group(2)))

    def __str__(self):
        return f"{self.height}PT{self.bottom}"

    def __repr__(self):
        return f"PowerTower({self.height}, {self.bottom})"

    def __eq__(self, other):
        if not isinstance(other, PowerTower):
            return NotImplemented

        return (
            self.height == other.height
            and self.bottom == other.bottom
        )

    @staticmethod
    def _compare_values(h1, b1, h2, b2):
        """Return -1, 0, or 1 when one tower is smaller, equal, or larger."""
    
        # Both represent ordinary integers.
        if h1 == 0 and h2 == 0:
            return (b1 > b2) - (b1 < b2)
    
        # If both are positive-height towers, compare their exponents.
        if h1 > 0 and h2 > 0:
            return PowerTower._compare_values(
                h1 - 1, b1, h2 - 1, b2
            )
    
        # Compare an ordinary integer with a positive-height tower.
        if h1 == 0:
            return -PowerTower._compare_integer_to_tower(b1, h2, b2)
    
        return PowerTower._compare_integer_to_tower(b2, h1, b1)
    
    
    @staticmethod
    def _compare_integer_to_tower(number, height, bottom):
        """Compare an ordinary non-negative integer with a tower."""
    
        if height == 0:
            return (number > bottom) - (number < bottom)
    
        # The tower is 10 raised to the value of its exponent tower.
        exponent_height = height - 1
    
        # Avoid converting enormous integers to decimal strings.
        if number == 0:
            return -1
    
        digits_lower_bound = number.bit_length() * 301 // 1000
    
        if exponent_height == 0:
            exponent = bottom
    
            if exponent >= number.bit_length():
                return -1
    
            tower_value = 10 ** exponent
            return (number > tower_value) - (number < tower_value)
    
        if bottom > digits_lower_bound:
            return -1
    
        # Compare using the number of decimal digits as a bound.
        # For very large cases, compare the exponent tower recursively.
        digits = len(str(number))
        exponent_comparison = PowerTower._compare_values(
            exponent_height, bottom, 0, digits
        )
    
        if exponent_comparison >= 0:
            return -1
    
        # The exponent is smaller than the digit count, so evaluate
        # only the bounded power needed for an exact comparison.
        exponent = PowerTower(exponent_height, bottom).to_int(
            max_digits=digits
        )
        tower_value = 10 ** exponent
        return (number > tower_value) - (number < tower_value)



    def __le__(self, other):
        result = self.__lt__(other)
        if result is NotImplemented:
            return NotImplemented
        return result or self == other

    def __gt__(self, other):
        result = self.__lt__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result and self != other

    def __ge__(self, other):
        result = self.__lt__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def is_zero(self):
        """Whether the represented value is zero."""
        return self.height == 0 and self.bottom == 0

    
    def to_int(self, max_digits=1000):
        """Evaluate a tower only when its exact integer fits the digit limit."""
        if not isinstance(max_digits, int) or isinstance(max_digits, bool):
            raise TypeError("max_digits must be an integer.")
        if max_digits < 1:
            raise ValueError("max_digits must be positive.")

        if self.height == 0:
            if len(str(self.bottom)) > max_digits:
                raise OverflowError("Result exceeds the digit limit.")
            return self.bottom

        # 1PTy = 10**y, which has y + 1 digits.
        if self.height == 1:
            if self.bottom + 1 > max_digits:
                raise OverflowError("Result exceeds the digit limit.")
            return 10 ** self.bottom

        # Higher towers grow too quickly for this simple conversion method.
        raise OverflowError(
            "Tower is too tall to evaluate safely with to_int()."
        )
