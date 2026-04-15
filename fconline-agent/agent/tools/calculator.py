import ast
import math
import operator
from langchain.tools import tool

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, complex)):
            raise ValueError("숫자 상수만 허용됩니다.")
        return node.value
    elif isinstance(node, ast.Name):
        if node.id not in _SAFE_NAMES:
            raise ValueError(f"허용되지 않는 변수: '{node.id}'")
        return _SAFE_NAMES[node.id]
    elif isinstance(node, ast.BinOp):
        op = type(node.op)
        if op not in _BINARY_OPS:
            raise ValueError(f"허용되지 않는 이진 연산자: {op.__name__}")
        left = _eval(node.left)
        right = _eval(node.right)
        if op is ast.Pow and abs(right) > 1000:
            raise ValueError("지수가 너무 큽니다 (최대 1000).")
        return _BINARY_OPS[op](left, right)
    elif isinstance(node, ast.UnaryOp):
        op = type(node.op)
        if op not in _UNARY_OPS:
            raise ValueError(f"허용되지 않는 단항 연산자: {op.__name__}")
        return _UNARY_OPS[op](_eval(node.operand))
    elif isinstance(node, ast.Call):
        func = _eval(node.func)
        if not callable(func):
            raise ValueError("호출할 수 없는 함수입니다.")
        args = [_eval(a) for a in node.args]
        if node.keywords:
            raise ValueError("키워드 인수는 지원하지 않습니다.")
        return func(*args)
    else:
        raise ValueError(f"허용되지 않는 표현식 유형: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """수학 수식을 안전하게 계산합니다.
    지원: 사칙연산, 제곱(^/**), 나머지(%), 수학 함수(sqrt, sin, cos, tan, log, exp 등)
    상수: pi, e
    예시: '2 + 3 * 4', 'sqrt(144)', 'sin(pi/2)', '2**10', 'factorial(10)'
    """
    try:
        expr = expression.strip().replace("^", "**")
        tree = ast.parse(expr, mode="eval")
        result = _eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            formatted = str(int(result))
        else:
            formatted = f"{result:.10g}"

        print("## calculator 툴 결과: ")
        print(f"{expression} = {formatted}")
        return f"{expression} = {formatted}"
    except ZeroDivisionError:
        return "오류: 0으로 나눌 수 없습니다."
    except Exception as e:
        return f"계산 오류: {e}"
