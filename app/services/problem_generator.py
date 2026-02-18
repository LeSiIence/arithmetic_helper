from __future__ import annotations

"""Question generation service.

This module is pure business logic and can be unit-tested without PyQt.
"""

import ast
import random
from fractions import Fraction

from app.domain.models import PracticeConfig, PracticeQuestion


class ExpressionEvaluator:
    """Safely evaluate arithmetic expressions using Python AST."""

    def evaluate(self, expression: str) -> Fraction:
        node = ast.parse(expression, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node: ast.AST) -> Fraction:
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                return left / right
            raise ValueError("unsupported operator")

        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return Fraction(node.value, 1)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = self._eval_node(node.operand)
            return -value

        raise ValueError("unsupported expression")


class ProblemGenerator:
    """Generate arithmetic questions based on `PracticeConfig`."""

    def __init__(self) -> None:
        self._evaluator = ExpressionEvaluator()

    def generate_questions(self, config: PracticeConfig) -> list[PracticeQuestion]:
        """Generate a full question set for one session."""
        questions: list[PracticeQuestion] = []
        for _ in range(config.question_count):
            operation = random.choice(config.operations)
            questions.append(self._generate_by_operation(operation, config))
        return questions

    def _generate_by_operation(self, operation: str, config: PracticeConfig) -> PracticeQuestion:
        if operation == "add":
            a = random.randint(config.number_min, config.number_max)
            b = random.randint(config.number_min, config.number_max)
            expression = f"{a} + {b}"
            return PracticeQuestion(expression=expression, correct_answer=a + b)

        if operation == "sub":
            a = random.randint(config.number_min, config.number_max)
            b = random.randint(config.number_min, config.number_max)
            if a < b:
                a, b = b, a
            expression = f"{a} - {b}"
            return PracticeQuestion(expression=expression, correct_answer=a - b)

        if operation == "mul":
            a = random.randint(config.number_min, config.number_max)
            b = random.randint(config.number_min, config.number_max)
            expression = f"{a} * {b}"
            return PracticeQuestion(expression=expression, correct_answer=a * b)

        if operation == "div":
            return self._generate_division(config.number_min, config.number_max)

        if operation == "mixed":
            return self._generate_mixed(config)

        raise ValueError(f"unsupported operation: {operation}")

    def _generate_division(self, num_min: int, num_max: int) -> PracticeQuestion:
        """Generate integer division questions with non-zero divisors."""
        for _ in range(200):
            b = random.randint(max(1, num_min), max(1, num_max))
            max_q = max(1, num_max // b)
            q = random.randint(max(1, num_min), max_q) if max_q >= max(1, num_min) else 1
            a = b * q
            if num_min <= a <= num_max:
                expression = f"{a} / {b}"
                return PracticeQuestion(expression=expression, correct_answer=q)

        # Fallback to a simple guaranteed valid question.
        expression = "10 / 2"
        return PracticeQuestion(expression=expression, correct_answer=5)

    def _generate_mixed(self, config: PracticeConfig) -> PracticeQuestion:
        """Generate mixed expressions with optional parentheses.

        Constraints:
        - result must be an integer
        - result must be non-negative
        - expression must be valid (no division by zero)
        """
        op_count = max(2, config.mixed_operator_count)
        for _ in range(500):
            expression = self._build_mixed_expression(
                num_min=config.number_min,
                num_max=config.number_max,
                operator_count=op_count,
                with_parentheses=config.enable_parentheses,
                max_pairs=config.max_parentheses_pairs,
            )
            try:
                result = self._evaluator.evaluate(expression)
            except (ZeroDivisionError, ValueError):
                continue

            if result.denominator != 1:
                continue
            value = int(result)
            if value < 0:
                continue
            return PracticeQuestion(expression=expression, correct_answer=value)

        return PracticeQuestion(expression="(8 + 4) * 2", correct_answer=24)

    def _build_mixed_expression(
        self,
        num_min: int,
        num_max: int,
        operator_count: int,
        with_parentheses: bool,
        max_pairs: int,
    ) -> str:
        """Build expression string from random numbers/operators.

        Parentheses are inserted by wrapping non-overlapping number spans.
        """
        numbers = [str(random.randint(num_min, num_max)) for _ in range(operator_count + 1)]
        operators = [random.choice(["+", "-", "*", "/"]) for _ in range(operator_count)]

        if with_parentheses and max_pairs > 0 and operator_count >= 2:
            spans = self._pick_non_overlapping_spans(operator_count + 1, max_pairs)
            prefix = [""] * (operator_count + 1)
            suffix = [""] * (operator_count + 1)
            for start_idx, end_idx in spans:
                prefix[start_idx] += "("
                suffix[end_idx] = ")" + suffix[end_idx]
            for i in range(operator_count + 1):
                numbers[i] = f"{prefix[i]}{numbers[i]}{suffix[i]}"

        parts: list[str] = [numbers[0]]
        for i in range(operator_count):
            parts.append(operators[i])
            parts.append(numbers[i + 1])
        return " ".join(parts)

    def _pick_non_overlapping_spans(self, number_count: int, max_pairs: int) -> list[tuple[int, int]]:
        """Pick random non-overlapping inclusive ranges for parentheses."""
        span_limit = min(max_pairs, number_count // 2)
        target = random.randint(1, span_limit)
        spans: list[tuple[int, int]] = []

        for _ in range(40):
            if len(spans) >= target:
                break

            start = random.randint(0, number_count - 2)
            end = random.randint(start + 1, number_count - 1)
            candidate = (start, end)
            if any(self._is_overlap(candidate, existing) for existing in spans):
                continue
            spans.append(candidate)

        spans.sort(key=lambda s: (s[0], s[1]))
        return spans

    @staticmethod
    def _is_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return not (a[1] < b[0] or b[1] < a[0])
