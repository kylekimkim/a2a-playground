"""
TDD: calculator 도구 단위 테스트

RED → 실패 케이스 먼저 정의
GREEN → 구현 코드로 통과
REFACTOR → 중복 제거 / 명확성 향상
"""
import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools.calculator import _eval, calculator
import ast


# ── _eval 내부 함수 단위 테스트 ────────────────────────────────────────────────

class TestEvalBasicArithmetic:
    """기본 사칙연산"""

    def _parse(self, expr: str):
        return ast.parse(expr, mode="eval").body

    def test_addition(self):
        assert _eval(self._parse("2 + 3")) == 5

    def test_subtraction(self):
        assert _eval(self._parse("10 - 4")) == 6

    def test_multiplication(self):
        assert _eval(self._parse("3 * 7")) == 21

    def test_division(self):
        assert _eval(self._parse("10 / 4")) == 2.5

    def test_floor_division(self):
        assert _eval(self._parse("10 // 3")) == 3

    def test_modulo(self):
        assert _eval(self._parse("10 % 3")) == 1

    def test_power(self):
        assert _eval(self._parse("2 ** 10")) == 1024

    def test_unary_minus(self):
        assert _eval(self._parse("-5")) == -5

    def test_unary_plus(self):
        assert _eval(self._parse("+7")) == 7

    def test_nested_expression(self):
        assert _eval(self._parse("(2 + 3) * 4")) == 20


class TestEvalMathFunctions:
    """수학 함수 및 상수"""

    def _parse(self, expr: str):
        return ast.parse(expr, mode="eval").body

    def test_sqrt(self):
        assert _eval(self._parse("sqrt(144)")) == 12.0

    def test_sin_pi_half(self):
        assert abs(_eval(self._parse("sin(pi/2)")) - 1.0) < 1e-9

    def test_cos_zero(self):
        assert abs(_eval(self._parse("cos(0)")) - 1.0) < 1e-9

    def test_log_e(self):
        assert abs(_eval(self._parse("log(e)")) - 1.0) < 1e-9

    def test_log2(self):
        assert _eval(self._parse("log2(8)")) == 3.0

    def test_log10(self):
        assert _eval(self._parse("log10(1000)")) == 3.0

    def test_exp_zero(self):
        assert _eval(self._parse("exp(0)")) == 1.0

    def test_abs_negative(self):
        assert _eval(self._parse("abs(-42)")) == 42

    def test_round(self):
        assert _eval(self._parse("round(3.14159)")) == 3

    def test_ceil(self):
        assert _eval(self._parse("ceil(2.1)")) == 3

    def test_floor(self):
        assert _eval(self._parse("floor(2.9)")) == 2

    def test_factorial(self):
        assert _eval(self._parse("factorial(5)")) == 120

    def test_pi_constant(self):
        assert abs(_eval(self._parse("pi")) - math.pi) < 1e-9

    def test_e_constant(self):
        assert abs(_eval(self._parse("e")) - math.e) < 1e-9


class TestEvalSecurityGuards:
    """보안 차단 테스트 — 허용되지 않는 표현식은 ValueError 발생"""

    def _parse(self, expr: str):
        return ast.parse(expr, mode="eval").body

    def test_disallows_string_constant(self):
        with pytest.raises(ValueError, match="숫자 상수만 허용"):
            _eval(self._parse("'hello'"))

    def test_disallows_unknown_name(self):
        with pytest.raises(ValueError, match="허용되지 않는 변수"):
            _eval(self._parse("os"))

    def test_disallows_exponent_overflow(self):
        with pytest.raises(ValueError, match="지수가 너무 큽니다"):
            _eval(self._parse("2 ** 1001"))

    def test_disallows_keyword_args(self):
        with pytest.raises(ValueError, match="키워드 인수는 지원하지 않습니다"):
            _eval(self._parse("round(3.14, ndigits=2)"))


# ── calculator @tool 래퍼 테스트 ──────────────────────────────────────────────

class TestCalculatorTool:
    """calculator LangChain 도구 (문자열 입출력)"""

    def test_simple_result_format(self):
        result = calculator.invoke({"expression": "2 + 3"})
        assert "2 + 3" in result
        assert "5" in result

    def test_caret_alias_for_power(self):
        # ^ 는 ** 로 변환되어야 함
        result = calculator.invoke({"expression": "2^10"})
        assert "1024" in result

    def test_float_without_fractional_part_returns_int_string(self):
        result = calculator.invoke({"expression": "10 / 2"})
        assert "5" in result
        assert "5.0" not in result  # 정수로 표시

    def test_division_by_zero_returns_error_message(self):
        result = calculator.invoke({"expression": "1 / 0"})
        assert "오류" in result or "error" in result.lower()

    def test_unknown_variable_returns_error_message(self):
        result = calculator.invoke({"expression": "x + 1"})
        assert "오류" in result or "계산 오류" in result

    def test_sqrt_result(self):
        result = calculator.invoke({"expression": "sqrt(256)"})
        assert "16" in result

    def test_complex_expression(self):
        result = calculator.invoke({"expression": "(3 + 4) * (10 - 3) / 7"})
        assert "7" in result

    def test_factorial(self):
        result = calculator.invoke({"expression": "factorial(6)"})
        assert "720" in result

    def test_empty_expression_returns_error(self):
        result = calculator.invoke({"expression": ""})
        assert "오류" in result or "계산 오류" in result

    def test_whitespace_expression_returns_error(self):
        result = calculator.invoke({"expression": "   "})
        assert "오류" in result or "계산 오류" in result

    def test_pi_expression(self):
        result = calculator.invoke({"expression": "pi * 2"})
        # 2π ≈ 6.283...
        assert "6.28" in result
