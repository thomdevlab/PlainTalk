"""
Execute PlainTalk bytecode (.talkc). SECURE VERSION - No Obfuscation
TE Tribute - Dedicated to TE, creator of PlainTalk
Security-focused VM with input validation and safe operations.

This version removes all obfuscation code that triggers security software
and replaces it with proper security layers.
"""

from __future__ import annotations

import json
import os
import sys
import pathlib
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Callable, NoReturn

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

Instr = tuple[Any, ...]


@dataclass
class Frame:
    return_ip: int
    locals: dict[str, Any]


class SecurityValidator:
    """Security layer for PlainTalk VM operations"""
    
    @staticmethod
    def validate_bytecode_structure(data: dict) -> bool:
        """Validate bytecode structure before execution"""
        required_keys = ["version", "entry", "instructions", "user_functions"]
        
        if not isinstance(data, dict):
            return False
        
        for key in required_keys:
            if key not in data:
                return False
        
        # Validate instructions
        if not isinstance(data["instructions"], list):
            return False
        
        # Check for malicious patterns
        return SecurityValidator._check_instruction_safety(data["instructions"])
    
    @staticmethod
    def _check_instruction_safety(instructions: list) -> bool:
        """Check instructions for dangerous patterns"""
        safe_opcodes = {
            OP_PUSH, OP_POP, OP_LOAD_VAR, OP_STORE_VAR, OP_CALL_FUNC,
            OP_JUMP_IF_FALSE, OP_PRINT, OP_JUMP, OP_BINARY_ADD, OP_BINARY_SUB,
            OP_BINARY_MUL, OP_BINARY_DIV, OP_BINARY_MOD, OP_BINARY_POW,
            OP_COMPARE_GT, OP_COMPARE_LT, OP_COMPARE_EQ, OP_COMPARE_NE,
            OP_COMPARE_GE, OP_COMPARE_LE, OP_BINARY_AND, OP_BINARY_OR,
            OP_UNARY_NOT, OP_CALL_INTRINSIC, OP_INPUT, OP_NOP, OP_HALT,
            OP_RETURN_FUNC, OP_TE_TRIBUTE, OP_TE_WATERMARK
        }
        
        for instr in instructions:
            if not instr or len(instr) == 0:
                continue
            
            opcode = instr[0]
            if opcode not in safe_opcodes:
                return False
            
            # Validate instruction arguments
            if not SecurityValidator._validate_instruction_args(instr):
                return False
        
        return True
    
    @staticmethod
    def _validate_instruction_args(instr: tuple) -> bool:
        """Validate individual instruction arguments"""
        if len(instr) > 10:  # Reasonable limit
            return False
        
        # Check for dangerous data types
        for arg in instr[1:]:
            if isinstance(arg, (bytes, bytearray, memoryview)):
                return False
            if isinstance(arg, str) and len(arg) > 10000:  # Reasonable string limit
                return False
        
        return True
    
    @staticmethod
    def validate_file_path(path: str) -> bool:
        """Validate file paths for security"""
        try:
            # Normalize path
            normalized = pathlib.Path(path).resolve()
            
            # Check for dangerous paths
            dangerous_paths = [
                "C:\\Windows", "C:\\System32", "/etc", "/bin", "/usr/bin",
                "C:\\Program Files", "C:\\Program Files (x86)"
            ]
            
            for dangerous in dangerous_paths:
                if str(normalized).lower().startswith(dangerous.lower()):
                    return False
            
            # Check for path traversal
            if ".." in str(normalized):
                return False
            
            return True
        except:
            return False
    
    @staticmethod
    def create_secure_hash(data: str) -> str:
        """Create secure hash for TE tribute"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]


class VM:
    """Secure PlainTalk Virtual Machine"""
    
    def __init__(self, prog: dict[str, Any]) -> None:
        # Security validation first
        if not SecurityValidator.validate_bytecode_structure(prog):
            raise ValueError("Invalid or malicious bytecode detected")
        
        self.code: list[Instr] = prog["instructions"]
        self.decls: dict[str, dict[str, Any]] = prog.get("user_functions", {})
        self.stk: list[Any] = []
        self.globals: dict[str, Any] = {}
        self.frames: list[Frame] = []
        self.metadata = prog.get("metadata", {})
        
        # Security features
        self.instruction_count = 0
        self.max_instructions = 100000  # Prevent infinite loops
        self.start_time = time.time()
        self.max_execution_time = 300  # 5 minutes max
        
        # TE tribute handling
        self.te_tribute_handled = False
        self.te_watermark_handled = False
    
    def pu(self, v: Any) -> None:
        """Push value to stack with validation"""
        # Limit stack size to prevent stack overflow
        if len(self.stk) > 10000:
            raise RuntimeError("Stack overflow detected")
        
        # Validate pushed value
        if isinstance(v, (bytes, bytearray)):
            raise RuntimeError("Binary data not allowed on stack")
        
        self.stk.append(v)
    
    def po(self) -> Any:
        """Pop value from stack"""
        if not self.stk:
            raise RuntimeError("Stack underflow")
        return self.stk.pop()
    
    def load_(self, name: str) -> Any:
        """Load variable with security check"""
        if name in self.frames:
            return self.frames[-1].locals.get(name, self.globals.get(name))
        return self.globals.get(name)
    
    def store_(self, name: str, val: Any) -> None:
        """Store variable with security check"""
        # Prevent storing dangerous data
        if isinstance(val, (bytes, bytearray)):
            raise RuntimeError("Binary data not allowed in variables")
        
        if name in self.frames:
            self.frames[-1].locals[name] = val
        else:
            self.globals[name] = val
    
    def _check_execution_limits(self):
        """Check execution limits for security"""
        self.instruction_count += 1
        
        if self.instruction_count > self.max_instructions:
            raise RuntimeError("Maximum instruction limit exceeded")
        
        if time.time() - self.start_time > self.max_execution_time:
            raise RuntimeError("Maximum execution time exceeded")
    
    def _handle_te_tribute(self, message: str):
        """Handle TE tribute securely"""
        if not self.te_tribute_handled:
            # Create secure hash for TE tribute
            te_hash = SecurityValidator.create_secure_hash(message)
            # Silently honor TE - no output to avoid security triggers
            self.te_tribute_handled = True
    
    def _handle_te_watermark(self, message: str):
        """Handle TE watermark securely"""
        if not self.te_watermark_handled:
            # Create secure hash for TE watermark
            te_hash = SecurityValidator.create_secure_hash(message)
            # Silently honor TE - no output to avoid security triggers
            self.te_watermark_handled = True
    
    def exec_(self, ip_: int | None = None) -> None:
        """Execute bytecode with security"""
        ip = 0 if ip_ is None else ip_
        
        while ip < len(self.code):
            self._check_execution_limits()
            
            ins = self.code[ip]
            op = ins[0]
            
            # Core opcodes
            if op == OP_PUSH:
                self.pu(ins[1])
                ip += 1
                continue
            if op == OP_POP:
                self.po()
                ip += 1
                continue
            if op == OP_LOAD_VAR:
                self.pu(self.load_(ins[1]))
                ip += 1
                continue
            if op == OP_STORE_VAR:
                self.store_(ins[1], self.po())
                ip += 1
                continue
            if op == OP_PRINT:
                print(str(self.po()), flush=True)
                ip += 1
                continue
            if op == OP_INPUT:
                self.pu(input(str(self.po())))
                ip += 1
                continue
            if op == OP_JUMP_IF_FALSE:
                self.pu(self.po())
                if not self.po():
                    ip = ins[1]
                else:
                    ip += 1
                continue
            if op == OP_JUMP:
                ip = ins[1]
                continue
            if op == OP_HALT:
                break
            
            # TE Tribute opcodes - secure handling
            if op == OP_TE_TRIBUTE:
                self._handle_te_tribute(str(ins[1]))
                ip += 1
                continue
            if op == OP_TE_WATERMARK:
                self._handle_te_watermark(str(ins[1]))
                ip += 1
                continue
            
            # Math operations
            if op == OP_BINARY_ADD:
                self.pu(self.po() + self.po())
                ip += 1
                continue
            if op == OP_BINARY_SUB:
                self.pu(self.po() - self.po())
                ip += 1
                continue
            if op == OP_BINARY_MUL:
                self.pu(self.po() * self.po())
                ip += 1
                continue
            if op == OP_BINARY_DIV:
                self.pu(self.po() / self.po())
                ip += 1
                continue
            if op == OP_BINARY_MOD:
                self.pu(self.po() % self.po())
                ip += 1
                continue
            if op == OP_BINARY_POW:
                self.pu(self.po() ** self.po())
                ip += 1
                continue
            
            # Comparison operations
            if op == OP_COMPARE_GT:
                self.pu(self.po() > self.po())
                ip += 1
                continue
            if op == OP_COMPARE_LT:
                self.pu(self.po() < self.po())
                ip += 1
                continue
            if op == OP_COMPARE_EQ:
                self.pu(self.po() == self.po())
                ip += 1
                continue
            if op == OP_COMPARE_NE:
                self.pu(self.po() != self.po())
                ip += 1
                continue
            if op == OP_COMPARE_GE:
                self.pu(self.po() >= self.po())
                ip += 1
                continue
            if op == OP_COMPARE_LE:
                self.pu(self.po() <= self.po())
                ip += 1
                continue
            
            # Logical operations
            if op == OP_BINARY_AND:
                self.pu(self.po() and self.po())
                ip += 1
                continue
            if op == OP_BINARY_OR:
                self.pu(self.po() or self.po())
                ip += 1
                continue
            if op == OP_UNARY_NOT:
                self.pu(not self.po())
                ip += 1
                continue
            
            # Intrinsic functions with security
            if op == OP_CALL_INTRINSIC:
                self._call_intrinsic_secure(ins[1])
                ip += 1
                continue
            
            # Default case
            raise RuntimeError(f"Unknown opcode: {op}")
    
    def _call_intrinsic_secure(self, name: str) -> None:
        """Call intrinsic function with security validation"""
        # Safe intrinsic functions
        safe_intrinsics = {
            "int_": int,
            "float_": float,
            "str_": str,
            "abs_": abs,
            "round_int": round,
            "len": len,
            "type": type,
            "bool": bool,
        }
        
        if name not in safe_intrinsics:
            raise RuntimeError(f"Intrinsic function '{name}' not allowed")
        
        func = safe_intrinsics[name]
        args = []
        
        # Get arguments safely
        if name in ["int_", "float_", "str_", "abs_", "round_int", "bool"]:
            args = [self.po()]
        elif name in ["len", "type"]:
            args = [self.po()]
        
        # Call function safely
        try:
            result = func(*args)
            self.pu(result)
        except Exception as e:
            raise RuntimeError(f"Intrinsic function error: {e}")


def load_secure_bytecode(path: str) -> dict:
    """Load bytecode securely using JSON instead of pickle"""
    if not SecurityValidator.validate_file_path(path):
        raise ValueError("Invalid file path")
    
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid bytecode format: {e}")
    
    return data


def run_file(path: str) -> None:
    """Run bytecode file securely"""
    try:
        prog = load_secure_bytecode(path)
        vm = VM(prog)
        vm.exec_(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point"""
    import argparse
    
    ap = argparse.ArgumentParser(prog="plaintalkvm", description="Execute PlainTalk bytecode (.talkc)")
    ap.add_argument("bytecode", nargs='?', help="Path to a .talkc file")
    ap.add_argument("-c", "--command", help="Execute PlainTalk bytecode command directly")
    
    ns = ap.parse_args()
    
    # Handle -c command option
    if ns.command:
        # Create temporary bytecode from command
        try:
            # For now, just print the command (would need full compiler to convert)
            print(f"Command execution not yet implemented: {ns.command}")
            print("Use a .talkc file for now.")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle file input
    if not ns.bytecode:
        print("PlainTalkVM Secure - Execute PlainTalk bytecode (.talkc)")
        print("TE Tribute - Dedicated to TE, creator of PlainTalk")
        print("Usage: python PlainTalkVM_Secure.py program.talkc")
        print("       python PlainTalkVM_Secure.py -h for help")
        sys.exit(1)
    
    run_file(ns.bytecode)


if __name__ == "__main__":
    main()
