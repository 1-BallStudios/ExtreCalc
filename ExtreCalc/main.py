from arithmetic import *
from biginteger import BigInt
from bigdecimal import BigDecimal
from scinot import SciNot
from expantanum import ExpantaNum
import power_normalizer
import ast
import io
import tokenize
import operator
import re
import os
import sys

sys.set_int_max_str_digits(0)
super = ["⁰","¹","²","³","⁴","⁵","⁶","⁷","⁸","⁹"]
superBool = False
running = True

os.system('cls' if os.name == 'nt' else 'clear')

def parse_number(text):
    """Parse a numeric literal without converting it to float."""
    text = text.strip()

    # Scientific notation: 1.23e100
    if "e" in text.lower():
        return SciNot.parse(text)

    # Decimal notation: 1.23
    if "." in text:
        return BigDecimal.parse(text)

    # Integer notation: 123
    return BigInt(int(text))

CURRENT_EXPRESSION = ""

def normalize_operators(text):
    """Convert calculator operators to Python-compatible operators."""
    result = []

    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.OP and tok.string == "^":
            result.append((tokenize.OP, "**"))
        else:
            result.append(tok)

    return tokenize.untokenize(result)

def tokenize_input(text):
    # Convert Power Tower literals before Python tokenizes the expression.
    text = re.sub(
        r'(?<![A-Za-z0-9_.])(\d+)PT(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)',
        lambda m: f"PowerTower.parse('{m.group(1)}PT{m.group(2)}')",
        text,
        flags=re.IGNORECASE,
    )

    tokens = []

    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (
            tokenize.NUMBER,
            tokenize.OP,
            tokenize.NAME,
            tokenize.STRING,
        ):
            tokens.append(tok.string)

    return tokens

# Allowed arithmetic operations.
BINARY_OPERATORS = {
    ast.Add: add,
    ast.Sub: subtract,
    ast.Mult: multiply,
    ast.Div: divide,
    ast.FloorDiv: integer_divide,
    ast.Mod: remainder,
    ast.Pow: power,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: negate,
}

TERNARY_OPERATORS = {
    "@": {
        "name": "arrow",
        "function": arrow,
    },
}

VARIABLES = {
    "ans": "",
    "pi": "3.141592653589793",
    "e": "2.718281828459045",
}

def get_power_chain(node):
    """Extract a right-associative exponent chain from an AST node."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Pow):
        return None

    bases = []
    current = node

    while isinstance(current, ast.BinOp) and isinstance(current.op, ast.Pow):
        bases.append(current.left)
        current = current.right

    bases.append(current)
    return bases


def get_integer_literal(node):
    """Return an integer literal, or None if the node isn't one."""
    if not isinstance(node, ast.Constant):
        return None

    value = node.value
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    return None

def evaluate_node(node):
    def get_power_chain(node):
        """Extract the bases of a right-associated power chain."""
        if not (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Pow)
        ):
            return None

        bases = []
        current = node

        while isinstance(current, ast.BinOp) and isinstance(
            current.op, ast.Pow
        ):
            bases.append(current.left)
            current = current.right

        bases.append(current)
        return bases
    if isinstance(node, ast.Expression):
        return evaluate_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "\033[91mBoolean constants are not allowed.\033[0m"

        if isinstance(node.value, (int, float)):
            literal = ast.get_source_segment(CURRENT_EXPRESSION, node)
            if literal is None:
                return "\033[91mCould not read numeric literal.\033[0m"

            return parse_number(literal)
        return "\033[91mOnly numeric constants are allowed.\033[0m"
    
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.MatMult)
        and isinstance(node.left, ast.BinOp)
        and isinstance(node.left.op, ast.MatMult)
    ):
        # Recognize the left-associated AST for: a @ c @ b
        a_node = node.left.left
        c_node = node.left.right
        b_node = node.right

        a = evaluate_node(a_node)
        c = evaluate_node(c_node)
        b = evaluate_node(b_node)

        for value in (a, c, b):
            if isinstance(value, str) and "\033[91m" in value:
                return value

        try:
            return TERNARY_OPERATORS["@"]["function"](a, c, b)
        except (
            ArithmeticError,
            TypeError,
            ValueError,
            NotImplementedError,
        ) as exc:
            return f"\033[91m{exc}\033[0m"

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
    
        if op_type not in BINARY_OPERATORS:
            return f"\033[91mUnsupported operator: {op_type.__name__}\033[0m"

        if isinstance(node.op, ast.Pow):
            chain = get_power_chain(node)

            if chain is not None and len(chain) >= 3:
                integer_bases = [
                    get_integer_literal(part)
                    for part in chain
                ]

                if all(value is not None for value in integer_bases):
                    try:
                        return power_normalizer.normalize_powertower(
                            power_normalizer.normalize_power_chain(integer_bases)
                        )    
                    except (
                        ArithmeticError,
                        TypeError,
                        ValueError,
                        NotImplementedError,
                    ) as exc:
                        return f"\033[91m{exc}\033[0m"

        left = evaluate_node(node.left)
        right = evaluate_node(node.right)

        # Don't try to perform arithmetic on an existing error message.
        if isinstance(left, str) and "\033[91m" in left:
            return left
        if isinstance(right, str) and "\033[91m" in right:
            return right

        try:
            return BINARY_OPERATORS[op_type](left, right)
        except (ArithmeticError, TypeError, ValueError, NotImplementedError) as exc:
            return f"\033[91m{exc}\033[0m"

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)

        if op_type not in UNARY_OPERATORS:
            return f"\033[91mUnsupported unary operator: {op_type.__name__}\033[0m"

        operand = evaluate_node(node.operand)

        if isinstance(operand, str) and "\033[91m" in operand:
            return operand

        try:
            return UNARY_OPERATORS[op_type](operand)
        except (ArithmeticError, TypeError, ValueError, NotImplementedError) as exc:
            return f"\033[91m{exc}\033[0m"

    if isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "PowerTower"
            and node.func.attr == "parse"
            and len(node.args) == 1
            and not node.keywords
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return PowerTower.parse(node.args[0].value)

        return "\033[91mUnsupported function call.\033[0m"

    if isinstance(node, ast.Name):
        if node.id in VARIABLES:
            return VARIABLES[node.id]
        return f"\033[91mUnknown variable: {node.id}\033[0m"
    
    return f"\033[91mUnsupported expression: {type(node).__name__}\033[0m"

