"""A more approachable desktop editor for Red's 16-bit assembly compiler."""

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from assembler import (
    MNEMONICS,
    OPCODES,
    OPERAND_COUNTS,
    assemble,
    source_from_inserted_file,
)


APP_NAME = "Red's Computer Compiler 2"
SAMPLE_SOURCE = (
    "start:\n"
    "    LDA 01    ; load a value into A\n"
    "    LDB 02    ; load a value into B\n"
    "    ADD\n"
    "    JMP start\n"
)

PALETTES = {
    "Dark": {
        "window": "#171b24",
        "panel": "#202633",
        "editor": "#11151c",
        "foreground": "#e6edf3",
        "muted": "#9ba8ba",
        "accent": "#4f8cff",
        "selection": "#31527d",
        "gutter": "#191f29",
        "border": "#303a4b",
        "comment": "#7f9d76",
        "keyword": "#76b7ff",
        "label": "#e7c675",
        "error": "#ff817b",
        "error_bg": "#512b32",
    },
    "Light": {
        "window": "#f2f4f8",
        "panel": "#ffffff",
        "editor": "#ffffff",
        "foreground": "#202938",
        "muted": "#66758a",
        "accent": "#2468d8",
        "selection": "#c8ddff",
        "gutter": "#f1f4f8",
        "border": "#d6dce5",
        "comment": "#527c3c",
        "keyword": "#175fc0",
        "label": "#8a5a00",
        "error": "#a82025",
        "error_bg": "#ffd9dc",
    },
}


