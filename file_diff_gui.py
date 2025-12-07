import difflib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines(keepends=False)
    except Exception as e:
        messagebox.showerror("Read error", f"Could not read {path}\n\n{e}")
        return None

def normalize_lines(lines, ignore_case, ignore_ws):
    norm = []
    for line in lines:
        s = line
        if ignore_ws:
            s = " ".join(s.split())  # collapse whitespace
        if ignore_case:
            s = s.casefold()
        norm.append(s)
    return norm

class DiffGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple File Diff (Tkinter)")
        self.geometry("1000x650")
        self.minsize(800, 500)

        self.file1 = tk.StringVar()
        self.file2 = tk.StringVar()
        self.ignore_case = tk.BooleanVar(value=False)
        self.ignore_ws = tk.BooleanVar(value=False)

        # Top file selectors
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="File A:").grid(row=0, column=0, sticky="w", padx=(0,6))
        ttk.Entry(top, textvariable=self.file1, width=70).grid(row=0, column=1, sticky="we")
        ttk.Button(top, text="Browse…", command=self.pick_file1).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="File B:").grid(row=1, column=0, sticky="w", padx=(0,6), pady=(8,0))
        ttk.Entry(top, textvariable=self.file2, width=70).grid(row=1, column=1, sticky="we", pady=(8,0))
        ttk.Button(top, text="Browse…", command=self.pick_file2).grid(row=1, column=2, padx=6, pady=(8,0))

        top.columnconfigure(1, weight=1)

        # Options + buttons
        opts = ttk.Frame(self, padding=(10,0,10,10))
        opts.pack(fill="x")
        ttk.Checkbutton(opts, text="Ignore case", variable=self.ignore_case).pack(side="left")
        ttk.Checkbutton(opts, text="Ignore whitespace", variable=self.ignore_ws).pack(side="left", padx=(12,0))

        ttk.Button(opts, text="Compare", command=self.compare).pack(side="right")
        ttk.Button(opts, text="Clear", command=self.clear).pack(side="right", padx=(0,8))
        ttk.Button(opts, text="Save Diff…", command=self.save_diff).pack(side="right", padx=(0,8))

        # Diff output
        self.text = ScrolledText(self, wrap="none", undo=False, font=("Courier New", 11))
        self.text.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Tags for colors
        self.text.tag_configure("plus", foreground="#1a7f37")     # green
        self.text.tag_configure("minus", foreground="#d1242f")    # red
        self.text.tag_configure("ctx", foreground="#57606a")      # gray
        self.text.tag_configure("meta", foreground="#0a3069")     # blue (headers)
        self.text.tag_configure("hint", background="#fff3b4")     # yellow bg for '?' hints

        # Status bar
        self.status = tk.StringVar(value="Pick two files and click Compare.")
        bar = ttk.Label(self, textvariable=self.status, anchor="w", padding=(10,4))
        bar.pack(fill="x", side="bottom")

        # Horizontal/vertical scroll sync (optional but nice)
        self._add_scrollbars()

        self.last_diff_lines = []  # for saving

    def _add_scrollbars(self):
        # Add horizontal scrollbar
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(xscrollcommand=hbar.set)
        hbar.pack(fill="x", side="bottom")

    def pick_file1(self):
        path = filedialog.askopenfilename(title="Select File A")
        if path:
            self.file1.set(path)

    def pick_file2(self):
        path = filedialog.askopenfilename(title="Select File B")
        if path:
            self.file2.set(path)

    def clear(self):
        self.text.delete("1.0", "end")
        self.status.set("Cleared.")
        self.last_diff_lines = []

    def insert_line(self, line):
        # Apply simple syntax coloring by diff marker
        if line.startswith("+"):
            self.text.insert("end", line, "plus")
        elif line.startswith("-"):
            self.text.insert("end", line, "minus")
        elif line.startswith("?"):
            self.text.insert("end", line, "hint")
        elif line.startswith(("---", "+++", "@@")):
            self.text.insert("end", line, "meta")
        elif line.startswith(" "):
            self.text.insert("end", line, "ctx")
        else:
            self.text.insert("end", line)  # fallback

    def compare(self):
        path1 = self.file1.get().strip()
        path2 = self.file2.get().strip()
        if not path1 or not path2:
            messagebox.showwarning("Missing file", "Please choose both File A and File B.")
            return
        if not Path(path1).exists() or not Path(path2).exists():
            messagebox.showwarning("Invalid file", "One or both file paths do not exist.")
            return

        lines1 = read_text(path1)
        lines2 = read_text(path2)
        if lines1 is None or lines2 is None:
            return

        # Normalize (for diff only) if options are set
        norm1 = normalize_lines(lines1, self.ignore_case.get(), self.ignore_ws.get())
        norm2 = normalize_lines(lines2, self.ignore_case.get(), self.ignore_ws.get())

        # Compute diff using ndiff for clear +/-/? lines
        diff = list(difflib.ndiff(norm1, norm2))

        # Count stats and display
        added = sum(1 for l in diff if l.startswith("+ "))
        removed = sum(1 for l in diff if l.startswith("- "))
        changed_hints = sum(1 for l in diff if l.startswith("? "))

        self.text.config(state="normal")
        self.clear()

        # Header
        header = [
            f"Comparing:\n  A: {path1}\n  B: {path2}\n",
            f"Options: ignore_case={self.ignore_case.get()}  ignore_whitespace={self.ignore_ws.get()}\n",
            f"Summary: +{added}  -{removed}  ?{changed_hints} (hints)\n",
            "-" * 80 + "\n"
        ]
        for h in header:
            self.text.insert("end", h, "meta")

        # Insert diff lines
        self.last_diff_lines = []
        for line in diff:
            out = line + "\n"
            self.insert_line(out)
            self.last_diff_lines.append(out)

        self.text.config(state="normal")
        self.text.see("1.0")
        self.status.set(f"Done. Added: {added}, Removed: {removed}, Hints: {changed_hints}")

    def save_diff(self):
        if not self.last_diff_lines:
            messagebox.showinfo("No diff", "Nothing to save. Run a comparison first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Diff",
            defaultextension=".diff",
            filetypes=[("Diff/patch file", "*.diff *.patch *.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            Path(path).write_text("".join(self.last_diff_lines), encoding="utf-8")
            self.status.set(f"Saved diff to {path}")
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save diff\n\n{e}")

if __name__ == "__main__":
    app = DiffGUI()
    try:
        app.iconify(); app.update(); app.deiconify()  # nudge some window managers
    except Exception:
        pass
    app.mainloop()
