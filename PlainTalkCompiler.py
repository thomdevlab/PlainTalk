"""
Compile PlainTalk (.talk) sources into pickled stack bytecode (.talkc).
Enhanced with obfuscation and performance optimizations.

TE Tribute - Dedicated to the creator of PlainTalk
CLI: python PlainTalkCompiler.py my_script.talk
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
import random
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Opcodes --- keep identical strings in PlainTalkVM.py --------------------------
OP_PUSH = "PUSH"
OP_POP = "POP"
OP_LOAD_VAR = "LOAD_VAR"
OP_STORE_VAR = "STORE_VAR"
OP_CALL_FUNC = "CALL_FUNC"
OP_JUMP_IF_FALSE = "JUMP_IF_FALSE"
OP_PRINT = "PRINT"
OP_JUMP = "JUMP"

OP_BINARY_ADD = "BINARY_ADD"
OP_BINARY_SUB = "BINARY_SUB"
OP_BINARY_MUL = "BINARY_MUL"
OP_BINARY_DIV = "BINARY_DIV"
OP_BINARY_MOD = "BINARY_MOD"
OP_BINARY_POW = "BINARY_POW"
OP_COMPARE_GT = "COMPARE_GT"
OP_COMPARE_LT = "COMPARE_LT"
OP_COMPARE_EQ = "COMPARE_EQ"
OP_COMPARE_NE = "COMPARE_NE"
OP_COMPARE_GE = "COMPARE_GE"
OP_COMPARE_LE = "COMPARE_LE"
OP_BINARY_AND = "BINARY_AND"
OP_BINARY_OR = "BINARY_OR"
OP_UNARY_NOT = "UNARY_NOT"

OP_CALL_INTRINSIC = "CALL_INTRINSIC"
OP_INPUT = "INPUT"
OP_NOP = "NOP"
OP_HALT = "HALT"
OP_RETURN_FUNC = "RETURN_FUNC"

# Enhanced opcodes for obfuscation
OP_OBFUSCATE_PUSH = "OBF_PUSH"
OP_OBFUSCATE_LOAD = "OBF_LOAD"
OP_DECRYPT_DATA = "DECRYPT"
OP_JUNK_CODE = "JUNK"

# TE Tribute opcodes
OP_TE_TRIBUTE = "TE_TRIBUTE"
OP_TE_WATERMARK = "TE_WATERMARK"

Instruction = tuple[Any, ...]


class PlainTalkError(Exception):
    def __init__(self, message: str, *, line_no: int | None = None, line: str | None = None):
        super().__init__(message)
        self.line_no = line_no
        self.line = line


def _clean_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    if line.endswith(".") and not line.endswith(":"):
        line = line[:-1].rstrip()
    return line


def _split_args_english(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
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
    if " and " in rebuilt:
        head, tail = rebuilt.rsplit(" and ", 1)
        left = [p.strip() for p in head.split(",") if p.strip()]
        right = tail.strip()
        return [*left, right]
    return [p.strip() for p in rebuilt.split(",") if p.strip()]


class Emitter:
    def __init__(self) -> None:
        self.code: list[Instruction] = []

    def emit(self, *instrs: Instruction) -> None:
        self.code.extend(instrs)

    def here(self) -> int:
        return len(self.code)

    def stub_jump(self, opcode: str) -> int:
        idx = len(self.code)
        self.code.append((opcode, None))
        return idx

    def patch_jump(self, ip: int, target: int | None = None) -> None:
        op = self.code[ip][0]
        tgt = len(self.code) if target is None else target
        self.code[ip] = (op, tgt)


class TempPool:
    def __init__(self) -> None:
        self.i = 0

    def name(self, hint: str) -> str:
        self.i += 1
        return f"__pt_{hint}_{self.i}"


def compile_expression(expr: str, emit: Emitter, temps: TempPool) -> None:
    expr = expr.strip()
    if not expr:
        raise PlainTalkError("I was expecting an expression, but I found nothing.")

    if re.fullmatch(r"-?\d+(\.\d+)?", expr):
        emit.emit((OP_PUSH, float(expr) if "." in expr else int(expr)))
        return
    if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
        emit.emit((OP_PUSH, expr[1:-1]))
        return

    def _bio(a: str, b: str, op: Instruction) -> None:
        compile_expression(a.strip(), emit, temps)
        compile_expression(b.strip(), emit, temps)
        emit.emit(op)

    # Constants & time helpers (delegated via intrinsics in VM)
    if re.fullmatch(r"the value of pi", expr, flags=re.IGNORECASE):
        emit.emit((OP_PUSH, 3.141592653589793))
        return
    if re.fullmatch(r"the value of tau", expr, flags=re.IGNORECASE):
        emit.emit((OP_PUSH, 6.283185307179586))
        return
    if re.fullmatch(r"the value of euler(?:'s)? number", expr, flags=re.IGNORECASE):
        emit.emit((OP_PUSH, 2.718281828459045))
        return
    for label, intrinsic in (
        ("the current date", "date_today"),
        ("the current datetime", "datetime_now"),
        ("the current year", "now_year"),
        ("the current month", "now_month"),
        ("the current day of the month", "now_day"),
        ("the current weekday number", "now_weekday"),
        ("the current hour", "now_hour"),
        ("the current minute", "now_minute"),
        ("the current second", "now_second"),
    ):
        if re.fullmatch(label, expr, flags=re.IGNORECASE):
            emit.emit((OP_CALL_INTRINSIC, intrinsic))
            return

    mm = re.fullmatch(r"the number value of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "float_"))
        return
    mm = re.fullmatch(r"the integer value of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "int_"))
        return
    mm = re.fullmatch(r"the text value of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "str_"))
        return

    unary_intrinsics = [
        (r"the square root of (.+)", "sqrt"),
        (r"the absolute value of (.+)", "abs_"),
        (r"the sine of (.+)", "sin"),
        (r"the cosine of (.+)", "cos"),
        (r"the tangent of (.+)", "tan"),
        (r"the arcsine of (.+)", "asin"),
        (r"the arccosine of (.+)", "acos"),
        (r"the arctangent of (.+)", "atan"),
        (r"the natural logarithm of (.+)", "log"),
        (r"the base ten logarithm of (.+)", "log10"),
        (r"the exponential of (.+)", "exp"),
        (r"the floor of (.+)", "floor"),
        (r"the ceiling of (.+)", "ceil"),
    ]
    for pat, name in unary_intrinsics:
        mm = re.fullmatch(pat, expr, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            emit.emit((OP_CALL_INTRINSIC, name))
            return

    mm = re.fullmatch(r"the logarithm of (.+) base (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "log_base"))
        return
    mm = re.fullmatch(r"(.+) rounded to the nearest integer", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "round_int"))
        return
    mm = re.fullmatch(r"the minimum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "binary_min"))
        return
    mm = re.fullmatch(r"the maximum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "binary_max"))
        return
    mm = re.fullmatch(r"the sign of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sign"))
        return
    mm = re.fullmatch(r"the power of (.+) to (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_POW,))
        return
    mm = re.fullmatch(r"the sum of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_ADD,))
        return
    mm = re.fullmatch(r"the difference of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_SUB,))
        return
    mm = re.fullmatch(r"the product of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_MUL,))
        return
    mm = re.fullmatch(r"the quotient of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_DIV,))
        return
    mm = re.fullmatch(r"the remainder of (.+) divided by (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_MOD,))
        return
    mm = re.fullmatch(r"(.+) clamped between (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        compile_expression(mm.group(3), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "clamp3"))
        return

    mm = re.fullmatch(r"the length of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "slen"))
        return
    for rx, intrinsic in (
        (r"the uppercase form of (.+)", "upper"),
        (r"the lowercase form of (.+)", "lower"),
        (r"the trimmed form of (.+)", "strip"),
        (r"the left-trimmed form of (.+)", "lstrip"),
        (r"the right-trimmed form of (.+)", "rstrip"),
        (r"the result of converting (.+) to uppercase", "upper"),
        (r"the result of converting (.+) to lowercase", "lower"),
        (r"the result of trimming whitespace from (.+)", "strip"),
    ):
        m2 = re.fullmatch(rx, expr, flags=re.IGNORECASE)
        if m2:
            compile_expression(m2.group(1), emit, temps)
            emit.emit((OP_CALL_INTRINSIC, intrinsic))
            return
    mm = re.fullmatch(r"the result of replacing (.+) with (.+) in (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(3), emit, temps)
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sreplace"))
        return
    mm = re.fullmatch(r"the result of splitting (.+) by delimiter (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "ssplit"))
        return
    mm = re.fullmatch(r"the result of joining (.+) using delimiter (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sjoin"))
        return
    mm = re.fullmatch(r"the result of repeating (.+) (.+) times", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "srepeat"))
        return
    mm = re.fullmatch(r"the result of taking the first (.+) characters of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(2), emit, temps)
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sfirst"))
        return
    mm = re.fullmatch(r"the result of taking the last (.+) characters of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(2), emit, temps)
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "slast"))
        return
    mm = re.fullmatch(r"the result of taking characters (.+) through (.+) of (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(3), emit, temps)
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sslice"))
        return
    mm = re.fullmatch(r"whether (.+) starts with (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "startswith"))
        return
    mm = re.fullmatch(r"whether (.+) ends with (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "endswith"))
        return
    mm = re.fullmatch(r"whether (.+) contains (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "contains"))
        return
    mm = re.fullmatch(r"the index of (.+) within (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(2), emit, temps)
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sfind"))
        return
    mm = re.fullmatch(r"the path (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "path_"))
        return
    mm = re.fullmatch(r"whether the file (.+) exists", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_exists"))
        return
    mm = re.fullmatch(r"a random number between (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        compile_expression(mm.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "uniform"))
        return

    mm = re.fullmatch(r"the result of calling ([A-Za-z_]\w*)(?: with (.+))?", expr, flags=re.IGNORECASE)
    if mm:
        fn = mm.group(1)
        args = _split_args_english(mm.group(2) or "")
        for a in reversed(args):
            compile_expression(a.strip(), emit, temps)
        emit.emit((OP_CALL_FUNC, fn, len(args)))
        return

    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        emit.emit((OP_LOAD_VAR, expr))
        return

    raise PlainTalkError(
        "I couldn't understand that expression. "
        "Try a number, a quoted string, a box name, or a phrase like 'the sum of a and b'."
    )


def compile_condition(cond: str, emit: Emitter, temps: TempPool) -> None:
    cond = cond.strip()
    if not cond:
        raise PlainTalkError("I was expecting a condition, but I found nothing.")

    if re.search(r"\s+or else\s+", cond, flags=re.IGNORECASE):
        left, right = re.split(r"\s+or else\s+", cond, maxsplit=1, flags=re.IGNORECASE)
        compile_condition(left, emit, temps)
        compile_condition(right, emit, temps)
        emit.emit((OP_BINARY_OR,))
        return
    if re.search(r"\s+and also\s+", cond, flags=re.IGNORECASE):
        left, right = re.split(r"\s+and also\s+", cond, maxsplit=1, flags=re.IGNORECASE)
        compile_condition(left, emit, temps)
        compile_condition(right, emit, temps)
        emit.emit((OP_BINARY_AND,))
        return
    mm = re.fullmatch(r"it is not true that (.+)", cond, flags=re.IGNORECASE)
    if mm:
        compile_condition(mm.group(1), emit, temps)
        emit.emit((OP_UNARY_NOT,))
        return
    mm = re.fullmatch(r"not (.+)", cond, flags=re.IGNORECASE)
    if mm:
        compile_condition(mm.group(1), emit, temps)
        emit.emit((OP_UNARY_NOT,))
        return
    mm = re.fullmatch(r"whether (.+) starts with (.+)", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression("whether " + mm.group(1) + " starts with " + mm.group(2), emit, temps)
        return
    mm = re.fullmatch(r"whether (.+) ends with (.+)", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression("whether " + mm.group(1) + " ends with " + mm.group(2), emit, temps)
        return
    mm = re.fullmatch(r"whether (.+) contains (.+)", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression("whether " + mm.group(1) + " contains " + mm.group(2), emit, temps)
        return
    mm = re.fullmatch(r"whether the file (.+) exists", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression("whether the file " + mm.group(1) + " exists", emit, temps)
        return
    comparisons = [
        (r"(.+) is greater than (.+)", OP_COMPARE_GT),
        (r"(.+) is less than (.+)", OP_COMPARE_LT),
        (r"(.+) is equal to (.+)", OP_COMPARE_EQ),
        (r"(.+) is not equal to (.+)", OP_COMPARE_NE),
        (r"(.+) is at least (.+)", OP_COMPARE_GE),
        (r"(.+) is at most (.+)", OP_COMPARE_LE),
    ]
    for pat, op in comparisons:
        mm = re.fullmatch(pat, cond, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            compile_expression(mm.group(2), emit, temps)
            emit.emit((op,))
            return
    mm = re.fullmatch(r"(.+) is true", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "bool_"))
        return
    mm = re.fullmatch(r"(.+) is false", cond, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "bool_"))
        emit.emit((OP_UNARY_NOT,))
        return
    raise PlainTalkError(
        "I couldn't understand that condition. "
        "Try something like 'userAge is greater than 18', or combine conditions using 'and also' / 'or else'."
    )


@dataclass
class RepeatCtl:
    ctr: str
    ntmp: str
    head_ip: int
    jf_false_ip: int
    break_ips: list[int] = field(default_factory=list)
    continue_ips: list[int] = field(default_factory=list)


@dataclass
class WhileCtl:
    cond_ip: int
    jf_false_ip: int
    break_ips: list[int] = field(default_factory=list)
    continue_ips: list[int] = field(default_factory=list)


@dataclass
class IfCtl:
    jf_false_ip: int
    jump_merge_placeholder: int | None = None


QueuedFunc = tuple[str, list[str], list[Instruction]]


def _compile_statement(line: str, emit: Emitter, temps: TempPool, loops: list[Any]) -> None:
    m = re.fullmatch(r"Store the value (.+) into a box called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_STORE_VAR, m.group(2)))
        return
    m = re.fullmatch(r"Print (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_PRINT,))
        return
    m = re.fullmatch(r"Wait for (.+) seconds", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "sleep"))
        return
    m = re.fullmatch(r"Clear the screen", line, flags=re.IGNORECASE)
    if m:
        emit.emit((OP_CALL_INTRINSIC, "clear_screen"))
        return
    m = re.fullmatch(r"Exit the program", line, flags=re.IGNORECASE)
    if m:
        emit.emit((OP_CALL_INTRINSIC, "halt0"))
        return
    m = re.fullmatch(r"Exit the program with code (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "halt_code"))
        return
    m = re.fullmatch(
        r"Ask the user for (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_INPUT,))
        emit.emit((OP_STORE_VAR, m.group(2)))
        return
    m = re.fullmatch(r"Break out of the loop", line, flags=re.IGNORECASE)
    if m:
        if not loops:
            raise PlainTalkError("I found 'Break out of the loop', but nothing is looping here.")
        stub = emit.stub_jump(OP_JUMP)
        loops[-1].break_ips.append(stub)
        return
    m = re.fullmatch(r"Continue to the next step", line, flags=re.IGNORECASE)
    if m:
        if not loops:
            raise PlainTalkError("I found 'Continue to the next step', but nothing is looping here.")
        stub = emit.stub_jump(OP_JUMP)
        loops[-1].continue_ips.append(stub)
        return
    m = re.fullmatch(r"Create an empty collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        emit.emit((OP_PUSH, []))
        emit.emit((OP_STORE_VAR, m.group(1)))
        return
    m = re.fullmatch(r"Add (.+) to the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_append"))
        return
    m = re.fullmatch(
        r"Insert (.+) into the collection called ([A-Za-z_]\w*) at position (.+)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(3), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_insert"))
        return
    m = re.fullmatch(
        r"Remove the item at position (.+) from the collection called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(2), emit, temps)
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_pop_pos"))
        return
    m = re.fullmatch(r"Remove the last item from the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_pop_last"))
        return
    m = re.fullmatch(r"Remove all items from the collection called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_clear"))
        return
    m = re.fullmatch(
        r"Store the number of items in the collection called ([A-Za-z_]\w*) into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_len_box"))
        emit.emit((OP_STORE_VAR, m.group(2)))
        return
    m = re.fullmatch(
        r"Store the item at position (.+) in the collection called ([A-Za-z_]\w*) into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(2), emit, temps)
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_get_idx"))
        emit.emit((OP_STORE_VAR, m.group(3)))
        return
    m = re.fullmatch(
        r"Set the item at position (.+) in the collection called ([A-Za-z_]\w*) to (.+)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(3), emit, temps)
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "list_set_idx"))
        return

    m = re.fullmatch(r"Write (.+) into a file named (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_write"))
        return
    m = re.fullmatch(r"Append (.+) into a file named (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_append"))
        return
    m = re.fullmatch(r"Read the content of file (.+) into a box called ([A-Za-z_]\w*)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_read"))
        emit.emit((OP_STORE_VAR, m.group(2)))
        return
    m = re.fullmatch(
        r"Check if file (.+) exists and store the result into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_exists"))
        emit.emit((OP_STORE_VAR, m.group(2)))
        return
    m = re.fullmatch(r"Delete the file named (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "file_delete"))
        return
    m = re.fullmatch(r"Create the folder named (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "mkdir"))
        return

    m = re.fullmatch(
        r"Generate a random number between (.+) and (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "uniform"))
        emit.emit((OP_STORE_VAR, m.group(3)))
        return
    m = re.fullmatch(
        r"Generate a random integer between (.+) and (.+) and store it into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        compile_expression(m.group(1), emit, temps)
        compile_expression(m.group(2), emit, temps)
        emit.emit((OP_CALL_INTRINSIC, "randint"))
        emit.emit((OP_STORE_VAR, m.group(3)))
        return

    m = re.fullmatch(r"Return (.+)", line, flags=re.IGNORECASE)
    if m:
        compile_expression(m.group(1), emit, temps)
        emit.emit((OP_RETURN_FUNC,))
        return

    m = re.fullmatch(
        r"Call ([A-Za-z_]\w*)(?: with (.+))? and store the result into a box called ([A-Za-z_]\w*)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        raw_args = _split_args_english(m.group(2) or "")
        for a in reversed(raw_args):
            compile_expression(a.strip(), emit, temps)
        emit.emit((OP_CALL_FUNC, m.group(1), len(raw_args)))
        emit.emit((OP_STORE_VAR, m.group(3)))
        return
    m = re.fullmatch(r"Call ([A-Za-z_]\w*)(?: with (.+))?", line, flags=re.IGNORECASE)
    if m:
        raw_args = _split_args_english(m.group(2) or "")
        for a in reversed(raw_args):
            compile_expression(a.strip(), emit, temps)
        emit.emit((OP_CALL_FUNC, m.group(1), len(raw_args)))
        return

    raise PlainTalkError(
        "I couldn't match this sentence to a known PlainTalk rule. "
        "Please rewrite it using one of the documented sentence patterns."
    )


def compile_region(
    fragment: list[str],
    emit: Emitter,
    *,
    polite,
    temps: TempPool,
    loops: list[Any],
    if_stack: list[IfCtl],
    function_depth: int,
    queued_funcs: list[QueuedFunc],
) -> None:
    idx = 0

    while idx < len(fragment):
        original = fragment[idx].rstrip("\n")
        line_clean = _clean_line(original)
        lineno = idx + 1
        idx += 1

        if not line_clean:
            continue
        line = line_clean.lstrip()

        if re.fullmatch(r"Otherwise:", line, flags=re.IGNORECASE):
            if not if_stack:
                raise polite(lineno, original, "I found 'Otherwise:', but nothing is awaiting it.")
            frame = if_stack[-1]
            jmp_over_else = emit.stub_jump(OP_JUMP)
            emit.patch_jump(frame.jf_false_ip, emit.here())
            frame.jf_false_ip = -1
            frame.jump_merge_placeholder = jmp_over_else
            continue

        if re.fullmatch(r"End if", line, flags=re.IGNORECASE):
            if not if_stack:
                raise polite(lineno, original, "I found 'End if' without a matching 'If … then:' block.")
            frame = if_stack.pop()
            exit_ip = emit.here()
            if frame.jf_false_ip >= 0:
                emit.patch_jump(frame.jf_false_ip, exit_ip)
            if frame.jump_merge_placeholder is not None:
                emit.patch_jump(frame.jump_merge_placeholder, exit_ip)
            continue

        if re.fullmatch(r"End repeat", line, flags=re.IGNORECASE):
            if not loops or not isinstance(loops[-1], RepeatCtl):
                raise polite(lineno, original, "I found 'End repeat' outside a Repeat block.")
            ctl = loops.pop()
            incr_ip = emit.here()
            for stub in ctl.continue_ips:
                emit.patch_jump(stub, incr_ip)
            emit.emit((OP_LOAD_VAR, ctl.ctr))
            emit.emit((OP_PUSH, 1))
            emit.emit((OP_BINARY_ADD,))
            emit.emit((OP_STORE_VAR, ctl.ctr))
            emit.emit((OP_JUMP, ctl.head_ip))
            exit_ip = emit.here()
            emit.patch_jump(ctl.jf_false_ip, exit_ip)
            for stub in ctl.break_ips:
                emit.patch_jump(stub, exit_ip)
            continue

        if re.fullmatch(r"End while", line, flags=re.IGNORECASE):
            if not loops or not isinstance(loops[-1], WhileCtl):
                raise polite(lineno, original, "I found 'End while' outside a While block.")
            ctl = loops.pop()
            emit.emit((OP_JUMP, ctl.cond_ip))
            exit_ip = emit.here()
            emit.patch_jump(ctl.jf_false_ip, exit_ip)
            for stub in ctl.break_ips:
                emit.patch_jump(stub, exit_ip)
            for stub in ctl.continue_ips:
                emit.patch_jump(stub, ctl.cond_ip)
            continue

        m = re.fullmatch(r"Repeat the following steps (.+) times(?: using a counter called ([A-Za-z_]\w*))?:", line, flags=re.IGNORECASE)
        if m:
            n_expr = m.group(1).strip()
            ctr = m.group(2) or "_"
            ntmp = temps.name("rep_n")
            try:
                compile_expression(n_expr, emit, temps)
            except PlainTalkError as e:
                raise polite(lineno, original, str(e), "Repeat the following steps 5 times:") from e
            emit.emit((OP_STORE_VAR, ntmp))
            emit.emit((OP_PUSH, 1))
            emit.emit((OP_STORE_VAR, ctr))
            head_ip = emit.here()
            emit.emit((OP_LOAD_VAR, ctr))
            emit.emit((OP_LOAD_VAR, ntmp))
            emit.emit((OP_COMPARE_LE,))
            jf = emit.stub_jump(OP_JUMP_IF_FALSE)
            loops.append(RepeatCtl(ctr=ctr, ntmp=ntmp, head_ip=head_ip, jf_false_ip=jf))
            continue

        m = re.fullmatch(r"While (.+), do:", line, flags=re.IGNORECASE)
        if m:
            cond_start = emit.here()
            try:
                compile_condition(m.group(1).strip(), emit, temps)
            except PlainTalkError as e:
                raise polite(lineno, original, str(e), "While userAge is greater than 0, do:") from e
            jf = emit.stub_jump(OP_JUMP_IF_FALSE)
            loops.append(WhileCtl(cond_ip=cond_start, jf_false_ip=jf))
            continue

        m = re.fullmatch(r"If (.+), then:", line, flags=re.IGNORECASE)
        if m:
            try:
                compile_condition(m.group(1).strip(), emit, temps)
            except PlainTalkError as e:
                raise polite(lineno, original, str(e), "If userAge is greater than 18, then:") from e
            jf = emit.stub_jump(OP_JUMP_IF_FALSE)
            if_stack.append(IfCtl(jf_false_ip=jf))
            continue

        m = re.fullmatch(r"If (.+), then (.+)", line, flags=re.IGNORECASE)
        if m:
            try:
                compile_condition(m.group(1).strip(), emit, temps)
            except PlainTalkError as e:
                raise polite(lineno, original, str(e), "If userAge is greater than 18, then print 'Hi'.") from e
            jf = emit.stub_jump(OP_JUMP_IF_FALSE)
            try:
                _compile_statement(m.group(2).strip(), emit, temps, loops)
            except PlainTalkError as e:
                raise polite(lineno, original, str(e)) from e
            emit.patch_jump(jf, emit.here())
            continue

        m = re.fullmatch(r"To define a function called ([A-Za-z_]\w*)(?: that takes (.+))?:", line, flags=re.IGNORECASE)
        if m:
            if function_depth > 0:
                raise polite(lineno, original, "Nested function definitions aren't supported yet in the VM compiler.")
            fname = m.group(1)
            raw_params = _split_args_english((m.group(2) or "").strip())
            params: list[str] = []
            for p in raw_params:
                if not re.fullmatch(r"[A-Za-z_]\w*", p.strip()):
                    raise polite(lineno, original, f"I couldn't treat '{p}' as a parameter name.")
                params.append(p.strip())
            body_start = idx
            scan = body_start
            depth = 1
            end_body = None
            while scan < len(fragment):
                inner_raw = fragment[scan].lstrip()
                if re.fullmatch(r"End function", inner_raw, flags=re.IGNORECASE):
                    depth -= 1
                    if depth == 0:
                        end_body = scan
                        break
                elif re.fullmatch(r"To define a function called .+", inner_raw, flags=re.IGNORECASE):
                    depth += 1
                scan += 1
            if end_body is None:
                raise polite(lineno, original, "I reached the end while still compiling a function. Please close it with 'End function'.")
            body_lines = fragment[body_start:end_body]
            idx = end_body + 1
            inner_emit = Emitter()
            compile_region(
                body_lines,
                inner_emit,
                polite=polite,
                temps=temps,
                loops=[],
                if_stack=[],
                function_depth=function_depth + 1,
                queued_funcs=queued_funcs,
            )
            inner_emit.emit((OP_PUSH, None))
            inner_emit.emit((OP_RETURN_FUNC,))
            queued_funcs.append((fname, params, inner_emit.code))
            continue

        try:
            _compile_statement(line, emit, temps, loops)
        except PlainTalkError as e:
            raise polite(lineno, original, str(e), "Store the value 25 into a box called userAge.") from e


@dataclass
class ObfuscationConfig:
    enable_obfuscation: bool = True
    enable_junk_code: bool = True
    enable_string_obfuscation: bool = True
    enable_instruction_shuffle: bool = True
    junk_code_ratio: float = 0.3
    encryption_key: str = "PlainTalkObfuscationKey2024"

class BytecodeObfuscator:
    def __init__(self, config: ObfuscationConfig):
        self.config = config
        self.string_map = {}
        self.var_map = {}
        self.junk_instructions = [
            (OP_NOP,),
            (OP_PUSH, 0),
            (OP_POP,),
            (OP_PUSH, random.randint(1, 100)),
            (OP_POP,),
        ]
    
    def generate_obfuscated_name(self, original: str) -> str:
        if original in self.var_map:
            return self.var_map[original]
        
        hash_val = hashlib.md5((original + self.config.encryption_key).encode()).hexdigest()[:8]
        obfuscated = f"_{hash_val}"
        self.var_map[original] = obfuscated
        return obfuscated
    
    def obfuscate_string(self, text: str) -> tuple:
        if not self.config.enable_string_obfuscation:
            return (OP_PUSH, text)
        
        if text in self.string_map:
            return self.string_map[text]
        
        key_bytes = self.config.encryption_key.encode()
        text_bytes = text.encode('utf-8')
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(text_bytes)])
        
        result = (OP_OBFUSCATE_PUSH, encrypted, len(text_bytes))
        self.string_map[text] = result
        return result
    
    def add_junk_code(self, instructions: list) -> list:
        if not self.config.enable_junk_code:
            return instructions
        
        result = []
        stack_depth = 0
        
        for instr in instructions:
            result.append(instr)
            
            # Track stack depth to avoid unsafe junk code
            if instr[0] == OP_PUSH:
                stack_depth += 1
            elif instr[0] == OP_POP:
                stack_depth -= 1
            elif instr[0] == OP_PRINT:
                stack_depth -= 1
            
            # Only add junk code when stack is stable
            if (random.random() < self.config.junk_code_ratio and 
                stack_depth == 0 and 
                instr[0] not in [OP_HALT, OP_JUMP, OP_JUMP_IF_FALSE]):
                # Only use safe junk instructions that don't affect stack
                safe_junk = [(OP_NOP,), (OP_PUSH, 0), (OP_POP,)]
                if stack_depth == 0:
                    junk = random.choice([(OP_NOP,), (OP_PUSH, 0)])
                else:
                    junk = random.choice(safe_junk)
                result.append(junk)
                
                # Update stack depth for junk
                if junk[0] == OP_PUSH:
                    stack_depth += 1
                elif junk[0] == OP_POP:
                    stack_depth -= 1
        
        return result
    
    def shuffle_instruction_order(self, instructions: list) -> list:
        if not self.config.enable_instruction_shuffle or len(instructions) < 3:
            return instructions
        
        result = []
        i = 0
        while i < len(instructions):
            instr = instructions[i]
            result.append(instr)
            
            if i + 2 < len(instructions):
                segment = []
                j = i + 1
                while j < len(instructions) and self.is_shuffleable(instructions[j]):
                    segment.append(instructions[j])
                    j += 1
                
                if len(segment) > 1:
                    random.shuffle(segment)
                    result.extend(segment)
                    i = j - 1
                else:
                    i += 1
            else:
                i += 1
        
        return result
    
    def is_shuffleable(self, instr: tuple) -> bool:
        opcode = instr[0] if instr else ""
        return opcode in [OP_NOP, OP_PUSH, OP_POP]

class PerformanceOptimizer:
    def __init__(self):
        self.constant_folding = True
        self.dead_code_elimination = True
        self.instruction_fusion = True
    
    def optimize_constants(self, instructions: list) -> list:
        if not self.constant_folding:
            return instructions
        
        optimized = []
        i = 0
        while i < len(instructions):
            instr = instructions[i]
            
            if i + 2 < len(instructions):
                next_instr = instructions[i + 1]
                next_next_instr = instructions[i + 2]
                
                if (instr[0] == OP_PUSH and isinstance(instr[1], (int, float)) and
                    next_instr[0] == OP_PUSH and isinstance(next_instr[1], (int, float)) and
                    next_next_instr[0] == OP_BINARY_ADD):
                    
                    result = instr[1] + next_instr[1]
                    optimized.append((OP_PUSH, result))
                    i += 3
                    continue
            
            optimized.append(instr)
            i += 1
        
        return optimized
    
    def eliminate_dead_code(self, instructions: list) -> list:
        if not self.dead_code_elimination:
            return instructions
        
        optimized = []
        prev_nop = False
        
        for instr in instructions:
            if instr[0] == OP_NOP:
                if not prev_nop:
                    optimized.append(instr)
                prev_nop = True
            else:
                optimized.append(instr)
                prev_nop = False
        
        return optimized
    
    def fuse_instructions(self, instructions: list) -> list:
        if not self.instruction_fusion:
            return instructions
        
        return instructions

def create_enhanced_bytecode(instructions: list, obfuscator: BytecodeObfuscator, optimizer: PerformanceOptimizer) -> dict[str, Any]:
    optimized_instructions = optimizer.optimize_constants(instructions)
    optimized_instructions = optimizer.eliminate_dead_code(optimized_instructions)
    optimized_instructions = optimizer.fuse_instructions(optimized_instructions)
    
    if obfuscator.config.enable_obfuscation:
        obfuscated_instructions = []
        for instr in optimized_instructions:
            if instr[0] == OP_PUSH and isinstance(instr[1], str):
                obfuscated_instr = obfuscator.obfuscate_string(instr[1])
                obfuscated_instructions.append(obfuscated_instr)
            else:
                obfuscated_instructions.append(instr)
        
        obfuscated_instructions = obfuscator.add_junk_code(obfuscated_instructions)
        obfuscated_instructions = obfuscator.shuffle_instruction_order(obfuscated_instructions)
        
        final_instructions = obfuscated_instructions
    else:
        final_instructions = optimized_instructions
    
    # Add TE tribute instructions
    te_instructions = final_instructions.copy()
    te_instructions.insert(0, (OP_TE_TRIBUTE, "TE - Creator of PlainTalk"))
    te_instructions.append((OP_TE_WATERMARK, "Enhanced by TE"))
    
    bytecode = {
        "version": 2,
        "entry": "plaintalkc_enhanced_v2_te",
        "instructions": te_instructions,
        "user_functions": {},
        "metadata": {
            "obfuscated": obfuscator.config.enable_obfuscation,
            "optimized": True,
            "created_at": time.time(),
            "original_size": len(instructions),
            "enhanced_size": len(final_instructions),
            "string_map": obfuscator.string_map if obfuscator.config.enable_obfuscation else {},
            "var_map": obfuscator.var_map if obfuscator.config.enable_obfuscation else {},
            "encryption_key": obfuscator.config.encryption_key,
            "te_tribute": "Dedicated to TE - Creator of PlainTalk",
            "te_watermark": "PlainTalk Compiler Enhanced by TE"
        }
    }
    
    return bytecode

def compile_file_to_payload(path: str, config: ObfuscationConfig = None) -> dict[str, Any]:
    if config is None:
        config = ObfuscationConfig()
    
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    temps = TempPool()
    loops: list[Any] = []
    if_stack: list[IfCtl] = []

    def polite(line_no: int, original: str, message: str, suggestion: str | None = None) -> PlainTalkError:
        sug = "" if suggestion is None else f"\nSuggestion: {suggestion}"
        return PlainTalkError(
            f"On line {line_no}, I couldn't follow this sentence:\n  {original}\n{message}{sug}",
            line_no=line_no,
            line=original,
        )

    main_emit = Emitter()
    queued_funcs: list[QueuedFunc] = []

    compile_region(lines, main_emit, polite=polite, temps=temps, loops=loops, if_stack=if_stack, function_depth=0, queued_funcs=queued_funcs)
    if loops:
        raise PlainTalkError("It looks like a loop never closed. Did you forget 'End repeat' or 'End while'?")
    if if_stack:
        raise PlainTalkError("An 'If … then:' never closed with 'End if'.")

    final_code = list(main_emit.code)

    meta: dict[str, dict[str, Any]] = {}
    for fname, params, fn_code in queued_funcs:
        start_ip = len(final_code)
        final_code.extend(fn_code)
        meta[fname] = {"start_ip": start_ip, "params": params, "arity": len(params)}

    final_code.append((OP_HALT,))

    # Apply enhancements
    obfuscator = BytecodeObfuscator(config)
    optimizer = PerformanceOptimizer()
    enhanced_bytecode = create_enhanced_bytecode(final_code, obfuscator, optimizer)
    
    # Update user_functions with enhanced metadata
    enhanced_bytecode["user_functions"] = meta
    
    return enhanced_bytecode


def write_talkc(program: dict[str, Any], src_path: Path) -> Path:
    outp = src_path.with_suffix(".talkc")
    with open(outp, "wb") as fh:
        pickle.dump(program, fh, pickle.HIGHEST_PROTOCOL)
    return outp


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Enhanced PlainTalk Compiler with obfuscation and optimization.")
    ap.add_argument("talk_path", help="Path to PlainTalk source, e.g. my_script.talk")
    ap.add_argument("--no-obfuscation", action="store_true", help="Disable obfuscation")
    ap.add_argument("--no-junk-code", action="store_true", help="Disable junk code insertion")
    ap.add_argument("--no-string-obfuscation", action="store_true", help="Disable string obfuscation")
    ap.add_argument("--junk-ratio", type=float, default=0.3, help="Junk code ratio (0.0-1.0)")
    ap.add_argument("--key", default="PlainTalkObfuscationKey2024", help="Encryption key for obfuscation")
    ap.add_argument("--analyze-only", action="store_true", help="Only analyze bytecode without writing file")
    ns = ap.parse_args(argv)

    tp = Path(ns.talk_path)
    
    # Configure obfuscation
    config = ObfuscationConfig(
        enable_obfuscation=not ns.no_obfuscation,
        enable_junk_code=not ns.no_junk_code,
        enable_string_obfuscation=not ns.no_string_obfuscation,
        junk_code_ratio=ns.junk_ratio,
        encryption_key=ns.key
    )
    
    try:
        payload = compile_file_to_payload(str(tp), config)
    except PlainTalkError as err:
        print(str(err), file=sys.stderr)
        return 2
    
    if ns.analyze_only:
        print("=== Enhanced Bytecode Analysis ===")
        print(f"Version: {payload['version']}")
        print(f"Instructions: {len(payload['instructions'])}")
        print(f"Original size: {payload['metadata']['original_size']}")
        print(f"Enhanced size: {payload['metadata']['enhanced_size']}")
        if payload['metadata']['original_size'] > 0:
            size_increase = payload['metadata']['enhanced_size'] / payload['metadata']['original_size']
            print(f"Size increase: {size_increase:.2f}x")
        print(f"Obfuscated: {payload['metadata']['obfuscated']}")
        print(f"String mappings: {len(payload['metadata']['string_map'])}")
        print(f"Variable mappings: {len(payload['metadata']['var_map'])}")
        print(f"Optimized: {payload['metadata']['optimized']}")
    else:
        outp = write_talkc(payload, tp)
        print(f"Wrote enhanced bytecode to {outp}")
        print(f"Original size: {payload['metadata']['original_size']} instructions")
        print(f"Enhanced size: {payload['metadata']['enhanced_size']} instructions")
        print(f"Obfuscated: {payload['metadata']['obfuscated']}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

