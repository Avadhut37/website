import ast
from typing import Tuple


def validate_python_code(content: str) -> Tuple[bool, str | None]:
    """Return (is_valid, error_message)."""
    try:
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} at line {e.lineno}:{e.offset}"
