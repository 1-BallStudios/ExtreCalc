class BigInt:
    def __init__(self, value=0):
        if isinstance(value, BigInt):
            self.value = value.value
        else:
            text = str(value).strip()
            if not text or text in ("+", "-"):
                raise ValueError("Invalid integer")
            if text[0] in "+-":
                digits = text[1:]
            else:
                digits = text
            if not digits.isdigit():
                raise ValueError(f"Invalid integer: {value!r}")
            self.value = int(text)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"BigInt({self.value})"

    def __add__(self, other):
        return BigInt(self.value + BigInt(other).value)

    def __sub__(self, other):
        return BigInt(self.value - BigInt(other).value)

    def __mul__(self, other):
        return BigInt(self.value * BigInt(other).value)

    def __floordiv__(self, other):
        return BigInt(self.value // BigInt(other).value)

    def __mod__(self, other):
        return BigInt(self.value % BigInt(other).value)

    def __pow__(self, exponent):
        exponent = int(str(exponent))
        if exponent < 0:
            raise ValueError("BigInt requires a nonnegative exponent")
        return BigInt(self.value ** exponent)

    def __neg__(self):
        return BigInt(-self.value)

    def __abs__(self):
        return BigInt(abs(self.value))

    def __eq__(self, other):
        return self.value == BigInt(other).value

    def __lt__(self, other):
        return self.value < BigInt(other).value

    def __le__(self, other):
        return self.value <= BigInt(other).value

    def __gt__(self, other):
        return self.value > BigInt(other).value

    def __ge__(self, other):
        return self.value >= BigInt(other).value