# DESCRIPTION: Red's Assembly Compiler — GUI editor + assembler for a custom 8-bit CPU; supports labels, numeric jump rebasing, themes (Light/Dark/Dark green), file I/O, undo/redo, compile (Ctrl+U) and save (Ctrl+S); remembers theme, last opened file, window size & position in config; update this single-line DESCRIPTION when modifying the compiler so future assistants/users have context.
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json

# --- Configuration ---
Ass = ["NOP","LDA","LDB","LDC","RTA","RTB","RTC","ATR","BTR","CTR","ADD","JMP","CJP","RTD","STR","PRV"]
Hex = ["00","A0","B0","C0","A1","B1","C1","A2","B2","C2","40","10","11","D2","D0","D4"]
opcode_map = {k.upper(): v for k, v in zip(Ass, Hex)}
instr_bytes = {"NOP":0,"LDA":1,"LDB":1,"LDC":1,"RTA":1,"RTB":1,"RTC":1,"ATR":1,"BTR":1,"CTR":1,"ADD":0,"JMP":1,"CJP":2,"RTD":2,"STR":2,"PRV":0}

file_path = None
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "redstone_config.json")
current_theme = "Light"

# ---------- Preferences ----------
def load_config():
    global current_theme, file_path, window_geometry
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            current_theme = cfg.get("theme","Light")
            file_path = cfg.get("last_file", None)
            window_geometry = cfg.get("window_geometry", None)
        except: 
            current_theme = "Light"
            file_path = None
            window_geometry = None
    else:
        current_theme = "Light"
        file_path = None
        window_geometry = None

def save_config():
    cfg = {
        "theme": current_theme,
        "last_file": file_path,
        "window_geometry": root.geometry()
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except:
        pass

# ---------- Tokenizing & parsing ----------
def tokenize_line(line):
    if ";" in line:
        code_part,_ = line.split(";",1)
    else: code_part = line
    code_part = code_part.rstrip()
    tokens = [t for t in code_part.replace(","," ").split() if t!=""]
    return tokens

def to_hex_byte(val): return f"{val:02X}"

def parse_int_token(tok):
    s = tok.strip()
    if s.lower().startswith("0x"):
        try: return int(s,16)
        except: return None
    if s.endswith(("h","H")):
        try: return int(s[:-1],16)
        except: return None
    try: return int(s,10)
    except: pass
    try: return int(s,16)
    except: return None

# ---------- UI ----------
root = tk.Tk()
root.title("Red's Computer Assembly Compiler")
menubar = tk.Menu(root)

# File menu
filemenu = tk.Menu(menubar, tearoff=False)
filemenu.add_command(label="Save", accelerator="Ctrl+S", command=lambda: do_save())
filemenu.add_command(label="Save as...", accelerator="Ctrl+Shift+S", command=lambda: do_save_as())
filemenu.add_separator()
filemenu.add_command(label="Open", accelerator="Ctrl+O", command=lambda: do_open())
menubar.add_cascade(label="File", menu=filemenu)

# Edit menu
editmenu = tk.Menu(menubar, tearoff=False)
editmenu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: on_undo())
editmenu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: on_redo())
editmenu.add_separator()
editmenu.add_command(label="Options...", command=lambda: open_options_window())
menubar.add_cascade(label="Edit", menu=editmenu)

root.config(menu=menubar)
frame = tk.Frame(root)
frame.pack(padx=8,pady=8,fill="both",expand=True)

# Input box
tk.Label(frame,text="Assembly input:",anchor="w").pack(fill="x")
input_box = tk.Text(frame,height=12,wrap="none",undo=True,autoseparators=True,maxundo=-1)
input_box.pack(fill="both",expand=True,padx=2,pady=2)

