from dataclasses import dataclass

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


@dataclass
class ArithmeticContext:
    precision: int = DEFAULT_PRECISION
    rounding: str = DEFAULT_ROUNDING

    def __post_init__(self):
        self.validate()

    def validate(self):
        if (
            not isinstance(self.precision, int)
            or isinstance(self.precision, bool)
            or self.precision < 1
        ):
            raise ValueError("Precision must be a positive integer")

        if self.rounding not in SUPPORTED_ROUNDING:
            raise ValueError(
                f"Unsupported rounding mode: {self.rounding}"
            )

    def set_precision(self, precision):
        old_precision = self.precision
        self.precision = precision

        try:
            self.validate()
        except Exception:
            self.precision = old_precision
            raise

    def set_rounding(self, rounding):
        old_rounding = self.rounding
        self.rounding = rounding

        try:
            self.validate()
        except Exception:
            self.rounding = old_rounding
            raise


DEFAULT_CONTEXT = ArithmeticContext()