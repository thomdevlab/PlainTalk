import argparse
import datetime as _datetime
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path


class PlainTalkError(Exception):
    def __init__(self, message: str, *, line_no: int | None = None, line: str | None = None):
        super().__init__(message)
        self.line_no = line_no
        self.line = line


def _clean_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    # Allow trailing period on non-block sentences.
    if line.endswith(".") and not line.endswith(":"):
        line = line[:-1].rstrip()
    return line


def _split_args_english(text: str) -> list[str]:
    """
    Split "a, b, and c" into ["a", "b", "c"] while keeping quoted strings intact.
    This is intentionally small and predictable, not a full NLP parser.
    """
    text = text.strip()
    if not text:
        return []

    # Tokenize: either quoted strings or runs of non-comma chars.
    tokens: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in ("'", '"'):
            q = text[i]
            j = i + 1
            while j < len(text) and text[j] != q:
                if text[j] == "\\" and j + 1 < len(text):
                    j += 2
                else:
                    j += 1
            if j >= len(text):
                raise PlainTalkError("I found a quote that never closes. Please close the string with a matching quote.")
            tokens.append(text[i : j + 1])
            i = j + 1
        else:
            j = i
            while j < len(text) and text[j] != ",":
                j += 1
            tokens.append(text[i:j])
            i = j
        if i < len(text) and text[i] == ",":
            i += 1

    parts = [t.strip() for t in tokens if t.strip()]
    rebuilt = " ".join(parts)
    # Now split by " and " for the last conjunction, but only when it acts as a separator.
    # We accept both "a and b" and "a, b, and c".
    if " and " in rebuilt:
        # Prefer splitting on " and " only for the last occurrence.
        head, tail = rebuilt.rsplit(" and ", 1)
        left = [p.strip() for p in head.split(",") if p.strip()]
        right = tail.strip()
        return [*left, right]
    return [p.strip() for p in rebuilt.split(",") if p.strip()]