class CodeEditor(ttk.Frame):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.on_change = on_change
        self.palette = PALETTES["Dark"]
        self._highlight_pending = False

        editor_frame = ttk.Frame(self)
        editor_frame.pack(fill="both", expand=True)
        self.gutter = tk.Canvas(editor_frame, width=48, highlightthickness=0, borderwidth=0)
        self.gutter.pack(side="left", fill="y")
        self.text = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            autoseparators=True,
            maxundo=-1,
            borderwidth=0,
            padx=10,
            pady=8,
            font=("Consolas", 11),
            tabs=("32p",),
        )
        self.text.pack(side="left", fill="both", expand=True)

        self.vertical = ttk.Scrollbar(editor_frame, orient="vertical", command=self.text.yview)
        self.vertical.pack(side="right", fill="y")
        self.horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.horizontal.pack(fill="x")
        self.text.configure(yscrollcommand=self._on_scroll, xscrollcommand=self.horizontal.set)

        self.text.tag_configure("comment")
        self.text.tag_configure("mnemonic")
        self.text.tag_configure("label")
        self.text.tag_configure("diagnostic")
        self.text.tag_raise("diagnostic")
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", self._refresh_gutter)
        self.text.bind("<ButtonRelease-1>", self._refresh_gutter)
        self.text.bind("<Configure>", self._refresh_gutter)

    def _on_scroll(self, first, last):
        self.vertical.set(first, last)
        self._refresh_gutter()

    def _refresh_gutter(self, _event=None):
        if not self.winfo_exists():
            return
        self.gutter.delete("all")
        try:
            first = int(self.text.index("@0,0").split(".")[0])
            last = int(self.text.index("@0,1000000").split(".")[0]) + 1
        except tk.TclError:
            return
        for line in range(first, last + 1):
            info = self.text.dlineinfo(f"{line}.0")
            if info is None:
                continue
            self.gutter.create_text(
                40,
                info[1],
                anchor="ne",
                text=str(line),
                fill=self.palette["muted"],
                font=("Consolas", 10),
            )

    def _on_modified(self, _event=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.on_change()
        if not self._highlight_pending:
            self._highlight_pending = True
            self.after_idle(self._highlight)

    def _highlight(self):
        self._highlight_pending = False
        source = self.text.get("1.0", "end-1c")
        for tag in ("comment", "mnemonic", "label"):
            self.text.tag_remove(tag, "1.0", "end")
        for match in re.finditer(r";[^\n]*", source):
            self._add_range("comment", match.start(), match.end())
        mnemonic_pattern = r"(?i)\b(?:" + "|".join(MNEMONICS) + r")\b"
        for match in re.finditer(mnemonic_pattern, source):
            self._add_range("mnemonic", match.start(), match.end())
        for match in re.finditer(r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*:", source):
            self._add_range("label", match.start(), match.end())
        self.text.tag_raise("label")
        self.text.tag_raise("mnemonic")
        self.text.tag_raise("comment")
        self.text.tag_raise("diagnostic")
        self._refresh_gutter()

    def _add_range(self, tag, start, end):
        self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

    def clear_diagnostics(self):
        self.text.tag_remove("diagnostic", "1.0", "end")

    def mark_diagnostics(self, diagnostics):
        self.clear_diagnostics()
        for diagnostic in diagnostics:
            self.text.tag_add(
                "diagnostic",
                f"{diagnostic.line}.0",
                f"{diagnostic.line}.end",
            )
        self.text.tag_raise("diagnostic")

    def set_palette(self, palette):
        self.palette = palette
        self.configure(style="Editor.TFrame")
        self.gutter.configure(bg=palette["gutter"])
        self.text.configure(
            bg=palette["editor"],
            fg=palette["foreground"],
            insertbackground=palette["foreground"],
            selectbackground=palette["selection"],
            selectforeground=palette["foreground"],
        )
        self.text.tag_configure("comment", foreground=palette["comment"])
        self.text.tag_configure("mnemonic", foreground=palette["keyword"])
        self.text.tag_configure("label", foreground=palette["label"])
        self.text.tag_configure(
            "diagnostic",
            foreground=palette["error"],
            background=palette["error_bg"],
        )
        self._refresh_gutter()

    def set_source(self, source):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", source)
        self.text.edit_modified(False)
        self._highlight()


class CompilerApp:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        self.dirty = False
        self.theme_name = "Dark"
        self.last_result = None
        self.status_var = tk.StringVar(value="Ready")
        self.cursor_var = tk.StringVar(value="Line 1, Column 1")
        self._build_ui()
        self._apply_theme()
        self.editor.set_source(SAMPLE_SOURCE)
        self.editor.text.edit_modified(False)
        self._update_title()
        self.editor.text.bind("<KeyRelease>", self._update_cursor, add=True)
        self.editor.text.bind("<ButtonRelease-1>", self._update_cursor, add=True)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _build_ui(self):
        self.root.title(APP_NAME)
        self.root.geometry("1180x760")
        self.root.minsize(860, 560)
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        self.container = ttk.Frame(self.root, padding=12)
        self.container.pack(fill="both", expand=True)

        heading = ttk.Frame(self.container)
        heading.pack(fill="x", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Assembly workspace", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            heading,
            text="Edit source, compile, then save the Logisim-ready hex output.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        toolbar = ttk.Frame(self.container)
        toolbar.pack(fill="x", pady=(0, 10))
        self.compile_button = ttk.Button(
            toolbar,
            text="Compile  Ctrl+U",
            command=self.compile_source,
            style="Accent.TButton",
        )
        self.compile_button.pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="New", command=self.new_file).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Insert files", command=self.insert_files).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Copy output", command=self.copy_output).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Save output", command=self.save_output).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Toggle theme", command=self.toggle_theme).pack(side="right")

        self.panes = ttk.Panedwindow(self.container, orient="horizontal")
        self.panes.pack(fill="both", expand=True)
        source_panel = ttk.Frame(self.panes, padding=(0, 0, 6, 0))
        output_panel = ttk.Frame(self.panes, padding=(6, 0, 0, 0))
        self.panes.add(source_panel, weight=3)
        self.panes.add(output_panel, weight=2)

        source_heading = ttk.Frame(source_panel)
        source_heading.pack(fill="x", pady=(0, 6))
        ttk.Label(source_heading, text="Source", style="PaneTitle.TLabel").pack(side="left")
        ttk.Label(source_heading, text="  ; comments start with semicolon", style="Muted.TLabel").pack(
            side="left"
        )
        self.editor = CodeEditor(source_panel, self._source_changed)
        self.editor.pack(fill="both", expand=True)

        output_heading = ttk.Frame(output_panel)
        output_heading.pack(fill="x", pady=(0, 6))
        ttk.Label(output_heading, text="Compiled output", style="PaneTitle.TLabel").pack(side="left")
        output_frame = ttk.Frame(output_panel)
        output_frame.pack(fill="both", expand=True)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output = tk.Text(
            output_frame,
            wrap="none",
            borderwidth=0,
            padx=10,
            pady=8,
            font=("Consolas", 11),
            state="disabled",
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        self.output_scroll = ttk.Scrollbar(
            output_frame,
            orient="vertical",
            command=self.output.yview,
        )
        self.output_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=self.output_scroll.set)
        self.output_x_scroll = ttk.Scrollbar(
            output_frame,
            orient="horizontal",
            command=self.output.xview,
        )
        self.output_x_scroll.grid(row=1, column=0, sticky="ew")
        self.output.configure(xscrollcommand=self.output_x_scroll.set)

        footer = ttk.Frame(self.container)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.cursor_var, style="Muted.TLabel").pack(side="right")

        self._build_menu()
        self.root.bind_all("<Control-u>", lambda _event: self._shortcut(self.compile_source))
        self.root.bind_all("<Control-U>", lambda _event: self._shortcut(self.compile_source))
        self.root.bind_all("<Control-s>", lambda _event: self._shortcut(self.save_file))
        self.root.bind_all("<Control-S>", lambda _event: self._shortcut(self.save_file))
        self.root.bind_all("<Control-Shift-S>", lambda _event: self._shortcut(self.save_file_as))
        self.root.bind_all("<Control-z>", lambda _event: self._shortcut(self._undo))
        self.root.bind_all("<Control-Z>", lambda _event: self._shortcut(self._undo))
        self.root.bind_all("<Control-y>", lambda _event: self._shortcut(self._redo))
        self.root.bind_all("<Control-Y>", lambda _event: self._shortcut(self._redo))
        self.root.bind_all("<Control-Shift-Z>", lambda _event: self._shortcut(self._redo))
        self.root.bind_all("<Control-o>", lambda _event: self._shortcut(self.open_file))
        self.root.bind_all("<Control-O>", lambda _event: self._shortcut(self.open_file))
        self.root.bind_all("<Control-n>", lambda _event: self._shortcut(self.new_file))
        self.root.bind_all("<Control-N>", lambda _event: self._shortcut(self.new_file))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Insert files...", command=self.insert_files)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save as...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self._undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self._redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Insert example", command=self.insert_example)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        build_menu = tk.Menu(menubar, tearoff=False)
        build_menu.add_command(label="Compile", accelerator="Ctrl+U", command=self.compile_source)
        build_menu.add_command(label="Copy output", command=self.copy_output)
        build_menu.add_command(label="Save output...", command=self.save_output)
        menubar.add_cascade(label="Build", menu=build_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Instruction reference", command=self.show_reference)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.configure(menu=menubar)

    def _apply_theme(self):
        palette = PALETTES[self.theme_name]
        self.root.configure(bg=palette["window"])
        self.style.configure("TFrame", background=palette["window"])
        self.style.configure("Editor.TFrame", background=palette["editor"])
        self.style.configure(
            "Treeview",
            background=palette["editor"],
            fieldbackground=palette["editor"],
            foreground=palette["foreground"],
        )
        self.style.configure(
            "Treeview.Heading",
            background=palette["panel"],
            foreground=palette["foreground"],
        )
        self.style.configure("TLabel", background=palette["window"], foreground=palette["foreground"])
        self.style.configure(
            "Heading.TLabel",
            background=palette["window"],
            foreground=palette["foreground"],
            font=("Segoe UI", 18, "bold"),
        )
        self.style.configure(
            "PaneTitle.TLabel",
            background=palette["window"],
            foreground=palette["foreground"],
            font=("Segoe UI", 11, "bold"),
        )
        self.style.configure("Muted.TLabel", background=palette["window"], foreground=palette["muted"])
        self.style.configure(
            "TButton",
            background=palette["panel"],
            foreground=palette["foreground"],
            bordercolor=palette["border"],
            padding=(10, 6),
        )
        self.style.map(
            "TButton",
            background=[("active", palette["border"]), ("pressed", palette["border"])],
        )
        self.style.configure(
            "Accent.TButton",
            background=palette["accent"],
            foreground="#ffffff",
            padding=(12, 6),
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map("Accent.TButton", background=[("active", palette["accent"])])
        self.style.configure(
            "TPanedwindow",
            background=palette["border"],
            sashwidth=5,
        )
        self.editor.set_palette(palette)
        self.output.configure(
            bg=palette["editor"],
            fg=palette["foreground"],
            insertbackground=palette["foreground"],
            selectbackground=palette["selection"],
            selectforeground=palette["foreground"],
        )

    def toggle_theme(self):
        self.theme_name = "Light" if self.theme_name == "Dark" else "Dark"
        self._apply_theme()

    def _source_changed(self):
        self.dirty = True
        self._update_title()

    def _update_title(self):
        name = os.path.basename(self.file_path) if self.file_path else "Untitled"
        marker = "*" if self.dirty else ""
        self.root.title(f"{marker}{name} - {APP_NAME}")

    def _update_cursor(self, _event=None):
        line, column = self.editor.text.index("insert").split(".")
        self.cursor_var.set(f"Line {line}, Column {int(column) + 1}")

    def _shortcut(self, callback):
        callback()
        return "break"

    def _undo(self):
        try:
            self.editor.text.edit_undo()
        except tk.TclError:
            self.status_var.set("Nothing to undo")

    def _redo(self):
        try:
            self.editor.text.edit_redo()
        except tk.TclError:
            self.status_var.set("Nothing to redo")

    def _confirm_discard(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved changes",
            "Save your changes before continuing?",
            parent=self.root,
        )
        if answer is None:
            return False
        if answer:
            return self.save_file()
        return True

    def new_file(self):
        if not self._confirm_discard():
            return
        self.editor.set_source("")
        self.file_path = None
        self.dirty = False
        self.last_result = None
        self._set_output("")
        self.editor.clear_diagnostics()
        self._update_title()
        self.status_var.set("New file")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open assembly source",
            filetypes=[
                ("Assembly and text files", "*.redstone *.txt *.asm"),
                ("All files", "*.*"),
            ],
        )
        if not path or not self._confirm_discard():
            return
        try:
            with open(path, "r", encoding="utf-8") as source_file:
                source = source_file.read()
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Open failed", str(error), parent=self.root)
            return
        self.editor.set_source(source)
        self.file_path = path
        self.dirty = False
        self.last_result = None
        self._set_output("")
        self.editor.clear_diagnostics()
        self._update_title()
        self.status_var.set(f"Opened {os.path.basename(path)}")

    def save_file(self):
        if not self.file_path:
            return self.save_file_as()
        return self._write_source(self.file_path)

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Save assembly source",
            defaultextension=".redstone",
            filetypes=[
                ("Redstone assembly", "*.redstone"),
                ("Text files", "*.txt"),
                ("Assembly files", "*.asm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return False
        if not self._write_source(path):
            return False
        self.file_path = path
        self._update_title()
        return True

    def _write_source(self, path):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as source_file:
                source_file.write(self.editor.text.get("1.0", "end-1c"))
        except OSError as error:
            messagebox.showerror("Save failed", str(error), parent=self.root)
            return False
        self.dirty = False
        self.editor.text.edit_modified(False)
        self._update_title()
        self.status_var.set(f"Saved {os.path.basename(path)}")
        return True

    def compile_source(self):
        source = self.editor.text.get("1.0", "end-1c")
        result = assemble(source)
        self.last_result = result
        self.editor.mark_diagnostics(result.diagnostics)
        if result.succeeded:
            self._set_output(result.output)
            self.status_var.set(f"Compiled successfully - {len(result.words)} word(s)")
        else:
            messages = [
                f"Line {diagnostic.line}: {diagnostic.message}"
                for diagnostic in result.diagnostics
            ]
            self._set_output("Compile failed:\n\n" + "\n".join(messages) + "\n")
            self.status_var.set(f"Compile failed - {len(result.diagnostics)} problem(s)")

    def _set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def copy_output(self):
        text = self.output.get("1.0", "end-1c")
        if not text:
            self.status_var.set("There is no output to copy")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Output copied to clipboard")

    def save_output(self):
        if self.last_result is None or not self.last_result.succeeded:
            messagebox.showinfo(
                "No compiled output",
                "Compile the source successfully before saving output.",
                parent=self.root,
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save compiled Logisim output",
            defaultextension=".txt",
            filetypes=[("Logisim hex files", "*.hex"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as output_file:
                output_file.write(self.last_result.output)
        except OSError as error:
            messagebox.showerror("Save failed", str(error), parent=self.root)
            return
        self.status_var.set(f"Output saved to {os.path.basename(path)}")

    def insert_files(self):
        paths = filedialog.askopenfilenames(
            title="Insert files at the caret",
            filetypes=[
                ("Assembly, text, and hex files", "*.redstone *.txt *.asm *.hex"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        try:
            contents = [source_from_inserted_file(path) for path in paths]
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Insert failed", str(error), parent=self.root)
            return

        inserted_text = ""
        for content in contents:
            if inserted_text and content and not inserted_text.endswith("\n") and not content.startswith("\n"):
                inserted_text += "\n"
            inserted_text += content
        if not inserted_text:
            self.status_var.set("Selected files contain no text")
            return

        caret = self.editor.text.index("insert")
        before_caret = self.editor.text.get("1.0", caret)
        if before_caret and not before_caret.endswith("\n") and not inserted_text.startswith("\n"):
            inserted_text = "\n" + inserted_text
        if not inserted_text.endswith("\n"):
            inserted_text += "\n"
        self.editor.text.insert(caret, inserted_text)
        self.editor.text.focus_set()
        self.status_var.set(f"Inserted {len(paths)} file(s)")

    def insert_example(self):
        self.editor.text.insert("insert", SAMPLE_SOURCE)
        self.editor.text.focus_set()

    def show_reference(self):
        window = tk.Toplevel(self.root)
        window.title("Instruction reference")
        window.transient(self.root)
        window.geometry("360x520")
        window.minsize(320, 300)
        table = ttk.Treeview(
            window,
            columns=("opcode", "operands"),
            show="headings",
            selectmode="browse",
        )
        table.heading("opcode", text="Opcode")
        table.heading("operands", text="Operands")
        table.column("opcode", width=90, anchor="center")
        table.column("operands", width=120, anchor="center")
        table.pack(fill="both", expand=True, padx=12, pady=12)
        for mnemonic in MNEMONICS:
            table.insert(
                "",
                "end",
                values=(f"{OPCODES[mnemonic]:02X}", OPERAND_COUNTS[mnemonic]),
                text=mnemonic,
            )
        table.configure(show="tree headings")
        table.heading("#0", text="Instruction")
        table.column("#0", width=130)
        ttk.Label(
            window,
            text="Numbers are hexadecimal. For JMP/BEQ, a number below the source line count is treated as a zero-based line target; labels are clearer.",
            wraplength=320,
        ).pack(fill="x", padx=12, pady=(0, 12))

    def exit_app(self):
        if self._confirm_discard():
            self.root.destroy()


def main():
    root = tk.Tk()
    CompilerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
