
import math
from copy import deepcopy


MAX_SAFE_INTEGER = 9007199254740991
MAX_E = math.log10(MAX_SAFE_INTEGER)


class ExpantaNum:
    """
    ExpantaNum-style huge-number representation.

    sign:  1 or -1
    array: [[operator_index, repetition_count], ...]
    layer: number of applications of J(x) = 10{x}10

    For a single pair [0, value] with layer == 0, value
    represents an ordinary nonnegative magnitude.
    """

    def __init__(self, value=0, *, sign=None, array=None, layer=0):
        if array is not None:
            self.sign = 1 if sign is None else sign
            self.array = deepcopy(array)
            self.layer = layer
        elif isinstance(value, ExpantaNum):
            self.sign = value.sign
            self.array = deepcopy(value.array)
            self.layer = value.layer
        else:
            self.sign, self.array, self.layer = self._from_number(value)

        self.normalize()

    def iterated_log10(value, count):
        """Apply log10 repeatedly, preserving huge-number structure."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer.")
        if count < 0:
            for _ in range(-count):
                result = 10^result
    
        result = value.copy()
    
        for _ in range(count):
            result = result.log10()

        return result
    
    def tetrate(self, height):
        """
        Integer-height tetration.
    
        Uses the convention:
            a^^0 = 1
            a^^(h+1) = a ** (a^^h)
    
        Requires representation-aware pow() and comparison methods.
        """
        if isinstance(height, bool) or not isinstance(height, int):
            raise TypeError("height must be an integer")
    
        if height < 0:
            raise ValueError(
                "Negative tetration heights need a separate convention."
            )
    
        if height == 0:
            return ExpantaNum(1)
    
        if height == 1:
            return self.copy()
    
        # Base cases only. Do not use this loop for enormous towers.
        result = self.copy()
        for _ in range(height - 1):
            result = self.pow(result)
    
        return result

    @staticmethod
    def _from_number(value):
        if isinstance(value, bool):
            raise TypeError("Boolean values are not valid numbers.")

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid ExpantaNum value: {value!r}") from exc

        if math.isnan(number):
            return 1, [[0, math.nan]], 0

        if math.isinf(number):
            return (-1 if number < 0 else 1), [[0, math.inf]], 0

        sign = -1 if number < 0 else 1
        return sign, [[0, abs(number)]], 0

    @classmethod
    def from_array(cls, array, sign=1, layer=0):
        return cls(sign=sign, array=array, layer=layer)

    def _compress_operator_runs(components):
        """
        Compress consecutive identical hyperoperators.

        components: ordered sequence of (operator_index, repetition_count)
        Returns: canonical list of [operator_index, repetition_count].
        """
        result = []

        for operator_index, count in components:
            if count <= 0:
                continue

            if result and result[-1][0] == operator_index:
                result[-1][1] += count
            else:
                result.append([operator_index, count])

        return result
    
    def normalize(self):
        """Normalize the sign, operator array, and J-layer."""
        if self.sign not in (-1, 1):
            self.sign = -1 if self.sign < 0 else 1

        if isinstance(self.layer, bool) or not isinstance(self.layer, int):
            raise TypeError("layer must be a nonnegative integer.")
        if self.layer < 0:
            raise ValueError("layer must be nonnegative.")

        if not isinstance(self.array, list) or not self.array:
            self.array = [[0, 0]]

        cleaned = []
        for pair in self.array:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError("Each array entry must be a pair.")

            index, count = pair
            if isinstance(index, bool) or not isinstance(index, int):
                raise TypeError("Operator indices must be integers.")
            if index < 0:
                raise ValueError("Operator indices must be nonnegative.")

            if isinstance(count, bool) or not isinstance(count, (int, float)):
                raise TypeError("Operator counts must be numeric.")

            count = float(count)

            if math.isnan(count):
                self.array = [[0, math.nan]]
                self.layer = 0
                return self

            if math.isinf(count):
                self.array = [[0, math.inf]]
                self.layer = 0
                return self

            if index != 0 and count == 0:
                continue

            if index != 0:
                count = math.floor(count)

            cleaned.append([index, count])

        self.array = cleaned or [[0, 0]]

        changed = True
        while changed:
            changed = False
            self.array.sort(key=lambda pair: pair[0])

            # Merge equal operator indices.
            merged = []
            for index, count in self.array:
                if merged and merged[-1][0] == index:
                    merged[-1][1] += count
                    changed = True
                else:
                    merged.append([index, count])
            self.array = merged

            if not self.array:
                self.array = [[0, 0]]

            # Convert operator indices beyond the safe integer range
            # into another J-layer.
            if self.array[-1][0] > MAX_SAFE_INTEGER:
                self.layer += 1
                self.array = [[0, float(self.array[-1][0])]]
                changed = True
                continue

            # A single [0, x] inside a J-layer can be expanded one
            # layer downward using the library's J representation.
            if self.layer and len(self.array) == 1 and self.array[0][0] == 0:
                value = self.array[0][1]
                self.layer -= 1
                if value == 0:
                    self.array = [[0, 10]]
                else:
                    self.array = [[0, 10], [round(value), 1]]
                changed = True
                continue

            # The first operator must be index zero.
            if self.array[0][0] != 0:
                self.array.insert(0, [0, 10])
                changed = True

            # Promote an oversized ordinary magnitude to operator 1.
            if self.array[0][1] > MAX_SAFE_INTEGER:
                if len(self.array) >= 2 and self.array[1][0] == 1:
                    self.array[1][1] += 1
                else:
                    self.array.insert(1, [1, 1])

                self.array[0][1] = math.log10(self.array[0][1])
                changed = True
                continue

            # Expand ordinary powers of ten into the lower operator.
            while (
                len(self.array) >= 2
                and self.array[0][0] == 0
                and self.array[0][1] < MAX_E
                and self.array[1][0] == 1
                and self.array[1][1]
            ):
                self.array[0][1] = 10 ** self.array[0][1]
                if self.array[1][1] > 1:
                    self.array[1][1] -= 1
                else:
                    self.array.pop(1)
                changed = True

            # Canonicalize the special 10^1 boundary.
            while (
                len(self.array) >= 2
                and self.array[0][0] == 0
                and self.array[0][1] == 1
                and self.array[1][1]
            ):
                if self.array[1][1] > 1:
                    self.array[1][1] -= 1
                else:
                    self.array.pop(1)
                self.array[0][1] = 10
                changed = True

            # If the first nonzero operator is not 1, carry the
            # fractional part of the magnitude into the representation.
            if (
                len(self.array) >= 2
                and self.array[0][0] == 0
                and self.array[1][0] != 1
            ):
                fractional = self.array[0][1] - math.floor(self.array[0][1])
                whole = math.floor(self.array[0][1])
                index = self.array[1][0]

                if whole:
                    self.array.insert(1, [index - 1, whole])

                self.array[0][1] = 10 ** fractional

                carry_index = 2 if whole else 1
                if self.array[carry_index][1] > 1:
                    self.array[carry_index][1] -= 1
                else:
                    self.array.pop(carry_index)

                changed = True
                continue

            # Carry counts that exceed the safe integer range into
            # the next operator index.
            for i in range(len(self.array)):
                if self.array[i][1] > MAX_SAFE_INTEGER:
                    index, count = self.array[i]

                    if (
                        i != len(self.array) - 1
                        and self.array[i + 1][0] == index + 1
                    ):
                        self.array[i + 1][1] += 1
                    else:
                        self.array.insert(i + 1, [index + 1, 1])

                    self.array[:i + 1] = [[0, count + 1]]
                    changed = True
                    break

        if not self.array:
            self.array = [[0, 0]]

        if self.is_zero():
            self.sign = 1

        return self

    # Keep the old name as a compatibility alias.
    def standardize(self):
        return self.normalize()

    def copy(self):
        return ExpantaNum(
            sign=self.sign,
            array=self.array,
            layer=self.layer,
        )

    def is_nan(self):
        return len(self.array) == 1 and math.isnan(self.array[0][1])

    def is_infinite(self):
        return len(self.array) == 1 and math.isinf(self.array[0][1])

    def is_zero(self):
        return (
            self.layer == 0
            and len(self.array) == 1
            and self.array[0][0] == 0
            and self.array[0][1] == 0
        )

    def to_float(self):
        """Convert to a Python float when the value is representable."""
        if self.is_nan():
            return math.nan

        if self.is_infinite():
            return math.copysign(math.inf, self.sign)

        if self.layer != 0 or len(self.array) != 1:
            raise OverflowError(
                "This ExpantaNum cannot be converted directly to a float."
            )

        operator_index, magnitude = self.array[0]

        if operator_index != 0:
            raise OverflowError(
                "This ExpantaNum is outside the ordinary-number range."
            )

        return self.sign * magnitude

    def cmp(self, other):
        """Compare two values. Return -1, 0, or 1."""
        other = other if isinstance(other, ExpantaNum) else ExpantaNum(other)

        if self.is_nan() or other.is_nan():
            raise ValueError("NaN is unordered.")

        a = self.to_float()
        b = other.to_float()

        return (a > b) - (a < b)

    def eq(self, other):
        try:
            return self.cmp(other) == 0
        except (ValueError, OverflowError):
            return False

    def lt(self, other):
        return self.cmp(other) < 0

    def lte(self, other):
        return self.cmp(other) <= 0

    def gt(self, other):
        return self.cmp(other) > 0

    def gte(self, other):
        return self.cmp(other) >= 0

    def __eq__(self, other):
        return self.eq(other)

    def __lt__(self, other):
        return self.lt(other)

    def __le__(self, other):
        return self.lte(other)

    def __gt__(self, other):
        return self.gt(other)

    def __ge__(self, other):
        return self.gte(other)
    
    def pow(self, exponent):
        """Exponentiation for ordinary representable values."""
        exponent = (
            exponent
            if isinstance(exponent, ExpantaNum)
            else ExpantaNum(exponent)
        )

        base_value = self.to_float()
        exp_value = exponent.to_float()

        if math.isnan(base_value) or math.isnan(exp_value):
            return ExpantaNum(math.nan)

        if exp_value == 0:
            return ExpantaNum(1)

        if base_value == 0:
            if exp_value < 0:
                return ExpantaNum(math.inf)
            return ExpantaNum(0)

        if base_value < 0:
            if not exp_value.is_integer():
                return ExpantaNum(math.nan)
            result_sign = -1 if int(exp_value) % 2 else 1
            magnitude = abs(base_value) ** exp_value
            return ExpantaNum(result_sign * magnitude)

        try:
            result = base_value ** exp_value
        except (OverflowError, ValueError):
            result = math.inf

        return ExpantaNum(result)

    def __pow__(self, exponent):
        return self.pow(exponent)

    @staticmethod
    def hyper(base, rank, payload):
        """
        Basic finite hyperoperations for small ordinary operands.

        This initial implementation is intentionally bounded.
        It does not yet support huge array operands.
        """
        base = base if isinstance(base, ExpantaNum) else ExpantaNum(base)
        payload = (
            payload
            if isinstance(payload, ExpantaNum)
            else ExpantaNum(payload)
        )

        if isinstance(rank, bool) or not isinstance(rank, int):
            raise TypeError("rank must be an integer.")
        if rank < 0:
            raise ValueError("rank must be nonnegative.")

        b = base.to_float()
        p = payload.to_float()

        if not p.is_integer() or p < 0 or p > 100:
            raise ValueError(
                "This initial hyper() implementation requires "
                "an integer payload from 0 through 100."
            )

        n = int(p)

        if rank == 0:
            return ExpantaNum(n + 1)

        if rank == 1:
            return ExpantaNum(b + n)

        if rank == 2:
            return ExpantaNum(b * n)

        if rank == 3:
            return base.pow(n)

        if rank >= 4:
            if n == 0:
                return ExpantaNum(1)

            result = b

            for _ in range(n - 1):
                if rank == 4:
                    result = b ** result
                else:
                    result = ExpantaNum.hyper(
                        b, rank - 1, result
                    ).to_float()

                if not math.isfinite(result):
                    return ExpantaNum(math.inf)

            return ExpantaNum(result)

        raise ValueError("Unsupported hyperoperation rank.")

    @staticmethod
    def tetr(base, height):
        return ExpantaNum.hyper(base, 4, height)

    @staticmethod
    def pent(base, height):
        return ExpantaNum.hyper(base, 5, height)

    @staticmethod
    def arrow(base, rank, payload):
        return ExpantaNum.hyper(base, rank + 2, payload)

    def __repr__(self):
        return (
            f"ExpantaNum(sign={self.sign}, "
            f"array={self.array!r}, layer={self.layer})"
        )

    def __str__(self):
        if self.is_nan():
            return "NaN"

        if self.is_infinite():
            return "-Infinity" if self.sign < 0 else "Infinity"

        if self.is_zero():
            return "0"

        if self.layer == 0 and len(self.array) == 1:
            operator_index, value = self.array[0]
            if operator_index == 0:
                return str(self.sign * value)

        return (
            f"ExpantaNum(sign={self.sign}, "
            f"array={self.array!r}, layer={self.layer})"
        )