def parse_expression(expr: str) -> str:
    expr = expr.strip()
    if not expr:
        raise PlainTalkError("I was expecting an expression, but I found nothing.")

    # Strings and numbers pass through.
    if re.fullmatch(r"-?\d+(\.\d+)?", expr):
        return expr
    if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
        return expr

    # ---- Constants and date/time expressions ----
    if re.fullmatch(r"the value of pi", expr, flags=re.IGNORECASE):
        return "math.pi"
    if re.fullmatch(r"the value of tau", expr, flags=re.IGNORECASE):
        return "math.tau"
    if re.fullmatch(r"the value of euler(?:'s)? number", expr, flags=re.IGNORECASE):
        return "math.e"
    if re.fullmatch(r"the current date", expr, flags=re.IGNORECASE):
        return "_datetime.date.today()"
    if re.fullmatch(r"the current datetime", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now()"
    if re.fullmatch(r"the current year", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().year"
    if re.fullmatch(r"the current month", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().month"
    if re.fullmatch(r"the current day of the month", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().day"
    if re.fullmatch(r"the current weekday number", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().isoweekday()"
    if re.fullmatch(r"the current hour", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().hour"
    if re.fullmatch(r"the current minute", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().minute"
    if re.fullmatch(r"the current second", expr, flags=re.IGNORECASE):
        return "_datetime.datetime.now().second"

    # ---- Numeric conversions ----
    m = re.fullmatch(r"the number value of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"float({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the integer value of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"int(float({parse_expression(m.group(1))}))"
    m = re.fullmatch(r"the text value of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))})"

    # ---- Advanced math (nested phrases) ----
    m = re.fullmatch(r"the square root of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.sqrt({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the absolute value of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"abs({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the power of (.+) to (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} ** {parse_expression(m.group(2))})"
    m = re.fullmatch(r"the sine of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.sin({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the cosine of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.cos({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the tangent of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.tan({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the arcsine of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.asin({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the arccosine of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.acos({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the arctangent of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.atan({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the natural logarithm of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.log({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the logarithm of (.+) base (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.log({parse_expression(m.group(1))}, {parse_expression(m.group(2))})"
    m = re.fullmatch(r"the base ten logarithm of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.log10({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the exponential of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.exp({parse_expression(m.group(1))})"
    m = re.fullmatch(r"(.+) rounded to the nearest integer", expr, flags=re.IGNORECASE)
    if m:
        return f"int(round({parse_expression(m.group(1))}))"
    m = re.fullmatch(r"the floor of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.floor({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the ceiling of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"math.ceil({parse_expression(m.group(1))})"
    m = re.fullmatch(r"the minimum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"min({parse_expression(m.group(1))}, {parse_expression(m.group(2))})"
    m = re.fullmatch(r"the maximum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"max({parse_expression(m.group(1))}, {parse_expression(m.group(2))})"
    m = re.fullmatch(r"the sign of (.+)", expr, flags=re.IGNORECASE)
    if m:
        x = parse_expression(m.group(1))
        return f"(0 if ({x}) == 0 else (1 if ({x}) > 0 else -1))"

    m = re.fullmatch(r"the sum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} + {parse_expression(m.group(2))})"

    m = re.fullmatch(r"the difference of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} - {parse_expression(m.group(2))})"

    m = re.fullmatch(r"the product of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} * {parse_expression(m.group(2))})"

    m = re.fullmatch(r"the quotient of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} / {parse_expression(m.group(2))})"

    m = re.fullmatch(r"the remainder of (.+) divided by (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression(m.group(1))} % {parse_expression(m.group(2))})"

    m = re.fullmatch(r"(.+) clamped between (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        x = parse_expression(m.group(1))
        lo = parse_expression(m.group(2))
        hi = parse_expression(m.group(3))
        return f"max({lo}, min({hi}, {x}))"

    # ---- String manipulation (nested phrases) ----
    m = re.fullmatch(r"the length of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"len(str({parse_expression(m.group(1))}))"
    m = re.fullmatch(r"the uppercase form of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).upper()"
    m = re.fullmatch(r"the lowercase form of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).lower()"
    m = re.fullmatch(r"the trimmed form of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).strip()"
    m = re.fullmatch(r"the left-trimmed form of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).lstrip()"
    m = re.fullmatch(r"the right-trimmed form of (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).rstrip()"
    m = re.fullmatch(r"the result of replacing (.+) with (.+) in (.+)", expr, flags=re.IGNORECASE)
    if m:
        old = parse_expression(m.group(1))
        new = parse_expression(m.group(2))
        s = parse_expression(m.group(3))
        return f"str({s}).replace(str({old}), str({new}))"
    m = re.fullmatch(r"the result of splitting (.+) by delimiter (.+)", expr, flags=re.IGNORECASE)
    if m:
        s = parse_expression(m.group(1))
        delim = parse_expression(m.group(2))
        return f"str({s}).split(str({delim}))"
    m = re.fullmatch(r"the result of joining (.+) using delimiter (.+)", expr, flags=re.IGNORECASE)
    if m:
        items = parse_expression(m.group(1))
        delim = parse_expression(m.group(2))
        return f"str({delim}).join([str(_x) for _x in {items}])"
    m = re.fullmatch(r"the result of repeating (.+) (.+) times", expr, flags=re.IGNORECASE)
    if m:
        s = parse_expression(m.group(1))
        n = parse_expression(m.group(2))
        return f"(str({s}) * int({n}))"
    m = re.fullmatch(r"the result of taking the first (.+) characters of (.+)", expr, flags=re.IGNORECASE)
    if m:
        n = parse_expression(m.group(1))
        s = parse_expression(m.group(2))
        return f"str({s})[:int({n})]"
    m = re.fullmatch(r"the result of taking the last (.+) characters of (.+)", expr, flags=re.IGNORECASE)
    if m:
        n = parse_expression(m.group(1))
        s = parse_expression(m.group(2))
        return f"str({s})[-int({n}):]"
    m = re.fullmatch(r"the result of taking characters (.+) through (.+) of (.+)", expr, flags=re.IGNORECASE)
    if m:
        a = parse_expression(m.group(1))
        b = parse_expression(m.group(2))
        s = parse_expression(m.group(3))
        return f"str({s})[int({a})-1:int({b})]"
    m = re.fullmatch(r"whether (.+) starts with (.+)", expr, flags=re.IGNORECASE)
    if m:
        s = parse_expression(m.group(1))
        prefix = parse_expression(m.group(2))
        return f"str({s}).startswith(str({prefix}))"
    m = re.fullmatch(r"whether (.+) ends with (.+)", expr, flags=re.IGNORECASE)
    if m:
        s = parse_expression(m.group(1))
        suf = parse_expression(m.group(2))
        return f"str({s}).endswith(str({suf}))"
    m = re.fullmatch(r"whether (.+) contains (.+)", expr, flags=re.IGNORECASE)
    if m:
        s = parse_expression(m.group(1))
        sub = parse_expression(m.group(2))
        return f"(str({sub}) in str({s}))"
    m = re.fullmatch(r"the index of (.+) within (.+)", expr, flags=re.IGNORECASE)
    if m:
        sub = parse_expression(m.group(1))
        s = parse_expression(m.group(2))
        return f"str({s}).find(str({sub}))"
    m = re.fullmatch(r"the result of converting (.+) to uppercase", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).upper()"
    m = re.fullmatch(r"the result of converting (.+) to lowercase", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).lower()"
    m = re.fullmatch(r"the result of trimming whitespace from (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"str({parse_expression(m.group(1))}).strip()"

    # ---- File path expressions ----
    m = re.fullmatch(r"the path (.+)", expr, flags=re.IGNORECASE)
    if m:
        return f"Path(str({parse_expression(m.group(1))}))"
    m = re.fullmatch(r"whether the file (.+) exists", expr, flags=re.IGNORECASE)
    if m:
        p = parse_expression(m.group(1))
        return f"Path(str({p})).exists()"

    # ---- Random expressions ----
    m = re.fullmatch(r"a random number between (.+) and (.+)", expr, flags=re.IGNORECASE)
    if m:
        a = parse_expression(m.group(1))
        b = parse_expression(m.group(2))
        return f"random.uniform(float({a}), float({b}))"

    m = re.fullmatch(r"the result of calling ([A-Za-z_]\w*)(?: with (.+))?", expr, flags=re.IGNORECASE)
    if m:
        fn = m.group(1)
        args_text = (m.group(2) or "").strip()
        args = [parse_expression(a) for a in _split_args_english(args_text)]
        return f"{fn}({', '.join(args)})"

    # Box name.
    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        return expr

    raise PlainTalkError(
        "I couldn't understand that expression. "
        "Try a number, a quoted string, a box name, or a phrase like 'the sum of a and b'."
    )


def parse_condition(cond: str) -> str:
    cond = cond.strip()
    if not cond:
        raise PlainTalkError("I was expecting a condition, but I found nothing.")

    # Logical composition (lowest precedence first).
    # We split on the FIRST occurrence to keep parsing predictable.
    if re.search(r"\s+or else\s+", cond, flags=re.IGNORECASE):
        left, right = re.split(r"\s+or else\s+", cond, maxsplit=1, flags=re.IGNORECASE)
        return f"({parse_condition(left)} or {parse_condition(right)})"
    if re.search(r"\s+and also\s+", cond, flags=re.IGNORECASE):
        left, right = re.split(r"\s+and also\s+", cond, maxsplit=1, flags=re.IGNORECASE)
        return f"({parse_condition(left)} and {parse_condition(right)})"

    m = re.fullmatch(r"it is not true that (.+)", cond, flags=re.IGNORECASE)
    if m:
        return f"(not {parse_condition(m.group(1))})"
    m = re.fullmatch(r"not (.+)", cond, flags=re.IGNORECASE)
    if m:
        return f"(not {parse_condition(m.group(1))})"

    # Predicate-style conditions.
    m = re.fullmatch(r"whether (.+) starts with (.+)", cond, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression('whether ' + m.group(1) + ' starts with ' + m.group(2))})"
    m = re.fullmatch(r"whether (.+) ends with (.+)", cond, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression('whether ' + m.group(1) + ' ends with ' + m.group(2))})"
    m = re.fullmatch(r"whether (.+) contains (.+)", cond, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression('whether ' + m.group(1) + ' contains ' + m.group(2))})"
    m = re.fullmatch(r"whether the file (.+) exists", cond, flags=re.IGNORECASE)
    if m:
        return f"({parse_expression('whether the file ' + m.group(1) + ' exists')})"

    patterns: list[tuple[str, str]] = [
        (r"(.+) is greater than (.+)", ">"),
        (r"(.+) is less than (.+)", "<"),
        (r"(.+) is equal to (.+)", "=="),
        (r"(.+) is not equal to (.+)", "!="),
        (r"(.+) is at least (.+)", ">="),
        (r"(.+) is at most (.+)", "<="),
    ]
    for pat, op in patterns:
        m = re.fullmatch(pat, cond, flags=re.IGNORECASE)
        if m:
            left = parse_expression(m.group(1))
            right = parse_expression(m.group(2))
            return f"({left} {op} {right})"

    # Truthiness
    m = re.fullmatch(r"(.+) is true", cond, flags=re.IGNORECASE)
    if m:
        return f"(bool({parse_expression(m.group(1))}))"
    m = re.fullmatch(r"(.+) is false", cond, flags=re.IGNORECASE)
    if m:
        return f"(not bool({parse_expression(m.group(1))}))"

    raise PlainTalkError(
        "I couldn't understand that condition. "
        "Try something like 'userAge is greater than 18', or combine conditions with 'and also' / 'or else'."
    )


@dataclass
class Block:
    kind: str  # "if", "repeat", "while", "function"
    indent: int
    allow_otherwise: bool = False
    otherwise_seen: bool = False


def transpile_lines(lines: list[str]) -> str:
    out: list[str] = []
    blocks: list[Block] = []

    def emit(py: str) -> None:
        out.append(" " * (4 * len(blocks)) + py)

    def polite_error(line_no: int, original: str, message: str, suggestion: str | None = None) -> PlainTalkError:
        hint = ""
        if suggestion:
            hint = f"\nSuggestion: {suggestion}"
        return PlainTalkError(
            f"On line {line_no}, I couldn't follow this sentence:\n  {original}\n{message}{hint}",
            line_no=line_no,
            line=original,
        )

    for idx, raw in enumerate(lines, start=1):
        original = raw.rstrip("\n")
        line = _clean_line(original)
        if not line:
            continue

        # Allow visual indentation in .talk but do not require it.
        line = line.lstrip()

        # Block endings / markers
        if re.fullmatch(r"End if", line, flags=re.IGNORECASE):
            if not blocks or blocks[-1].kind != "if":
                raise polite_error(idx, original, "I found 'End if' without a matching 'If ... then:' block.")
            blocks.pop()
            continue

        if re.fullmatch(r"End repeat", line, flags=re.IGNORECASE):
            if not blocks or blocks[-1].kind != "repeat":
                raise polite_error(idx, original, "I found 'End repeat' without a matching 'Repeat ... times:' block.")
            blocks.pop()
            continue

        if re.fullmatch(r"End while", line, flags=re.IGNORECASE):
            if not blocks or blocks[-1].kind != "while":
                raise polite_error(idx, original, "I found 'End while' without a matching 'While ... do:' block.")
            blocks.pop()
            continue

        if re.fullmatch(r"End function", line, flags=re.IGNORECASE):
            if not blocks or blocks[-1].kind != "function":
                raise polite_error(
                    idx, original, "I found 'End function' without a matching 'To define a function ...:' block."
                )
            blocks.pop()
            continue

        if re.fullmatch(r"Otherwise:", line, flags=re.IGNORECASE):
            if not blocks or blocks[-1].kind != "if":
                raise polite_error(idx, original, "I found 'Otherwise:' but I'm not inside an 'If ... then:' block.")
            blk = blocks[-1]
            if blk.otherwise_seen:
                raise polite_error(idx, original, "I found a second 'Otherwise:' for the same 'If' block.")
            blk.otherwise_seen = True
            # Dedent one level for else: it aligns with the if header.
            out.append(" " * (4 * (len(blocks) - 1)) + "else:")
            continue

        # Repeat block header
        m = re.fullmatch(
            r"Repeat the following steps (.+) times(?: using a counter called ([A-Za-z_]\w*))?:",
            line,
            flags=re.IGNORECASE,
        )
        if m:
            count_expr = m.group(1).strip()
            counter = m.group(2) or "_"
            try:
                py_n = parse_expression(count_expr)
            except PlainTalkError as e:
                raise polite_error(
                    idx,
                    original,
                    str(e),
                    "Repeat the following steps 5 times:",
                )
            emit(f"for {counter} in range(1, int({py_n}) + 1):")
            blocks.append(Block(kind="repeat", indent=len(blocks)))
            continue

        # While block header
        m = re.fullmatch(r"While (.+), do:", line, flags=re.IGNORECASE)
        if m:
            cond_text = m.group(1).strip()
            try:
                py_cond = parse_condition(cond_text)
            except PlainTalkError as e:
                raise polite_error(idx, original, str(e), "While userAge is less than 100, do:")
            emit(f"while {py_cond}:")
            blocks.append(Block(kind="while", indent=len(blocks)))
            continue

        # If block header
        m = re.fullmatch(r"If (.+), then:", line, flags=re.IGNORECASE)
        if m:
            cond_text = m.group(1).strip()
            try:
                py_cond = parse_condition(cond_text)
            except PlainTalkError as e:
                raise polite_error(idx, original, str(e), "If userAge is greater than 18, then:")
            emit(f"if {py_cond}:")
            blocks.append(Block(kind="if", indent=len(blocks), allow_otherwise=True))
            continue

        # Single-line if
        m = re.fullmatch(r"If (.+), then (.+)", line, flags=re.IGNORECASE)
        if m:
            cond_text = m.group(1).strip()
            stmt_text = m.group(2).strip()
            try:
                py_cond = parse_condition(cond_text)
            except PlainTalkError as e:
                raise polite_error(idx, original, str(e), "If userAge is greater than 18, then print 'Access Granted'.")
            emit(f"if {py_cond}:")
            blocks.append(Block(kind="if", indent=len(blocks), allow_otherwise=False))
            # Compile the single statement inside the temporary if block.
            try:
                py_stmt = _transpile_single_statement(stmt_text, idx, original)
            except PlainTalkError as e:
                raise polite_error(idx, original, str(e))
            emit(py_stmt)
            blocks.pop()
            continue

        # Function header
        m = re.fullmatch(
            r"To define a function called ([A-Za-z_]\w*)(?: that takes (.+))?:",
            line,
            flags=re.IGNORECASE,
        )
        if m:
            fn = m.group(1)
            params_text = (m.group(2) or "").strip()
            params = [p.strip() for p in _split_args_english(params_text)]
            for p in params:
                if not re.fullmatch(r"[A-Za-z_]\w*", p):
                    raise polite_error(
                        idx,
                        original,
                        f"I couldn't use '{p}' as a parameter name.",
                        "To define a function called add that takes a and b:",
                    )
            emit(f"def {fn}({', '.join(params)}):")
            blocks.append(Block(kind="function", indent=len(blocks)))
            continue

        # Normal statement
        try:
            py_stmt = _transpile_single_statement(line, idx, original)
        except PlainTalkError as e:
            raise polite_error(
                idx,
                original,
                str(e),
                "Store the value 25 into a box called userAge.",
            )
        emit(py_stmt)

    if blocks:
        last = blocks[-1].kind
        expected = {"if": "End if.", "repeat": "End repeat.", "while": "End while.", "function": "End function."}[last]
        raise PlainTalkError(
            f"It looks like your program ends while a '{last}' block is still open. "
            f"Please add '{expected}' at the end."
        )

    return "\n".join(out) + "\n"


def _transpile_single_statement(line: str, line_no: int, original: str) -> str:
    # Store
    m = re.fullmatch(r"Store the value (.+) into a box called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        return f"{m.group(2)} = {parse_expression(m.group(1))}"

    # Print
    m = re.fullmatch(r"Print (.+)", line, flags=re.IGNORECASE)
    if m:
        return f"print({parse_expression(m.group(1))})"

    # Wait
    m = re.fullmatch(r"Wait for (.+) seconds", line, flags=re.IGNORECASE)
    if m:
        return f"time.sleep(float({parse_expression(m.group(1))}))"

    # Clear screen
    m = re.fullmatch(r"Clear the screen", line, flags=re.IGNORECASE)
    if m:
        return r"os.system('cls' if os.name == 'nt' else 'clear')"

    # Exit
    m = re.fullmatch(r"Exit the program", line, flags=re.IGNORECASE)
    if m:
        return "raise SystemExit(0)"
    m = re.fullmatch(r"Exit the program with code (.+)", line, flags=re.IGNORECASE)
    if m:
        return f"raise SystemExit(int({parse_expression(m.group(1))}))"

    # Input
    m = re.fullmatch(
        r"Ask the user for (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        prompt = parse_expression(m.group(1))
        box = m.group(2)
        return f"{box} = input({prompt})"

    # Loop controls
    m = re.fullmatch(r"Break out of the loop", line, flags=re.IGNORECASE)
    if m:
        return "break"
    m = re.fullmatch(r"Continue to the next step", line, flags=re.IGNORECASE)
    if m:
        return "continue"

    # Collections
    m = re.fullmatch(r"Create an empty collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)} = []"

    m = re.fullmatch(r"Add (.+) to the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        return f"{m.group(2)}.append({parse_expression(m.group(1))})"

    m = re.fullmatch(r"Insert (.+) into the collection called ([A-Za-z_]\w*) at position (.+)", line, flags=re.IGNORECASE)
    if m:
        item = parse_expression(m.group(1))
        coll = m.group(2)
        pos = parse_expression(m.group(3))
        return f"{coll}.insert(int({pos}) - 1, {item})"

    m = re.fullmatch(r"Remove the item at position (.+) from the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        pos = parse_expression(m.group(1))
        coll = m.group(2)
        return f"{coll}.pop(int({pos}) - 1)"

    m = re.fullmatch(r"Remove the last item from the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)}.pop()"

    m = re.fullmatch(
        r"Remove all items from the collection called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}.clear()"

    m = re.fullmatch(
        r"Store the number of items in the collection called ([A-Za-z_]\w*) into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        coll, box = m.group(1), m.group(2)
        return f"{box} = len({coll})"

    m = re.fullmatch(
        r"Store the item at position (.+) in the collection called ([A-Za-z_]\w*) into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        pos_expr = parse_expression(m.group(1))
        coll = m.group(2)
        box = m.group(3)
        return f"{box} = {coll}[int({pos_expr}) - 1]"

    m = re.fullmatch(
        r"Set the item at position (.+) in the collection called ([A-Za-z_]\w*) to (.+)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        pos_expr = parse_expression(m.group(1))
        coll = m.group(2)
        value = parse_expression(m.group(3))
        return f"{coll}[int({pos_expr}) - 1] = {value}"

    # File I/O
    m = re.fullmatch(r"Write (.+) into a file named (.+)", line, flags=re.IGNORECASE)
    if m:
        content = parse_expression(m.group(1))
        name = parse_expression(m.group(2))
        return f"Path(str({name})).write_text(str({content}), encoding='utf-8')"

    m = re.fullmatch(r"Append (.+) into a file named (.+)", line, flags=re.IGNORECASE)
    if m:
        content = parse_expression(m.group(1))
        name = parse_expression(m.group(2))
        return f"Path(str({name})).open('a', encoding='utf-8').write(str({content}))"

    m = re.fullmatch(r"Read the content of file (.+) into a box called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        file_expr = parse_expression(m.group(1))
        box = m.group(2)
        return f"{box} = Path(str({file_expr})).read_text(encoding='utf-8')"

    m = re.fullmatch(r"Check if file (.+) exists and store the result into a box called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        file_expr = parse_expression(m.group(1))
        box = m.group(2)
        return f"{box} = Path(str({file_expr})).exists()"

    m = re.fullmatch(r"Delete the file named (.+)", line, flags=re.IGNORECASE)
    if m:
        name = parse_expression(m.group(1))
        return f"Path(str({name})).unlink(missing_ok=True)"

    m = re.fullmatch(r"Create the folder named (.+)", line, flags=re.IGNORECASE)
    if m:
        name = parse_expression(m.group(1))
        return f"Path(str({name})).mkdir(parents=True, exist_ok=True)"

    # Random (statement form)
    m = re.fullmatch(
        r"Generate a random number between (.+) and (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        a = parse_expression(m.group(1))
        b = parse_expression(m.group(2))
        box = m.group(3)
        return f"{box} = random.uniform(float({a}), float({b}))"

    m = re.fullmatch(
        r"Generate a random integer between (.+) and (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        a = parse_expression(m.group(1))
        b = parse_expression(m.group(2))
        box = m.group(3)
        return f"{box} = random.randint(int({a}), int({b}))"

    # Return
    m = re.fullmatch(r"Return (.+)", line, flags=re.IGNORECASE)
    if m:
        return f"return {parse_expression(m.group(1))}"

    # Call (store result)
    m = re.fullmatch(
        r"Call ([A-Za-z_]\w*)(?: with (.+))? and store the result into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        fn = m.group(1)
        args_text = (m.group(2) or "").strip()
        args = [parse_expression(a) for a in _split_args_english(args_text)]
        box = m.group(3)
        return f"{box} = {fn}({', '.join(args)})"

    # Call (no result)
    m = re.fullmatch(r"Call ([A-Za-z_]\w*)(?: with (.+))?", line, flags=re.IGNORECASE)
    if m:
        fn = m.group(1)
        args_text = (m.group(2) or "").strip()
        args = [parse_expression(a) for a in _split_args_english(args_text)]
        return f"{fn}({', '.join(args)})"

    raise PlainTalkError(
        "I couldn't match this sentence to a known PlainTalk rule. "
        "Please rewrite it using one of the documented patterns."
    )


def transpile_file(input_path: str) -> str:
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return transpile_lines(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="plaintalk", description="Transpile PlainTalk (.talk) into Python.")
    ap.add_argument("source", nargs='?', help="Path to a .talk file")
    ap.add_argument("--emit", help="Write transpiled Python to this path")
    ap.add_argument("--run", action="store_true", help="Execute the transpiled program")
    ap.add_argument("-c", "--command", help="Execute PlainTalk command directly")
    ns = ap.parse_args(argv)

    # Handle -c command option
    if ns.command:
        try:
            py = transpile_lines([ns.command])
        except PlainTalkError as e:
            print(str(e), file=sys.stderr)
            return 2
        
        # Execute the command
        glb: dict[str, object] = {"__name__": "__main__"}
        try:
            exec(compile(py, "<command>", "exec"), glb, glb)
        except Exception as e:
            print(
                "I translated your PlainTalk into Python, but Python raised an error while running it.\n"
                f"Python said: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            return 1
        return 0
    
    # Handle file input
    if not ns.source:
        print("Error: No source file specified", file=sys.stderr)
        ap.print_help()
        return 1

    try:
        py = transpile_file(ns.source)
    except PlainTalkError as e:
        print(str(e), file=sys.stderr)
        return 2

    if ns.emit:
        with open(ns.emit, "w", encoding="utf-8") as f:
            f.write(py)

    if ns.run:
        # Execute in a fresh global namespace.
        glb: dict[str, object] = {"__name__": "__main__"}
        try:
            exec(compile(py, ns.source, "exec"), glb, glb)
        except Exception as e:
            print(
                "I translated your PlainTalk into Python, but Python raised an error while running it.\n"
                f"Python said: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            return 1

    if not ns.run and not ns.emit:
        # Default: print transpiled Python to stdout.
        print(py, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

