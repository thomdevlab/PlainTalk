## PlainTalk (Plain English Programming) — v0.1 Specification

PlainTalk is a high-level language whose syntax is intended to be indistinguishable from ordinary English sentences. Programs are written as sentences, one per line. Blocks (like loops and function bodies) are introduced by sentences ending with a colon and are closed by explicit “End …” sentences.

PlainTalk avoids curly braces, semicolons, and operator symbols such as `&&`, `||`, `!=`. Punctuation like commas, apostrophes, and a trailing colon is allowed because it is common in written English.

### 1) Lexical rules

- **One sentence per line.** Empty lines are ignored.
- **Trailing period is optional** on non-block lines.
- **Strings** use single or double quotes: `'Hello'` or `"Hello"`.
- **Names** (boxes, functions, collections) are English-style identifiers: `userAge`, `total`, `fibonacciNumbers`.
- **Numbers**: integers and decimals supported: `25`, `3.14`.

### 2) Core concepts

- A **box** is a variable.
- A **collection** is a list.
- A **step block** is a group of lines under a header ending with a colon.

### 3) Statements and forms

#### 3.1 Variable assignment

Store the value <expression> into a box called <name>.

Examples:
- Store the value 25 into a box called userAge.
- Store the value the sum of 2 and 3 into a box called total.

#### 3.2 Printing

Print <expression>.

Examples:
- Print 'Hello, world'.
- Print userAge.

#### 3.3 Input

Ask the user for <prompt string> and store it into a box called <name>.

Examples:
- Ask the user for 'What is your name?' and store it into a box called name.

Notes:
- Input is stored as text. Convert with `the number value of <expression>` when needed.

#### 3.4 Conditionals

**Single-line form**

If <condition>, then <single statement>.

Example:
- If userAge is greater than 18, then print 'Access Granted'.

**Block form**

If <condition>, then:
  <statements>
End if.

Optional else:

If <condition>, then:
  <statements>
Otherwise:
  <statements>
End if.

Supported condition phrases:
- `<left> is greater than <right>`
- `<left> is less than <right>`
- `<left> is equal to <right>`
- `<left> is not equal to <right>`
- `<left> is at least <right>`
- `<left> is at most <right>`

#### 3.5 Loops

Repeat the following steps <N> times:
  <statements>
End repeat.

Optional counter name:

Repeat the following steps <N> times using a counter called <name>:
  <statements>
End repeat.

The counter starts at 1 and increases by 1 each iteration.

#### 3.6 Functions

To define a function called <name> that takes <param1>, <param2>, and <param3>:
  <statements>
End function.

With one parameter:
- To define a function called greet that takes name:

With zero parameters:
- To define a function called main:

Returning:

Return <expression>.

Calling:

Call <function name> with <arg1>, <arg2>, and <arg3> and store the result into a box called <name>.
Call <function name> with <args>.
Call <function name>.

#### 3.7 Collections (lists)

Create an empty collection called <name>.
Add <expression> to the collection called <name>.
Remove the last item from the collection called <name>.
Store the number of items in the collection called <name> into a box called <box>.
Store the item at position <expression> in the collection called <name> into a box called <box>.

Positions are 1-based in PlainTalk (position 1 is the first item).

### 4) Expressions (English arithmetic)

Expressions can be:
- A number: `10`
- A string: `'hello'`
- A box name: `userAge`
- A function call expression:
  - `the result of calling <name> with <args>`
- English math phrases:
  - `the sum of <a> and <b>`
  - `the difference of <a> and <b>`
  - `the product of <a> and <b>`
  - `the quotient of <a> and <b>`
  - `the remainder of <a> divided by <b>`
  - `the number value of <x>` (convert to number)

### 5) Errors (polite and actionable)

When a line is ambiguous or does not match the grammar, the transpiler reports:
- The line number and original sentence
- A polite explanation
- A suggestion with an example of a valid sentence

Example:
- “I couldn’t understand this sentence. I was expecting something like: ‘Store the value 10 into a box called total.’”

### 6) File extension and running

- Source files use the extension `.talk`.
- The reference implementation transpiles PlainTalk to Python and can optionally execute it.