# Toolbar
toolbar = tk.Frame(frame); toolbar.pack(fill="x", pady=(6,6))
compile_btn = tk.Button(toolbar,text="Compile",width=9,command=lambda: assemble_and_rebase())
compile_btn.pack(side="left", padx=2)
copy_btn = tk.Button(toolbar,text="Copy output",width=9,command=lambda: copy_output())
copy_btn.pack(side="left", padx=2)
save_btn = tk.Button(toolbar,text="Save",width=9,command=lambda: do_save())
save_btn.pack(side="left", padx=2)
open_btn = tk.Button(toolbar,text="Open",width=9,command=lambda: do_open())
open_btn.pack(side="left", padx=2)

# Output box
tk.Label(frame,text="Hex output:",anchor="w").pack(fill="x", pady=(4,0))
output_box = tk.Text(frame,height=12,wrap="none")
output_box.pack(fill="both",expand=True,padx=2,pady=2)

# Tags
output_box.tag_configure("bad",foreground="white",background="red")
output_box.tag_configure("good",foreground="black")
input_box.tag_configure("bad",foreground="white",background="red")
input_box.tag_configure("good",foreground="black")
status_var = tk.StringVar(value="Ready")
status = tk.Label(frame,textvariable=status_var,anchor="w",fg="gray")
status.pack(fill="x", pady=(6,0))

# ---------- Theme ----------
def apply_theme(theme_name, extra_windows=()):
    global current_theme
    current_theme = theme_name
    save_config()  # save theme + window state

    if theme_name=="Light":
        bg_in,fg_in,out_bg,out_fg,bad_bg,bad_fg = "white","black","white","black","red","white"
        win_bg,toolbar_bg,btn_bg = "#f0f0f0","#eaeaea","#e8e8e8"
    elif theme_name=="Dark":
        bg_in,fg_in,out_bg,out_fg,bad_bg,bad_fg = "#1e1e1e","#dcdcdc","#1e1e1e","#dcdcdc","#7f0000","#ffffff"
        win_bg,toolbar_bg,btn_bg = "#2b2b2b","#2b2b2b","#3a3a3a"
    else:  # Dark green
        bg_in,fg_in,out_bg,out_fg,bad_bg,bad_fg = "#0B3B0B","#C9FFD1","#0B3B0B","#C9FFD1","#550000","#FFFFFF"
        win_bg,toolbar_bg,btn_bg = "#0A2A0A","#092509","#09320A"

    root.configure(bg=win_bg); frame.configure(bg=win_bg); toolbar.configure(bg=toolbar_bg); status.configure(bg=win_bg)
    input_box.configure(bg=bg_in,fg=fg_in,insertbackground=fg_in)
    output_box.configure(bg=out_bg,fg=out_fg,insertbackground=out_fg)
    for w in toolbar.winfo_children():
        try: w.configure(bg=btn_bg,fg=fg_in,activebackground=toolbar_bg)
        except: pass
    for child in frame.winfo_children():
        if isinstance(child, tk.Label):
            try: child.configure(bg=win_bg,fg=fg_in)
            except: pass
    input_box.tag_configure("good",foreground=fg_in,background=bg_in)
    input_box.tag_configure("bad",foreground=bad_fg,background=bad_bg)
    output_box.tag_configure("good",foreground=out_fg,background=out_bg)
    output_box.tag_configure("bad",foreground=bad_fg,background=bad_bg)
    for w in extra_windows:
        try:
            w.configure(bg=win_bg)
            for child in w.winfo_children():
                try: child.configure(bg=win_bg,fg=fg_in)
                except: pass
                if isinstance(child, tk.Frame):
                    child.configure(bg=win_bg)
                    for sub in child.winfo_children():
                        try: sub.configure(bg=win_bg,fg=fg_in,selectcolor=win_bg,activebackground=win_bg)
                        except: pass
        except: pass

