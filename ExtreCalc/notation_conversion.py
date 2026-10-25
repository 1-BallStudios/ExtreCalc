"""
notation_conversion.py — ExtreCalc notation parsing and symbolic conversion.

This is an initial, dependency-free foundation. It preserves huge values symbolically
instead of trying to evaluate numbers that cannot feasibly be expanded.

Supported input forms:
  * Knuth up-arrows: 3^^^^^6, 3 ↑↑↑ 6
  * Conway chains: 7 -> 3 -> 12
  * BAN/BEAF-style arrays: {3,3,1,2}
  * Hyper-E: E6.4#12
  * Effective-base-26 letter notation: 1'000^ABC (configurable alphabet)
  * MatthewNotebook/Huge Letter Notation: A100, AA100, B3, C2, ...
  * User-defined -illion names: exact registered names and a symbolic fallback

Important:
  * Parsing and formatting are implemented independently of numeric evaluation.
  * The BAN and Conway AST nodes remain distinct; their recursion rules are not
    assumed equivalent.
  * The custom -illion system is user-defined. Add exact names/grammar rules as
    they are confirmed rather than silently substituting conventional names.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import re
from typing import Callable, Iterable, Mapping, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Shared expression model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Integer:
    value: int


@dataclass(frozen=True)
class DecimalNumber:
    value: Decimal


@dataclass(frozen=True)
class Add:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Subtract:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Multiply:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Divide:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Power:
    base: "Expr"
    exponent: "Expr"


@dataclass(frozen=True)
class UpArrow:
    base: "Expr"
    arrows: int
    height: "Expr"


@dataclass(frozen=True)
class ConwayChain:
    entries: tuple["Expr", ...]


@dataclass(frozen=True)
class BANArray:
    entries: tuple["Expr", ...]
    notation: str = "BAN"


@dataclass(frozen=True)
class HyperE:
    level: int
    coefficient: Decimal
    height: int


@dataclass(frozen=True)
class EffectiveBase26:
    prefix: str
    exponent: int
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class HugeLetter:
    letters: str
    index: int


@dataclass(frozen=True)
class Illion:
    coefficient: Decimal
    name: str
    index: Optional[int] = None


@dataclass(frozen=True)
class Symbol:
    text: str
    notation: Optional[str] = None


Expr = Union[
    Integer, DecimalNumber, Add, Subtract, Multiply, Divide, Power, UpArrow,
    ConwayChain, BANArray, HyperE, EffectiveBase26, HugeLetter, Illion, Symbol
]


class Notation(str, Enum):
    AUTO = "auto"
    DECIMAL = "decimal"
    KNUTH = "knuth"
    CONWAY = "conway"
    BAN = "ban"
    BEAF = "beaf"
    HYPER_E = "hyper_e"
    EFFECTIVE_BASE26 = "effective_base26"
    HUGE_LETTER = "huge_letter"
    ILLION = "illion"


class NotationError(ValueError):
    """Raised when input resembles a supported notation but is malformed."""


# ---------------------------------------------------------------------------
# Lexical helpers
# ---------------------------------------------------------------------------

_NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_INT = re.compile(r"^[+-]?\d+$")
_ARROW_SPLIT = re.compile(r"\s*->\s*")
_UP_ARROW = re.compile(r"^\s*(.+?)\s*(\^+|↑+)\s*(.+?)\s*$")
_HYPER_E = re.compile(
    r"^\s*[Ee](\d+)\.(\d+)#(\d+)\s*$"
)
_HUGE_LETTER = re.compile(r"^\s*([A-Za-z]+)(\d+)\s*$")
_EFFECTIVE_B26 = re.compile(
    r"^\s*([\d'_, ]+)\s*\^\s*([A-Za-z]+)\s*$"
)
_ARRAY = re.compile(r"^\s*[\{\[]\s*(.*?)\s*[\}\]]\s*$")


def _clean_number_text(text: str) -> str:
    return text.strip().replace("_", "").replace("'", "").replace(",", "")


def _parse_number(text: str) -> Expr:
    cleaned = _clean_number_text(text)
    if not _NUMBER.fullmatch(cleaned):
        raise NotationError(f"Not a supported numeric literal: {text!r}")
    if _INT.fullmatch(cleaned):
        return Integer(int(cleaned))
    return DecimalNumber(Decimal(cleaned))


def _split_top_level(text: str, delimiter: str = ",") -> list[str]:
    """Split on delimiter while ignoring delimiters inside nested brackets."""
    result: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(text):
        if char in "{[(":
            depth += 1
        elif char in "}])":
            depth -= 1
            if depth < 0:
                raise NotationError("Mismatched closing bracket")
        elif char == delimiter and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    if depth != 0:
        raise NotationError("Mismatched brackets")
    result.append(text[start:].strip())
    return result


def effective_base26_value(letters: str, alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ") -> int:
    """
    Interpret letters as 1-based positional base-26 (A=1, ..., Z=26, AA=27).
    This is the standard Excel-like letter index; the user's effective exponent
    convention can be customized by passing a different alphabet.
    """
    if len(set(alphabet)) != len(alphabet) or len(alphabet) < 2:
        raise ValueError("alphabet must contain unique symbols")
    lookup = {char: i + 1 for i, char in enumerate(alphabet)}
    total = 0
    for char in letters.upper():
        if char not in lookup:
            raise NotationError(f"Letter {char!r} is not in the configured alphabet")
        total = total * len(alphabet) + lookup[char]
    return total


def _parse_array(text: str, notation: str) -> Expr:
    match = _ARRAY.fullmatch(text)
    if not match:
        raise NotationError("Malformed array")
    body = match.group(1)
    parts = _split_top_level(body)
    if not body:
        raise NotationError("Array cannot be empty")
    entries = tuple(parse(part, notation=Notation.AUTO) for part in parts)
    return BANArray(entries, notation=notation.upper())


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse(text: str, notation: Union[Notation, str] = Notation.AUTO) -> Expr:
    """
    Parse a notation string into the shared expression tree.

    AUTO recognizes unambiguous syntaxes first. Use an explicit notation to
    resolve ambiguous strings or to force a particular parser.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    source = text.strip()
    if not source:
        raise NotationError("Cannot parse an empty expression")

    try:
        selected = notation if isinstance(notation, Notation) else Notation(notation.lower())
    except ValueError as exc:
        raise ValueError(f"Unknown notation: {notation!r}") from exc

    if selected == Notation.DECIMAL:
        return _parse_number(source)

    if selected in (Notation.BAN, Notation.BEAF):
        return _parse_array(source, selected.value)

    if selected == Notation.KNUTH:
        return _parse_knuth(source)

    if selected == Notation.CONWAY:
        return _parse_conway(source)

    if selected == Notation.HYPER_E:
        return _parse_hyper_e(source)

    if selected == Notation.EFFECTIVE_BASE26:
        return _parse_effective_base26(source)

    if selected == Notation.HUGE_LETTER:
        return _parse_huge_letter(source)

    if selected == Notation.ILLION:
        return _parse_illion(source)

    # AUTO: prioritize syntax that has clear separators/markers.
    if "->" in source:
        return _parse_conway(source)
    if _ARRAY.fullmatch(source):
        return _parse_array(source, "BAN")
    if _HYPER_E.fullmatch(source):
        return _parse_hyper_e(source)
    if _UP_ARROW.fullmatch(source):
        return _parse_knuth(source)
    if _EFFECTIVE_B26.fullmatch(source):
        return _parse_effective_base26(source)
    if _HUGE_LETTER.fullmatch(source):
        return _parse_huge_letter(source)
    if _NUMBER.fullmatch(_clean_number_text(source)):
        return _parse_number(source)

    # The user's -illion lexicon is custom; known names are parsed as Illion,
    # and unknown word-like strings are preserved symbolically rather than
    # guessed using conventional naming rules.
    return _parse_illion(source)


