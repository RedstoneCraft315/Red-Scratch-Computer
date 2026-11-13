# Compiler 2

This folder contains a standalone, easier-to-use GUI for the Red's 16-bit assembly compiler.

## Run

On Windows, double-click `Compiler 2.pyw`. It uses Python's built-in Tkinter; no extra packages are needed.

## Use

- Edit assembly in the left pane. The editor shows line numbers and highlights instructions, labels, comments, and compiler errors.
- Select **Compile** or press **Ctrl+U**. The right pane shows Logisim's `v3.0 hex words addressed` format when compilation succeeds, or line-specific errors otherwise.
- Use **Open**, **Save**, and **Save output** to manage source and compiled files. Unsaved source edits are confirmed before replacing or closing a document.
- Use **Insert files** to add assembly/text at the caret or convert compatible `.hex`/binary machine-code files into readable assembly or raw-data comments.
- Use **Help > Instruction reference** to look up each instruction's opcode and operand count.
- Numbers use the existing hexadecimal convention (`01`, `0x10`, or `10h`). Labels can be used as jump targets. For compatibility with the earlier compiler, a numeric `JMP` or `BEQ` operand smaller than the source line count is treated as a zero-based source-line target and rebased to its instruction address.
- **Edit > Insert example** inserts the starter program at the caret. **Toggle theme** switches between dark and light modes.

The assembler core is in `assembler.py`; its focused regression tests are in `test_assembler.py`. Run them from this folder with:

```powershell
python -m unittest -v
```