# Options window remains unchanged (theme radio buttons)
# Options window
def open_options_window():
    win = tk.Toplevel(root)
    win.title("Options")
    win.transient(root)
    win.grab_set()
    # Ensure the options window uses current theme immediately and gets updates
    # radio buttons arranged horizontally
    tk.Label(win, text="Theme:", anchor="w").pack(anchor="w", padx=8, pady=(8,0))

    theme_var = tk.StringVar(value=current_theme)

    row = tk.Frame(win)
    row.pack(fill="x", padx=8, pady=8)

    rb_light = tk.Radiobutton(row, text="Light", variable=theme_var, value="Light")
    rb_light.pack(side="left", padx=6)
    rb_dark = tk.Radiobutton(row, text="Dark", variable=theme_var, value="Dark")
    rb_dark.pack(side="left", padx=6)
    rb_comp = tk.Radiobutton(row, text="Dark green", variable=theme_var, value="Dark green")
    rb_comp.pack(side="left", padx=6)

    # live preview: when theme_var changes, apply immediately to main window and options window
    def on_theme_change(*_):
        apply_theme(theme_var.get(), extra_windows=(win,))
    theme_var.trace_add("write", on_theme_change)

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill="x", pady=8, padx=8)
    def on_ok():
        apply_theme(theme_var.get())
        win.destroy()
    tk.Button(btn_frame, text="OK", width=10, command=on_ok).pack(side="right", padx=4)
    tk.Button(btn_frame, text="Cancel", width=10, command=win.destroy).pack(side="right")

    # apply initial styling to the options window
    apply_theme(current_theme, extra_windows=(win,))


# ---------- Load preferences ----------
load_config()
if "window_geometry" in locals() and window_geometry: root.geometry(window_geometry)
apply_theme(current_theme)

# Continue with your compile, file IO, undo/redo, keybindings, etc.

#############################################################################################################################

# ---------- Core compile logic ----------
def compute_addresses(lines_tokens):
    addresses = []
    addr = 0
    for tokens in lines_tokens:
        addresses.append(addr)
        if not tokens:
            continue
        if tokens[0].endswith(":") and len(tokens) == 1:
            size = 0
        else:
            mn = tokens[0].upper()
            if mn.endswith(":"):
                if len(tokens) >= 2:
                    mn = tokens[1].upper()
                    data_tokens = tokens[2:]
                else:
                    size = 0
                    addr += size
                    continue
            else:
                data_tokens = tokens[1:]
            instr_size = 1 + instr_bytes.get(mn, 0)
            size = instr_size
        addr += size
    return addresses

def assemble_and_rebase():
    output_box.delete("1.0", tk.END)
    input_box.tag_remove("bad", "1.0", tk.END)
    input_box.tag_remove("good", "1.0", tk.END)

    raw = input_box.get("1.0", tk.END).rstrip("\n")
    if raw.strip() == "":
        status_var.set("Nothing to compile")
        return

    lines = raw.splitlines()
    lines_tokens = [tokenize_line(line) for line in lines]
    addresses = compute_addresses(lines_tokens)

    label_map = {}
    for i, tokens in enumerate(lines_tokens):
        if not tokens:
            continue
        first = tokens[0]
        if first.endswith(":"):
            label = first[:-1]
            label_map[label] = addresses[i]

    for i, tokens in enumerate(lines_tokens, start=1):
        rawline = lines[i-1]
        if not tokens:
            output_box.insert(tk.END, "\n")
            input_box.tag_add("good", f"{i}.0", f"{i}.end")
            continue

        if tokens[0].endswith(":") and len(tokens) == 1:
            output_box.insert(tk.END, "\n")
            input_box.tag_add("good", f"{i}.0", f"{i}.end")
            continue

        if tokens[0].endswith(":"):
            label_decl = tokens[0][:-1]
            mnemonic = tokens[1].upper() if len(tokens) > 1 else ""
            data_tokens = tokens[2:]
        else:
            mnemonic = tokens[0].upper()
            data_tokens = tokens[1:]

        expected = instr_bytes.get(mnemonic, None)
        opcode = opcode_map.get(mnemonic, None)

        resolved_data = []
        bad_line = False

        for dt in data_tokens:
            if dt in label_map:
                addr_val = label_map[dt]
                resolved_data.append(to_hex_byte(addr_val))
                continue
            num = parse_int_token(dt)
            if num is not None:
                if 0 <= num < len(lines):
                    target_addr = addresses[num]
                    resolved_data.append(to_hex_byte(target_addr))
                else:
                    resolved_data.append(to_hex_byte(num & 0xFF))
                continue
            parsed = parse_int_token(dt)
            if parsed is not None:
                resolved_data.append(to_hex_byte(parsed & 0xFF))
            else:
                resolved_data.append(dt)
                bad_line = True

        if opcode:
            converted_parts = [opcode] + resolved_data
        else:
            converted_parts = [mnemonic + "/*?*/"] + resolved_data
            bad_line = True

        if expected is not None and len(data_tokens) != expected:
            bad_line = True

        converted_line = " ".join(converted_parts)
        tag = "bad" if bad_line else "good"

        output_box.insert(tk.END, converted_line + "\n", (tag,))
        input_box.tag_add(tag, f"{i}.0", f"{i}.end")

    status_var.set("Compiled: labels resolved, jumps rebased")