def _parse_knuth(source: str) -> Expr:
    match = _UP_ARROW.fullmatch(source)
    if not match:
        raise NotationError(f"Malformed Knuth up-arrow expression: {source!r}")
    base_text, arrow_text, height_text = match.groups()
    base = parse(base_text)
    height = parse(height_text)
    arrows = len(arrow_text)
    if arrows < 1:
        raise NotationError("At least one arrow is required")
    return UpArrow(base, arrows, height)


def _parse_conway(source: str) -> Expr:
    parts = _ARROW_SPLIT.split(source)
    if len(parts) < 2 or any(not part for part in parts):
        raise NotationError(f"Malformed Conway chain: {source!r}")
    return ConwayChain(tuple(parse(part) for part in parts))


def _parse_hyper_e(source: str) -> Expr:
    match = _HYPER_E.fullmatch(source)
    if not match:
        raise NotationError(f"Malformed Hyper-E expression: {source!r}")
    level, fractional, height = match.groups()
    coefficient = Decimal(f"{level}.{fractional}")
    return HyperE(int(level), coefficient, int(height))


def _parse_effective_base26(source: str) -> Expr:
    match = _EFFECTIVE_B26.fullmatch(source)
    if not match:
        raise NotationError(f"Malformed effective-base-26 expression: {source!r}")
    prefix, letters = match.groups()
    # Preserve the user's written leading coefficient; it is not necessarily
    # an integer in every custom variant, so retain it as text in Symbol.
    coefficient_text = _clean_number_text(prefix)
    if not coefficient_text:
        raise NotationError("Missing coefficient before ^")
    coefficient = int(coefficient_text)
    return EffectiveBase26(str(coefficient), effective_base26_value(letters))


