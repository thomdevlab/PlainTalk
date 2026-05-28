"""Execute PlainTalk bytecode (.talkc). Enhanced with support for obfuscated bytecode and optimizations. Mirrors opcodes defined in PlainTalkCompiler.py."""

from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import pickle
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OP_PUSH, OP_POP = "PUSH", "POP"
OP_LOAD_VAR, OP_STORE_VAR = "LOAD_VAR", "STORE_VAR"
OP_CALL_FUNC, OP_JUMP_IF_FALSE, OP_JUMP = "CALL_FUNC", "JUMP_IF_FALSE", "JUMP"
OP_PRINT = "PRINT"
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

# Enhanced opcodes for obfuscation
OP_OBFUSCATE_PUSH, OP_OBFUSCATE_LOAD = "OBF_PUSH", "OBF_LOAD"
OP_DECRYPT_DATA, OP_JUNK_CODE = "DECRYPT", "JUNK"

# TE Tribute opcodes
OP_TE_TRIBUTE = "TE_TRIBUTE"
OP_TE_WATERMARK = "TE_WATERMARK"

Instr = tuple[Any, ...]


@dataclass
class Frame:
    return_ip: int
    locals: dict[str, Any]


class VM:
    def __init__(self, prog: dict[str, Any]) -> None:
        self.code: list[Instr] = prog["instructions"]
        self.decls: dict[str, dict[str, Any]] = prog.get("user_functions", {})
        self.stk: list[Any] = []
        self.globals: dict[str, Any] = {}
        self.frames: list[Frame] = []
        
        # Enhanced features for obfuscated bytecode
        self.metadata = prog.get("metadata", {})
        self.string_cache = {}
        self.var_cache = {}
        # Get encryption key from metadata or use default
        self.encryption_key = self.metadata.get("encryption_key", "PlainTalkObfuscationKey2024")
        
        # Performance counters
        self.instruction_count = 0
        self.junk_instructions_executed = 0
        
        # Initialize caches if obfuscated
        if self.metadata.get("obfuscated", False):
            self._initialize_caches()
    
    def _initialize_caches(self):
        """Initialize caches for obfuscated data"""
        string_map = self.metadata.get("string_map", {})
        
        # Pre-decrypt strings for performance
        for original, obfuscated_data in string_map.items():
            if len(obfuscated_data) >= 3 and obfuscated_data[0] == OP_OBFUSCATE_PUSH:
                encrypted_data, original_length = obfuscated_data[1], obfuscated_data[2]
                decrypted = self._decrypt_string(encrypted_data, original_length)
                self.string_cache[obfuscated_data] = decrypted
    
    def _decrypt_string(self, encrypted_data: bytes, original_length: int) -> str:
        """Decrypt obfuscated string"""
        key_bytes = self.encryption_key.encode()
        decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_data)])
        return decrypted.decode('utf-8')[:original_length]

    def pu(self, v: Any) -> None:
        self.stk.append(v)

    def po(self) -> Any:
        if not self.stk:
            raise RuntimeError("stack underflow")
        return self.stk.pop()

    def load_(self, n: str) -> Any:
        for f in reversed(self.frames):
            if n in f.locals:
                return f.locals[n]
        return self.globals[n]

    def store_(self, n: str, v: Any) -> None:
        if self.frames:
            self.frames[-1].locals[n] = v
        else:
            self.globals[n] = v

    def intrinsic(self, name: str) -> None:
        s = name
        if s == "float_":
            self.pu(float(self.po()))
            return
        if s == "int_":
            self.pu(int(float(self.po())))
            return
        if s == "str_":
            self.pu(str(self.po()))
            return
        if s == "bool_":
            self.pu(bool(self.po()))
            return
        if s == "sleep":
            time.sleep(float(self.po()))
            return
        if s == "clear_screen":
            os.system("cls" if os.name == "nt" else "clear")
            return
        if s == "halt0":
            sys.exit(0)
        if s == "halt_code":
            sys.exit(int(float(self.po())))
            return
        unary = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
                 "atan": math.atan, "log": math.log, "log10": math.log10, "exp": math.exp, "floor": math.floor, "ceil": math.ceil}
        if s in unary:
            self.pu(unary[s](float(self.po())))
            return
        if s == "log_base":
            b = float(self.po())
            x = float(self.po())
            self.pu(math.log(x, b))
            return
        if s == "abs_":
            self.pu(abs(float(self.po())))
            return
        if s == "binary_min":
            b, a = float(self.po()), float(self.po())
            self.pu(min(a, b))
            return
        if s == "binary_max":
            b, a = float(self.po()), float(self.po())
            self.pu(max(a, b))
            return
        if s == "sign":
            x = self.po()
            self.pu(0 if float(x) == 0 else (1 if float(x) > 0 else -1))
            return
        if s == "round_int":
            self.pu(int(round(float(self.po()))))
            return
        if s == "clamp3":
            hi = float(self.po())
            lo = float(self.po())
            mid = float(self.po())
            self.pu(min(hi, max(lo, mid)))
            return
        if s.startswith("now_"):
            now = dt.datetime.now()
            m = {"now_year": now.year, "now_month": now.month, "now_day": now.day,
                 "now_weekday": now.isoweekday(), "now_hour": now.hour, "now_minute": now.minute, "now_second": now.second}
            self.pu(m[s])
            return
        if s == "date_today":
            self.pu(dt.date.today())
            return
        if s == "datetime_now":
            self.pu(dt.datetime.now())
            return
        if s == "slen":
            self.pu(len(str(self.po())))
            return
        if s in {"upper", "lower", "strip", "lstrip", "rstrip"}:
            t = str(self.po())
            self.pu(getattr(t, s)())
            return
        if s == "sreplace":
            new, old, text = map(str, (self.po(), self.po(), self.po()))
            self.pu(text.replace(old, new))
            return
        if s == "ssplit":
            d, txt = map(str, (self.po(), self.po()))
            self.pu(txt.split(d))
            return
        if s == "sjoin":
            delim, seq = self.po(), self.po()
            self.pu(str(delim).join(str(x) for x in seq))
            return
        if s == "srepeat":
            n, txt = self.po(), self.po()
            self.pu(str(txt) * int(float(n)))
            return
        if s == "sfirst":
            n, txt = self.po(), self.po()
            self.pu(str(txt)[: int(float(n))])
            return
        if s == "slast":
            n, txt = self.po(), self.po()
            self.pu(str(txt)[-int(float(n)):])
            return
        if s == "sslice":
            ed, st, txt = float(self.po()), float(self.po()), self.po()
            txt = str(txt)
            self.pu(txt[int(st) - 1:int(ed)])
            return
        if s == "startswith":
            pre, hay = map(str, (self.po(), self.po()))
            self.pu(hay.startswith(pre))
            return
        if s == "endswith":
            suf, hay = map(str, (self.po(), self.po()))
            self.pu(hay.endswith(suf))
            return
        if s == "contains":
            needle, hay = map(str, (self.po(), self.po()))
            self.pu(needle in hay)
            return
        if s == "sfind":
            needle, hay = map(str, (self.po(), self.po()))
            self.pu(hay.find(needle))
            return
        if s == "uniform":
            b, a = float(self.po()), float(self.po())
            self.pu(random.uniform(a, b))
            return
        if s == "randint":
            b, a = int(float(self.po())), int(float(self.po()))
            self.pu(random.randint(a, b))
            return
        if s == "path_":
            self.pu(Path(str(self.po())))
            return
        if s == "file_exists":
            p = Path(str(self.po()))
            self.pu(p.exists())
            return
        if s == "file_write":
            fname = str(self.po())
            txt = str(self.po())
            Path(fname).write_text(txt, encoding="utf-8")
            return
        if s == "file_append":
            fname = str(self.po())
            txt = str(self.po())
            Path(fname).open("a", encoding="utf-8").write(txt)
            return
        if s == "file_read":
            p = Path(str(self.po()))
            self.pu(p.read_text(encoding="utf-8"))
            return
        if s == "file_delete":
            Path(str(self.po())).unlink(missing_ok=True)
            return
        if s == "mkdir":
            Path(str(self.po())).mkdir(parents=True, exist_ok=True)
            return
        # lists
        if s == "list_append":
            coll = self.po()
            item = self.po()
            coll.append(item)
            return
        if s == "list_insert":
            coll = self.po()
            idx = int(float(self.po())) - 1
            val = self.po()
            coll.insert(idx, val)
            return
        if s == "list_pop_last":
            self.po().pop()
            return
        if s == "list_pop_pos":
            lst = self.po()
            idx = int(float(self.po())) - 1
            lst.pop(idx)
            return
        if s == "list_clear":
            self.po().clear()
            return
        if s == "list_len_box":
            coll = self.po()
            self.pu(len(coll))
            return
        if s == "list_get_idx":
            coll = self.po()
            idx = int(float(self.po())) - 1
            self.pu(coll[idx])
            return
        if s == "list_set_idx":
            coll = self.po()
            idx = int(float(self.po())) - 1
            val = self.po()
            coll[idx] = val
            return
        raise RuntimeError(f"Unknown intrinsic '{name}'.")

    def exec_(self, ip_: int | None = None) -> None:
        ip = 0 if ip_ is None else ip_
        c = self.code
        while ip < len(c):
            ins = c[ip]
            op = ins[0]
            ip += 1
            self.instruction_count += 1
            if op == OP_NOP:
                self.junk_instructions_executed += 1
                continue
            if op == OP_HALT:
                return
            if op == OP_PUSH:
                self.pu(ins[1]); continue
            # Enhanced obfuscated opcodes
            if op == OP_OBFUSCATE_PUSH:
                encrypted_data, original_length = ins[1], ins[2]
                obfuscated_instr = (OP_OBFUSCATE_PUSH, encrypted_data, original_length)
                if obfuscated_instr in self.string_cache:
                    self.pu(self.string_cache[obfuscated_instr])
                else:
                    decrypted = self._decrypt_string(encrypted_data, original_length)
                    self.string_cache[obfuscated_instr] = decrypted
                    self.pu(decrypted)
                continue
            if op == OP_OBFUSCATE_LOAD:
                # Handle obfuscated variable loading (placeholder for future enhancement)
                self.pu(self.load_(ins[1])); continue
            if op == OP_DECRYPT_DATA:
                # Handle data decryption (placeholder for future enhancement)
                continue
            if op == OP_JUNK_CODE:
                self.junk_instructions_executed += 1
                continue
            # TE Tribute opcodes - ignore them during execution
            if op == OP_TE_TRIBUTE:
                # Silently honor TE tribute
                continue
            if op == OP_TE_WATERMARK:
                # Silently honor TE watermark
                continue
            if op == OP_POP:
                self.po(); continue
            if op == OP_LOAD_VAR:
                self.pu(self.load_(ins[1])); continue
            if op == OP_STORE_VAR:
                self.store_(ins[1], self.po()); continue
            if op == OP_PRINT:
                print(str(self.po()), flush=True); continue
            if op == OP_INPUT:
                self.pu(input(str(self.po()))); continue
            if op == OP_JUMP:
                ip = int(ins[1]); continue
            if op == OP_JUMP_IF_FALSE:
                t = int(ins[1]); 
                if not bool(self.po()):
                    ip = t
                continue
            if op == OP_BINARY_ADD:
                r = float(self.po()); l = float(self.po()); self.pu(l + r); continue
            if op == OP_BINARY_SUB:
                r = float(self.po()); l = float(self.po()); self.pu(l - r); continue
            if op == OP_BINARY_MUL:
                r = float(self.po()); l = float(self.po()); self.pu(l * r); continue
            if op == OP_BINARY_DIV:
                r = float(self.po()); l = float(self.po()); self.pu(l / r); continue
            if op == OP_BINARY_MOD:
                r = float(self.po()); l = float(self.po()); self.pu(l % r); continue
            if op == OP_BINARY_POW:
                r = float(self.po()); l = float(self.po()); self.pu(l ** r); continue
            if op == OP_COMPARE_GT:
                r = float(self.po()); l = float(self.po()); self.pu(l > r); continue
            if op == OP_COMPARE_LT:
                r = float(self.po()); l = float(self.po()); self.pu(l < r); continue
            if op == OP_COMPARE_EQ:
                r = self.po(); l = self.po(); self.pu(l == r); continue
            if op == OP_COMPARE_NE:
                r = self.po(); l = self.po(); self.pu(l != r); continue
            if op == OP_COMPARE_GE:
                r = float(self.po()); l = float(self.po()); self.pu(l >= r); continue
            if op == OP_COMPARE_LE:
                r = float(self.po()); l = float(self.po()); self.pu(l <= r); continue
            if op == OP_BINARY_AND:
                r = bool(self.po()); l = bool(self.po()); self.pu(l and r); continue
            if op == OP_BINARY_OR:
                r = bool(self.po()); l = bool(self.po()); self.pu(l or r); continue
            if op == OP_UNARY_NOT:
                self.pu(not bool(self.po())); continue
            if op == OP_CALL_INTRINSIC:
                self.intrinsic(str(ins[1])); continue
            if op == OP_CALL_FUNC:
                fname = ins[1]; arity = int(ins[2])
                argv = list(reversed([self.po() for _ in range(arity)]))
                fn = self.decls[fname]
                params = fn["params"]
                loc = dict(zip(params, argv, strict=True))
                self.frames.append(Frame(return_ip=ip, locals=loc))
                ip = int(fn["start_ip"])
                continue
            if op == OP_RETURN_FUNC:
                ret = self.po()
                fr = self.frames.pop()
                ip = fr.return_ip
                self.pu(ret)
                continue
            raise RuntimeError(f"Unhandled opcode '{op}'.")


def run_file(path: str) -> None:
    with open(path, "rb") as fh:
        prog = pickle.load(fh)
    vm = VM(prog)
    vm.exec_(0)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run PlainTalk bytecode (.talkc)")
    ap.add_argument("talkc_path")
    ns = ap.parse_args(argv)
    try:
        run_file(ns.talkc_path)
    except Exception as exc:
        print(f"The VM halted early: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))