# ---------- File IO ----------
def do_open():
    global file_path
    p = filedialog.askopenfilename(defaultextension=".redstone",
                                   filetypes=[("Redstone files","*.redstone"), ("Text files","*.txt"), ("All files","*.*")])
    if not p:
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        input_box.delete("1.0", tk.END)
        input_box.insert("1.0", content)
        file_path = p
        status_var.set(f"Opened: {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open file:\n{e}")

def do_save():
    global file_path
    if not file_path:
        return do_save_as()
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(input_box.get("1.0", tk.END))
        status_var.set(f"Saved: {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save file:\n{e}")

def do_save_as():
    global file_path
    p = filedialog.asksaveasfilename(defaultextension=".redstone",
                                     filetypes=[("Redstone files","*.redstone"), ("Text files","*.txt"), ("All files","*.*")])
    if not p:
        return
    file_path = p
    do_save()

def copy_output():
    out = output_box.get("1.0", tk.END)
    root.clipboard_clear()
    root.clipboard_append(out)
    status_var.set("Output copied to clipboard")

# ---------- Undo / Redo ----------
def on_undo(event=None):
    try:
        input_box.edit_undo()
    except tk.TclError:
        pass
    return "break"

def on_redo(event=None):
    try:
        input_box.edit_redo()
    except tk.TclError:
        pass
    return "break"

# ---------- Keybindings ----------
root.bind_all("<Control-s>", lambda e: (do_save(), "break"))
root.bind_all("<Control-S>", lambda e: (do_save(), "break"))
root.bind_all("<Control-Shift-S>", lambda e: (do_save_as(), "break"))
root.bind_all("<Control-o>", lambda e: (do_open(), "break"))
root.bind_all("<Control-O>", lambda e: (do_open(), "break"))
root.bind_all("<Control-u>", lambda e: (assemble_and_rebase(), "break"))
root.bind_all("<Control-U>", lambda e: (assemble_and_rebase(), "break"))
root.bind_all("<Control-z>", lambda e: on_undo(), add=True)
root.bind_all("<Control-Z>", lambda e: on_undo(), add=True)
root.bind_all("<Control-y>", lambda e: on_redo(), add=True)
root.bind_all("<Control-Y>", lambda e: on_redo(), add=True)
root.bind_all("<Control-Shift-Z>", lambda e: on_redo(), add=True)

# Start example
example = (
    "start:\n"
    "LDA 01    ; load A\n"
    "LDB 02\n"
    "ADD\n"
    "JMP start\n"
)
input_box.insert("1.0", example)

root.mainloop()