def normalize_ternary_operators(text):
    """Translate a{c}b into a @ c @ b for AST parsing."""
    result = []
    depth = 0

    for char in text:
        if char == "{":
            depth += 1
            result.append(" @ ")
        elif char == "}":
            if depth == 0:
                raise SyntaxError("Unmatched closing brace.")
            depth -= 1
            result.append(" @ ")
        else:
            result.append(char)

    if depth != 0:
        raise SyntaxError("Unmatched opening brace.")

    return "".join(result)

def evaluate_tokens(tokens):
    global CURRENT_EXPRESSION

    expression = "".join(tokens)
    expression = normalize_ternary_operators(expression)
    CURRENT_EXPRESSION = normalize_operators(expression)

    tree = ast.parse(CURRENT_EXPRESSION, mode="eval")
    return evaluate_node(tree)


print("Go ahead -- just TRY to make me overflow!")
print("\033[36m  ______      _             _____      _       \033[0m")
print("\033[36m |  ____|    | |           / ____|    | |      \033[0m")
print("\033[36m | |__  __  _| |_ _ __ ___| |     __ _| | ___  \033[0m")
print("\033[36m |  __| \\ \\/ / __| '__/ _ \\ |    / _` | |/ __| \033[0m")
print("\033[36m | |____ >  <| |_| | |  __/ |___| (_| | | (__  \033[0m")
print("\033[36m |______/_/\\_\\___|_|  \\___|\\_____\\__,_|_|\\___| \033[0m")
print("\033[36m                  VERSION 0.1                  \033[0m")
print("")
print("Made by Robert Kim (1-Ball) with the help of many others")
print("Type '?' for function list")
print("Type 'credits' for credits.")
print("Type 'quit' to quit ExtreCalc.")
print("")
while running:
    INPUT = input("")
    if INPUT == "?":
        print("\033[32mBelow is a list of all functions and operations:\033[0m")
        print("\033[32m +  ---------------------- addition\033[0m")
        print("\033[32m -  ------------------- subtraction\033[0m")
        print("\033[32m *  ---------------- multiplication\033[0m")
        print("\033[32m /  ---------------------- division\033[0m")
        print("\033[32m ** ---------------- exponentiation\033[0m")
        print("\033[32m // -------------- integer division\033[0m")
        print("\033[32m %  --------------------- remainder\033[0m")
        print("\033[32m sciNot ------------- format to xEy\033[0m")
        print("\033[32m hyperE ------------ format to Ex#y\033[0m")
        print("\033[32m superBool - Toggle Fancy Exponents\033[0m")
        print("")
    elif INPUT == "credits":
        print("----- CREDITS -----")
        print("Made By Robert Kim (1-Ball)")
        print("with some help from:")
        print("ChatGPT")
        print("ExpantaNum.js")
        print("NCalc Fx")
        print("Omega Calculator")
        print("HyperCalc JavaScript")
        print("PenguinMod")
        print("The Googology Wiki")
        print("mrob.com")
        print("and of course, all of you. :)")
        print("")
    elif INPUT == "quit":
        running = False
    elif INPUT == "sciNot":
        print(str(SciNot.parse(VARIABLES["ans"])))
        print("")
    elif INPUT == "hyperE":
        temp = PowerTower.parse(VARIABLES["ans"])
        print("E"+str(temp.top)+"#"+str(temp.height))
        print("")
    elif INPUT == "superBool":
        if superBool == False:
            superBool = True
        else:
            superBool = False
        print("superBool has been set to " + str(superBool))
        print("")
    else:    
        if isinstance(evaluate_tokens(tokenize_input(INPUT)), ExpantaNum):
            VARIABLES["ans"] = ExpantaNum.to_str(evaluate_tokens(tokenize_input(INPUT)),superBool)
        else:
            VARIABLES["ans"] = str(evaluate_tokens(tokenize_input(INPUT)))
        if superBool == True and VARIABLES["ans"].__contains__("e"):
            exponent = str(SciNot.parse(VARIABLES["ans"]).exponent)
            for i in range(10):
                exponent = exponent.replace(str(i),super[i])
            print(str(SciNot.parse(VARIABLES["ans"]).coefficient)+" × 10"+exponent)
        else:
            print(VARIABLES["ans"])
        print("")