def _parse_huge_letter(source: str) -> Expr:
    match = _HUGE_LETTER.fullmatch(source)
    if not match:
        raise NotationError(f"Malformed Huge Letter expression: {source!r}")
    letters, index = match.groups()
    return HugeLetter(letters.upper(), int(index))


# This lexicon is deliberately explicit and expandable. The custom rules supplied
# by the user include these common metric-era names; unconfirmed spellings remain
# symbolic rather than being assigned a potentially wrong exponent.
_ILLION_EXPONENTS: dict[str, int] = {
    "thousand": 3,
    "million": 6,
    "billion": 9,
    "trillion": 12,
    "quadrillion": 15,
    "quintillion": 18,
    "sextillion": 21,
    "septillion": 24,
    "octillion": 27,
    "nonillion": 30,
    "decillion": 33,
    "millillion": 3003,
    "millinillion": 3003,
}


def register_illion(name: str, exponent: int) -> None:
    """Register a confirmed custom -illion name as coefficient * 10**exponent."""
    normalized = name.strip().lower()
    if not normalized or not isinstance(exponent, int):
        raise ValueError("A nonempty name and integer exponent are required")
    _ILLION_EXPONENTS[normalized] = exponent


def _parse_illion(source: str) -> Expr:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s+(.+?)\s*", source)
    if match:
        coefficient_text, name = match.groups()
        normalized = name.lower()
        exponent = _ILLION_EXPONENTS.get(normalized)
        return Illion(Decimal(coefficient_text), normalized, exponent)
    normalized = source.lower()
    if normalized in _ILLION_EXPONENTS:
        return Illion(Decimal(1), normalized, _ILLION_EXPONENTS[normalized])
    # Keep the expression intact: do not silently apply standard English rules
    # to the user's custom component system.
    return Symbol(source, "illion")


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_expr(expr: Expr, notation: Union[Notation, str] = Notation.AUTO) -> str:
    """Format an expression in its native or requested notation."""
    selected = notation if isinstance(notation, Notation) else Notation(notation.lower())
    if selected == Notation.AUTO:
        return _format_native(expr)

    if selected == Notation.DECIMAL:
        value = evaluate(expr)
        if isinstance(value, (Integer, DecimalNumber)):
            return _format_native(value)
        raise NotationError("Expression cannot be represented as an ordinary decimal")

    if selected == Notation.KNUTH:
        return _format_knuth(expr)
    if selected == Notation.CONWAY:
        return _format_conway(expr)
    if selected in (Notation.BAN, Notation.BEAF):
        if isinstance(expr, BANArray):
            return _format_array(expr, selected.value)
        raise NotationError("Only array expressions can be formatted as BAN/BEAF")
    if selected == Notation.HYPER_E:
        if isinstance(expr, HyperE):
            return f"E{expr.level}.{str(expr.coefficient).split('.')[-1]}#{expr.height}"
        raise NotationError("Expression is not a Hyper-E value")
    if selected == Notation.EFFECTIVE_BASE26:
        if isinstance(expr, EffectiveBase26):
            return f"{expr.prefix}^{expr.exponent}"
        raise NotationError("Expression is not effective-base-26 notation")
    if selected == Notation.HUGE_LETTER:
        if isinstance(expr, HugeLetter):
            return f"{expr.letters}{expr.index}"
        raise NotationError("Expression is not Huge Letter notation")
    if selected == Notation.ILLION:
        if isinstance(expr, Illion):
            coeff = _format_decimal(expr.coefficient)
            return f"{coeff} {expr.name}"
        if isinstance(expr, Symbol) and expr.notation == "illion":
            return expr.text
        raise NotationError("Expression is not an -illion expression")
    raise NotationError(f"Cannot format {type(expr).__name__} as {selected.value}")


