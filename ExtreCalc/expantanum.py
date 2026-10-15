class ExpantaNum:
    """Stores a number using a sign and layered magnitude.

    This is an initial storage structure, not a full ExpantaNum
    implementation. Arithmetic and canonical normalization come later.
    """

    def __init__(self, sign=1, layer=0, magnitude=0):
        if isinstance(sign, bool) or not isinstance(sign, int):
            raise TypeError("sign must be an integer.")

        if sign not in (-1, 0, 1):
            raise ValueError("sign must be -1, 0, or 1.")

        if isinstance(layer, bool) or not isinstance(layer, int):
            raise TypeError("layer must be an integer.")

        if layer < 0:
            raise ValueError("layer cannot be negative.")

        if not isinstance(magnitude, (int, float)):
            raise TypeError("magnitude must be numeric.")

        if isinstance(magnitude, bool):
            raise TypeError("magnitude must be numeric, not bool.")

        if layer > 0 and magnitude <= 0:
            raise ValueError(
                "A layered magnitude must be positive."
            )

        if sign == 0 or magnitude == 0:
            self.sign = 0
            self.layer = 0
            self.magnitude = 0
        else:
            self.sign = sign
            self.layer = layer
            self.magnitude = magnitude

    def __str__(self):
        if self.sign == 0:
            return "0"

        prefix = "-" if self.sign < 0 else ""

        if self.layer == 0:
            return f"{prefix}{self.magnitude}"

        return f"{prefix}ExpantaNum(layer={self.layer}, magnitude={self.magnitude})"

    def __repr__(self):
        return (
            f"ExpantaNum(sign={self.sign}, "
            f"layer={self.layer}, magnitude={self.magnitude})"
        )

    def is_zero(self):
        return self.sign == 0

    def is_negative(self):
        return self.sign < 0

    def is_positive(self):
        return self.sign > 0