# PlainTalk

## About PlainTalk

PlainTalk is a high-level programming language that uses plain English syntax. Write programs that read like natural sentences!

## Quick Start

### Installation (Pre-built)
1. Download prebuilt executables from 'https://github.com/thomdevlab/PlainTalk/releases/tag/prebuiltb1'
2. Extract PlainTalk.zip
3. Add `PlainTalk` to your system PATH
4. Run: `plaintalk your_program.talk`

### Installation (Source)
1. Clone from GitHub: https://github.com/thomdevlab/PlainTalk
2. Compile using PyInstaller: `python -m PyInstaller PlainTalkCompiler.py --onefile`
3. Add compiled executables to PATH

## Usage Examples

### Hello World
```plaintext
Print 'Hello, world'.
```

### Variables
```plaintext
Store the value 25 into a box called userAge.
Print userAge.
```

### Loops
```plaintext
Repeat the following steps 5 times:
  Print 'Hello!'
End repeat.
```

### Functions
```plaintext
To define a function called greet that takes name:
  Print 'Hello, ' + name.
End function.

Call greet with 'World'.
```

## Available Commands

- `plaintalk` - Core interpreter
- `PlainTalkCompiler` - Compile .talk to .talkc
- `PlainTalkVM` - Virtual machine for execution
- `Talk2Exe` - Convert .talk to standalone .exe

## File Structure

**Note:** All folders listed below are for developers only. Users only receive .py files or .exe files from GitHub releases.

- `src/` - Source code files
- `examples/` - Sample PlainTalk programs
- `download/dist/` - Pre-built executables
- `docs/` - Documentation and specifications
- `tools/` - Utility scripts
- `build_artifacts/` - Build outputs

**Distribution:** Users download .py files or .exe files directly from GitHub releases.

## Language Features

- Plain English syntax
- Variables (boxes)
- Collections (lists)
- Functions and procedures
- Loops and conditionals
- Input/output operations
- Mathematical expressions

## Getting Help

- Check `examples/` folder for sample programs
- Read `PLAINTALK_SPEC.md` for complete language specification
- Visit GitHub repository for issues and updates
