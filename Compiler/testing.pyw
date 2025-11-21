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
input_box = tk.Text(frame,height=10,wrap="none",undo=True,autoseparators=True,maxundo=-1)
input_box.pack(fill="both",expand=False,padx=2,pady=2)

# Toolbar
toolbar = tk.Frame(frame); toolbar.pack(fill="x", pady=(6,6))
open_btn = tk.Button(toolbar,text="Open",width=9,command=lambda: do_open())
open_btn.pack(side="left", padx=2)
save_btn = tk.Button(toolbar,text="Save",width=9,command=lambda: do_save())
save_btn.pack(side="left", padx=2)
compile_btn = tk.Button(toolbar,text="Compile",width=9,command=lambda: assemble_and_rebase())
compile_btn.pack(side="left", padx=2)
copy_btn = tk.Button(toolbar,text="Copy output",width=11,command=lambda: copy_output())
copy_btn.pack(side="left", padx=8)

# Output box
tk.Label(frame,text="Hex output:",anchor="w").pack(fill="x", pady=(4,0))
output_box = tk.Text(frame,height=10,wrap="none")
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
# ---------- Load preferences ----------
load_config()
if "window_geometry" in locals() and window_geometry: root.geometry(window_geometry)
apply_theme(current_theme)

# Continue with your compile, file IO, undo/redo, keybindings, etc.