def _format_native(expr: Expr) -> str:
    if isinstance(expr, Integer):
        return str(expr.value)
    if isinstance(expr, DecimalNumber):
        return _format_decimal(expr.value)
    if isinstance(expr, Add):
        return f"({_format_native(expr.left)} + {_format_native(expr.right)})"
    if isinstance(expr, Subtract):
        return f"({_format_native(expr.left)} - {_format_native(expr.right)})"
    if isinstance(expr, Multiply):
        return f"({_format_native(expr.left)} * {_format_native(expr.right)})"
    if isinstance(expr, Divide):
        return f"({_format_native(expr.left)} / {_format_native(expr.right)})"
    if isinstance(expr, Power):
        return f"({_format_native(expr.base)} ** {_format_native(expr.exponent)})"
    if isinstance(expr, UpArrow):
        return f"{_format_native(expr.base)} {'^' * expr.arrows} {_format_native(expr.height)}"
    if isinstance(expr, ConwayChain):
        return " -> ".join(_format_native(item) for item in expr.entries)
    if isinstance(expr, BANArray):
        left, right = ("[", "]") if expr.notation == "BEAF" else ("{", "}")
        return left + ",".join(_format_native(item) for item in expr.entries) + right
    if isinstance(expr, HyperE):
        fractional = str(expr.coefficient).split(".")
        fraction = fractional[1] if len(fractional) > 1 else "0"
        return f"E{expr.level}.{fraction}#{expr.height}"
    if isinstance(expr, EffectiveBase26):
        return f"{expr.prefix}^{expr.exponent}"
    if isinstance(expr, HugeLetter):
        return f"{expr.letters}{expr.index}"
    if isinstance(expr, Illion):
        coeff = _format_decimal(expr.coefficient)
        return f"{coeff} {expr.name}"
    if isinstance(expr, Symbol):
        return expr.text
    raise TypeError(f"Unknown expression node: {type(expr).__name__}")


def _format_decimal(value: Decimal) -> str:
    return format(value, "f") if value == value.to_integral_value() else str(value)


def _format_knuth(expr: Expr) -> str:
    if isinstance(expr, UpArrow):
        return f"{_format_native(expr.base)} {'^' * expr.arrows} {_format_native(expr.height)}"
    if isinstance(expr, Power):
        return f"{_format_native(expr.base)} ^ {_format_native(expr.exponent)}"
    if isinstance(expr, Integer):
        return str(expr.value)
    raise NotationError("No general Knuth conversion is defined for this expression")


