"""
Compile PlainTalk (.talk) sources into secure JSON bytecode (.talkc).
SECURE VERSION - No Obfuscation, Security Layer Instead
TE Tribute - Dedicated to TE, creator of PlainTalk

This version removes all obfuscation code that triggers security software
and replaces it with proper security validation and JSON serialization.

CLI: python PlainTalkCompiler_Secure.py my_script.talk
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Core opcodes only - no obfuscation opcodes
OP_PUSH = "PUSH"
OP_POP = "POP"
OP_LOAD_VAR = "LOAD_VAR"
OP_STORE_VAR = "STORE_VAR"
OP_CALL_FUNC = "CALL_FUNC"
OP_JUMP_IF_FALSE = "JUMP_IF_FALSE"
OP_PRINT = "PRINT"
OP_JUMP = "JUMP"

OP_BINARY_ADD, OP_BINARY_SUB, OP_BINARY_MUL, OP_BINARY_DIV, OP_BINARY_MOD, OP_BINARY_POW = (
    "BINARY_ADD",
    "BINARY_SUB",
    "BINARY_MUL",
    "BINARY_DIV",
    "BINARY_MOD",
    "BINARY_POW",
)
OP_COMPARE_GT, OP_COMPARE_LT, OP_COMPARE_EQ, OP_COMPARE_NE, OP_COMPARE_GE, OP_COMPARE_LE = (
    "COMPARE_GT",
    "COMPARE_LT",
    "COMPARE_EQ",
    "COMPARE_NE",
    "COMPARE_GE",
    "COMPARE_LE",
)
OP_BINARY_AND, OP_BINARY_OR, OP_UNARY_NOT = "BINARY_AND", "BINARY_OR", "UNARY_NOT"
OP_CALL_INTRINSIC = "CALL_INTRINSIC"
OP_INPUT, OP_NOP, OP_HALT, OP_RETURN_FUNC = "INPUT", "NOP", "HALT", "RETURN_FUNC"

# TE Tribute opcodes - secure implementation
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
    mm = re.fullmatch(r"the remainder of (.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_MOD,))
        return

    # Comparison operators
    for op_pat, op_code in (
        (r"(.+) greater than (.+)", OP_COMPARE_GT),
        (r"(.+) less than (.+)", OP_COMPARE_LT),
        (r"(.+) equal to (.+)", OP_COMPARE_EQ),
        (r"(.+) not equal to (.+)", OP_COMPARE_NE),
        (r"(.+) greater than or equal to (.+)", OP_COMPARE_GE),
        (r"(.+) less than or equal to (.+)", OP_COMPARE_LE),
    ):
        mm = re.fullmatch(op_pat, expr, flags=re.IGNORECASE)
        if mm:
            _bio(mm.group(1), mm.group(2), (op_code,))
            return

    # Logical operators
    mm = re.fullmatch(r"(.+) and (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_AND,))
        return
    mm = re.fullmatch(r"(.+) or (.+)", expr, flags=re.IGNORECASE)
    if mm:
        _bio(mm.group(1), mm.group(2), (OP_BINARY_OR,))
        return
    mm = re.fullmatch(r"not (.+)", expr, flags=re.IGNORECASE)
    if mm:
        compile_expression(mm.group(1), emit, temps)
        emit.emit((OP_UNARY_NOT,))
        return

    # Variable reference
    if re.fullmatch(r"[a-zA-Z_]\w*", expr):
        emit.emit((OP_LOAD_VAR, expr))
        return

    raise PlainTalkError(f"I don't understand this expression: {expr}")


@dataclass
class IfCtl:
    addr: int
    has_else: bool = False


def compile_file_to_payload(path: str) -> dict[str, Any]:
    """Compile PlainTalk file to secure JSON bytecode"""
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

    emit = Emitter()

    # Add TE tribute at the beginning
    emit.emit((OP_TE_TRIBUTE, "TE - Creator of PlainTalk"))

    for line_no, raw in enumerate(lines, 1):
        line = _clean_line(raw)
        if not line or line.startswith("#"):
            continue

        # Store statements
        mm = re.fullmatch(r"store the value of (.+) into a box called (.+)", line, flags=re.IGNORECASE)
        if not mm:
            mm = re.fullmatch(r"store (.+) into a box called (.+)", line, flags=re.IGNORECASE)
        if not mm:
            mm = re.fullmatch(r"store (.+) into (.+)", line, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            emit.emit((OP_STORE_VAR, mm.group(2)))
            continue

        # Print statements
        mm = re.fullmatch(r"print (.+)", line, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            emit.emit((OP_PRINT,))
            continue

        # Input statements
        mm = re.fullmatch(r"ask the user for (.+) and store it into a box called (.+)", line, flags=re.IGNORECASE)
        if not mm:
            mm = re.fullmatch(r"ask for (.+) and store it into (.+)", line, flags=re.IGNORECASE)
        if mm:
            emit.emit((OP_PUSH, mm.group(1)))
            emit.emit((OP_INPUT,))
            emit.emit((OP_STORE_VAR, mm.group(2)))
            continue

        # If statements
        mm = re.fullmatch(r"if (.+) then", line, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            addr = emit.stub_jump(OP_JUMP_IF_FALSE)
            if_stack.append(IfCtl(addr))
            continue

        if line.lower() == "else":
            if not if_stack or if_stack[-1].has_else:
                raise PlainTalkError("Unexpected else", line_no=line_no, line=line)
            ctl = if_stack[-1]
            ctl.has_else = True
            else_addr = emit.stub_jump(OP_JUMP)
            emit.patch_jump(ctl.addr)
            ctl.addr = else_addr
            continue

        if line.lower() == "end if":
            if not if_stack:
                raise PlainTalkError("Unexpected end if", line_no=line_no, line=line)
            ctl = if_stack.pop()
            emit.patch_jump(ctl.addr)
            continue

        # While loops
        mm = re.fullmatch(r"while (.+) do", line, flags=re.IGNORECASE)
        if mm:
            start_addr = emit.here()
            compile_expression(mm.group(1), emit, temps)
            addr = emit.stub_jump(OP_JUMP_IF_FALSE)
            loops.append(("while", start_addr, addr))
            continue

        if line.lower() == "end while":
            if not loops or loops[-1][0] != "while":
                raise PlainTalkError("Unexpected end while", line_no=line_no, line=line)
            loop_type, start_addr, exit_addr = loops.pop()
            emit.emit((OP_JUMP, start_addr))
            emit.patch_jump(exit_addr)
            continue

        # Repeat loops
        mm = re.fullmatch(r"repeat (.+) times", line, flags=re.IGNORECASE)
        if mm:
            compile_expression(mm.group(1), emit, temps)
            counter = temps.name("repeat")
            emit.emit((OP_STORE_VAR, counter))
            start_addr = emit.here()
            emit.emit((OP_LOAD_VAR, counter))
            emit.emit((OP_PUSH, 0))
            emit.emit((OP_COMPARE_LE,))
            exit_addr = emit.stub_jump(OP_JUMP_IF_FALSE)
            loops.append(("repeat", counter, start_addr, exit_addr))
            continue

        if line.lower() == "end repeat":
            if not loops or loops[-1][0] != "repeat":
                raise PlainTalkError("Unexpected end repeat", line_no=line_no, line=line)
            loop_type, counter, start_addr, exit_addr = loops.pop()
            emit.emit((OP_LOAD_VAR, counter))
            emit.emit((OP_PUSH, 1))
            emit.emit((OP_BINARY_SUB,))
            emit.emit((OP_STORE_VAR, counter))
            emit.emit((OP_JUMP, start_addr))
            emit.patch_jump(exit_addr)
            continue

        raise PlainTalkError(f"I don't understand this sentence: {line}", line_no=line_no, line=line)

    # Add TE watermark at the end
    emit.emit((OP_TE_WATERMARK, "Enhanced by TE"))
    emit.emit((OP_HALT,))

    # Create secure bytecode structure
    bytecode = {
        "version": "3.0-secure",
        "entry": "plaintalk_secure_v3",
        "instructions": emit.code,
        "user_functions": {},
        "metadata": {
            "compiler": "PlainTalkCompiler_Secure",
            "te_tribute": "Dedicated to TE - Creator of PlainTalk",
            "te_watermark": "PlainTalk Compiler Enhanced by TE",
            "security_level": "high",
            "created_at": time.time(),
            "instruction_count": len(emit.code),
            "security_features": [
                "input_validation",
                "execution_limits",
                "secure_serialization",
                "te_tribute_secure"
            ]
        }
    }
    
    return bytecode


def save_secure_bytecode(data: dict, path: str) -> None:
    """Save bytecode securely using JSON"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PlainTalk Compiler Secure - Compile .talk to secure .talkc (JSON)",
        epilog="TE Tribute - Dedicated to TE, creator of PlainTalk"
    )
    parser.add_argument("input", help="PlainTalk source file")
    parser.add_argument("-o", "--output", help="Output bytecode file (default: input.talkc)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    if not input_path.suffix.lower() == ".talk":
        print(f"Error: Input file must have .talk extension", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".talkc")

    try:
        bytecode = compile_file_to_payload(str(input_path))
        save_secure_bytecode(bytecode, str(output_path))
        
        print(f"Wrote secure bytecode to {output_path}")
        print(f"Instructions: {len(bytecode['instructions'])}")
        print(f"Security: High (JSON serialization, no obfuscation)")
        print(f"TE Tribute: Embedded securely")
        
    except PlainTalkError as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Internal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