def _format_conway(expr: Expr) -> str:
    if isinstance(expr, ConwayChain):
        return " -> ".join(_format_native(item) for item in expr.entries)
    if isinstance(expr, Integer):
        return str(expr.value)
    if isinstance(expr, Power):
        return f"{_format_native(expr.base)} -> {_format_native(expr.exponent)}"
    raise NotationError("No general Conway conversion is defined for this expression")


def _format_array(expr: BANArray, notation: str) -> str:
    left, right = ("[", "]") if notation.lower() == "beaf" else ("{", "}")
    return left + ",".join(_format_native(item) for item in expr.entries) + right


# ---------------------------------------------------------------------------
# Safe, deliberately limited evaluation
# ---------------------------------------------------------------------------

def evaluate(expr: Expr, *, max_integer_bits: int = 1_000_000) -> Expr:
    """
    Evaluate safe, small expressions. Return the original symbolic node when
    exact evaluation would exceed the configured bit limit or is unsupported.
    This is not a full evaluator for Conway/BAN/BEAF/Hyper-E.
    """
    if isinstance(expr, (Integer, DecimalNumber, Symbol, UpArrow, ConwayChain,
                         BANArray, HyperE, EffectiveBase26, HugeLetter, Illion)):
        return expr
    left = evaluate(expr.left, max_integer_bits=max_integer_bits)
    right = evaluate(expr.right, max_integer_bits=max_integer_bits)
    if not isinstance(left, (Integer, DecimalNumber)) or not isinstance(right, (Integer, DecimalNumber)):
        return expr

    a = Decimal(left.value) if isinstance(left, Integer) else left.value
    b = Decimal(right.value) if isinstance(right, Integer) else right.value

    try:
        if isinstance(expr, Add):
            result = a + b
        elif isinstance(expr, Subtract):
            result = a - b
        elif isinstance(expr, Multiply):
            result = a * b
        elif isinstance(expr, Divide):
            if b == 0:
                raise ZeroDivisionError("division by zero")
            result = a / b
        elif isinstance(expr, Power):
            if isinstance(left, Integer) and isinstance(right, Integer) and right.value >= 0:
                estimate_bits = max(1, abs(left.value).bit_length()) * right.value
                if estimate_bits > max_integer_bits:
                    return expr
                result_int = pow(left.value, right.value)
                return Integer(result_int)
            # Decimal exponentiation is intentionally not guessed.
            return expr
        else:
            return expr
    except (ArithmeticError, ValueError):
        return expr

    if isinstance(result, Decimal) and result == result.to_integral_value():
        return Integer(int(result))
    return DecimalNumber(result)


# ---------------------------------------------------------------------------
# Conversion API
# ---------------------------------------------------------------------------

def convert_from(text: str, notation: Union[Notation, str] = Notation.AUTO) -> Expr:
    """Parse input notation to the shared symbolic representation."""
    return parse(text, notation)


def convert_to(value: Union[Expr, str], notation: Union[Notation, str]) -> str:
    """Format a parsed expression in a requested notation where supported."""
    expr = parse(value) if isinstance(value, str) else value
    return format_expr(expr, notation)


def convert(text: str, source: Union[Notation, str], target: Union[Notation, str]) -> str:
    """Convert notation through the shared expression tree."""
    return convert_to(convert_from(text, source), target)


# CamelCase aliases for compatibility with the names discussed in the project.
convertFrom = convert_from
convertTo = convert_to


__all__ = [
    "Notation", "NotationError", "Expr", "Integer", "DecimalNumber", "Add",
    "Subtract", "Multiply", "Divide", "Power", "UpArrow", "ConwayChain",
    "BANArray", "HyperE", "EffectiveBase26", "HugeLetter", "Illion", "Symbol",
    "parse", "format_expr", "evaluate", "convert", "convert_from", "convert_to",
    "convertFrom", "convertTo", "register_illion", "effective_base26_value",
]