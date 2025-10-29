import json
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

LETTER_CHOICES = ["A", "B", "C", "D"]

# --- Robust JSON reader: tolerates BOM, // comments, /* */ blocks, and trailing commas
def _read_json_loose(path: str):
    text = Path(path).read_text(encoding="utf-8-sig")  # strip BOM if present
    # Remove // comments that start a line or follow a comma/brace/bracket (heuristic)
    text = re.sub(r'(^|[\s\[{,])//.*?$', r'\1', text, flags=re.MULTILINE)
    # Remove /* block */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove trailing commas before ] or }
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return json.loads(text)

def extract_correct_letter(answer_field: str) -> str:
    """
    Normalize the correct answer letter from formats like:
    "B", "B.", "B) Something", "B - Something", "b", etc.
    """
    if not isinstance(answer_field, str):
        return ""
    s = answer_field.strip()
    for ch in s:
        if ch.upper() in LETTER_CHOICES:
            return ch.upper()
    return ""

class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AJ Quiz App")
        self.geometry("900x620")
        self.minsize(820, 560)

        # Data
        self.questions = []        # list of {question, answer_letter, options[4], explanation?}
        self.user_answers = {}     # index -> "A"/"B"/"C"/"D"
        self.current_index = 0
        self.metadata = {}         # v2 metadata (title, chapter, etc.)

        # Modes
        self.learning_mode = tk.BooleanVar(value=False)  # instant feedback on selection
        self.slides_mode = tk.BooleanVar(value=False)    # show Q + Answer (+ explanation)

        self.create_widgets()
        self.update_navigation_state()

    # ---------- UI ----------
    def create_widgets(self):
        # Top controls
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 5))
        top_frame.pack(fill="x")

        self.open_btn = ttk.Button(top_frame, text="Open JSON", command=self.open_json)
        self.open_btn.pack(side="left")

        # NEW: Library and About
        self.lib_btn = ttk.Button(top_frame, text="Library…", command=self.open_from_library)
        self.lib_btn.pack(side="left", padx=(6, 0))

        self.about_btn = ttk.Button(top_frame, text="About", command=self.show_about)
        self.about_btn.pack(side="left", padx=(6, 12))

        # Learning mode checkbox
        self.learning_chk = ttk.Checkbutton(
            top_frame,
            text="Learning Mode (instant feedback)",
            variable=self.learning_mode,
            command=self.on_toggle_learning_mode
        )
        self.learning_chk.pack(side="left")

        # Slides Mode toggle button
        self.slides_btn = ttk.Button(top_frame, text="Slides Mode: OFF", command=self.toggle_slides_mode)
        self.slides_btn.pack(side="left", padx=(10, 12))

        # Progress and Submit
        self.progress_var = tk.StringVar(value="No file loaded")
        self.progress_label = ttk.Label(top_frame, textvariable=self.progress_var)
        self.progress_label.pack(side="right", padx=10)

        self.submit_btn = ttk.Button(top_frame, text="Submit", command=self.submit_quiz, state="disabled")
        self.submit_btn.pack(side="right")

        # Quiz title
        self.quiz_title_var = tk.StringVar(value="(no quiz loaded)")
        title_frame = ttk.Frame(self, padding=(10, 0, 10, 6))
        title_frame.pack(fill="x")
        self.title_label = ttk.Label(title_frame, textvariable=self.quiz_title_var)
        try:
            # Larger bold header if available
            self.title_label.configure(font=tkfont.Font(size=14, weight="bold"))
        except Exception:
            pass
        self.title_label.pack(anchor="w")

        # Question area
        q_frame = ttk.LabelFrame(self, text="Question", padding=10)
        q_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self.question_text = tk.Text(q_frame, height=6, wrap="word")
        self.question_text.pack(fill="both", expand=True)
        self.question_text.configure(state="disabled")

        # Options
        opts_frame = ttk.Frame(q_frame)
        opts_frame.pack(fill="x", pady=(10, 6))

        self.option_vars = [tk.StringVar(value=f"{ch})") for ch in LETTER_CHOICES]
        self.choice_var = tk.StringVar(value="")
        self.rb_widgets = []
        self.default_fg = None
        for i in range(4):
            rb = tk.Radiobutton(
                opts_frame,
                textvariable=self.option_vars[i],
                variable=self.choice_var,
                value=LETTER_CHOICES[i],
                anchor="w",
                justify="left",
                command=self.record_choice,
            )
            rb.pack(fill="x", pady=4, anchor="w")
            if self.default_fg is None:
                self.default_fg = rb.cget("fg")
            self.rb_widgets.append(rb)

        # Slides Mode answer & explanation
        ans_frame = ttk.Frame(q_frame)
        ans_frame.pack(fill="x", pady=(4, 0))
        self.answer_var = tk.StringVar(value="")
        self.answer_label = ttk.Label(ans_frame, textvariable=self.answer_var, foreground="green4")
        self.answer_label.pack(anchor="w")

        self.expl_var = tk.StringVar(value="")
        self.expl_label = ttk.Label(ans_frame, textvariable=self.expl_var, wraplength=800, justify="left")
        self.expl_label.pack(anchor="w", pady=(2, 0))

        # Legend for learning mode
        self.legend_var = tk.StringVar(value="")
        self.legend_lbl = ttk.Label(self, textvariable=self.legend_var, padding=(10, 0, 10, 10))
        self.legend_lbl.pack(fill="x")

        # Bottom navigation
        nav = ttk.Frame(self, padding=(10, 0, 10, 10))
        nav.pack(fill="x")

        self.prev_btn = ttk.Button(nav, text="◀ Previous", command=self.prev_question, state="disabled")
        self.prev_btn.pack(side="left")

        self.unanswered_btn = ttk.Button(nav, text="Jump to Unanswered", command=self.jump_unanswered, state="disabled")
        self.unanswered_btn.pack(side="right")

        self.next_btn = ttk.Button(nav, text="Next ▶", command=self.next_question, state="disabled")
        self.next_btn.pack(side="right", padx=(0, 10))

    # ---------- Data loading ----------
    def open_json(self):
        file_path = filedialog.askopenfilename(
            title="Open quiz JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            data = _read_json_loose(file_path)
            self._load_from_data(data, file_path=file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON from:\n{file_path}\n\n{e}")

    def _parse_questions_list(self, items):
        parsed = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if "question" not in item or "answer" not in item:
                continue
            qtext = str(item["question"]).strip()
            ans = item["answer"]
            letter = extract_correct_letter(ans)

            display_options = None
            if "options" in item and isinstance(item["options"], (list, tuple)) and len(item["options"]) >= 4:
                disp = []
                for i, opt in enumerate(item["options"][:4]):
                    t = str(opt).strip()
                    if t.upper().startswith(f"{LETTER_CHOICES[i]})"):
                        disp.append(t)
                    else:
                        disp.append(f"{LETTER_CHOICES[i]}) {t}")
                display_options = disp

            parsed.append({
                "question": qtext,
                "answer_letter": letter,
                "options": display_options,
                "explanation": item.get("explanation", "")
            })
        return parsed

    def _load_from_data(self, data, file_path="(memory)"):
        """Accepts v1 (root=list) or v2 (root=dict with 'questions'). Applies metadata/config if present."""
        metadata_title = None
        set_learning = None
        set_slides = None
        self.metadata = {}

        if isinstance(data, list):
            # v1 legacy format
            parsed = self._parse_questions_list(data)
            base = os.path.basename(file_path)
            name, _ = os.path.splitext(base)
            quiz_title = name
        elif isinstance(data, dict):
            # v2 format with metadata/config/questions
            questions = data.get("questions")
            if not isinstance(questions, list):
                raise ValueError("JSON root is an object but no valid 'questions' array was found.")
            parsed = self._parse_questions_list(questions)

            md = data.get("metadata", {})
            if isinstance(md, dict):
                self.metadata = md
                metadata_title = md.get("title")

            base = os.path.basename(file_path)
            name, _ = os.path.splitext(base)
            quiz_title = metadata_title or name

            cfg = data.get("config", {})
            if isinstance(cfg, dict):
                lm = cfg.get("learning_mode", {})
                if isinstance(lm, dict) and isinstance(lm.get("instant_feedback"), bool):
                    set_learning = lm["instant_feedback"]
                sm = cfg.get("slides_mode", {})
                if isinstance(sm, dict) and isinstance(sm.get("enabled"), bool):
                    set_slides = sm["enabled"]
        else:
            raise ValueError("Unsupported JSON structure. Expect a list or an object with a 'questions' array.")

        if not parsed:
            raise ValueError("No valid questions found. Each question needs 'question', 'answer', and 4 'options'.")

        # Commit to UI state
        self.questions = parsed
        self.user_answers = {}
        self.current_index = 0

        if isinstance(set_learning, bool):
            self.learning_mode.set(set_learning)
        if isinstance(set_slides, bool):
            self.slides_mode.set(set_slides)

        # Update UI text for modes
        self.slides_btn.config(text=f"Slides Mode: {'ON' if self.slides_mode.get() else 'OFF'}")
        if self.learning_mode.get():
            self.legend_var.set("Learning Mode: choose an answer to see instant feedback (green = correct, red = your wrong choice).")
        else:
            self.legend_var.set("")

        # First question
        self.load_question(0)
        self.update_navigation_state()
        self.submit_btn.config(state="normal")
        self.unanswered_btn.config(state="normal")
        self.progress_var.set(self.progress_text())

        # Title in window + header
        self.quiz_title_var.set(f"Quiz: {quiz_title}")
        try:
            self.title(f"AJ Quiz App — {quiz_title}")
        except Exception:
            pass

        messagebox.showinfo("Loaded", f"Loaded {len(self.questions)} questions.")

    def open_from_library(self):
        # Default to ./quizzes if exists
        default_dir = os.path.join(os.getcwd(), "quizzes")
        initial = default_dir if os.path.isdir(default_dir) else os.getcwd()
        folder = filedialog.askdirectory(title="Select quiz library folder", initialdir=initial)
        if not folder:
            return

        import glob
        paths = sorted(glob.glob(os.path.join(folder, "*.json")))
        if not paths:
            messagebox.showwarning("No quizzes", "No .json files found in that folder.")
            return

        # Build list entries with v2 metadata title if present
        entries = []
        for path in paths:
            try:
                d = _read_json_loose(path)
                if isinstance(d, dict) and isinstance(d.get("metadata"), dict) and isinstance(d.get("questions"), list):
                    title = d["metadata"].get("title") or os.path.basename(path)
                else:
                    title = os.path.basename(path)
            except Exception:
                title = os.path.basename(path)
            entries.append((title, path))

        # Modal selector
        sel = tk.Toplevel(self)
        sel.title("Quiz Library")
        sel.geometry("560x460")
        ttk.Label(sel, text=f"Folder: {folder}", wraplength=520).pack(pady=(10,4))
        frame = ttk.Frame(sel)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        lb = tk.Listbox(frame)
        lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.config(yscrollcommand=sb.set)

        for title, _p in entries:
            lb.insert("end", title)

        btn_frame = ttk.Frame(sel)
        btn_frame.pack(fill="x", padx=10, pady=(0,10))

        def _load_selected():
            idxs = lb.curselection()
            if not idxs:
                messagebox.showwarning("Pick one", "Select a quiz from the list.")
                return
            _, path = entries[idxs[0]]
            try:
                data = _read_json_loose(path)
                self._load_from_data(data, file_path=path)
                sel.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load:\n{path}\n\n{e}")

        ttk.Button(btn_frame, text="Load", command=_load_selected).pack(side="right")
        ttk.Button(btn_frame, text="Cancel", command=sel.destroy).pack(side="right", padx=(0,6))

    def show_about(self):
        if not self.questions:
            messagebox.showinfo("About", "No quiz loaded yet.")
            return
        md = self.metadata or {}
        lines = []
        title = md.get("title") or self.quiz_title_var.get()
        lines.append(f"{title}")
        if "chapter" in md: lines.append(f"Chapter: {md['chapter']}")
        if "topic" in md: lines.append(f"Topic: {md['topic']}")
        if "source" in md: lines.append(f"Source: {md['source']}")
        if "author" in md: lines.append(f"Author: {md['author']}")
        if "version" in md: lines.append(f"Quiz JSON Version: {md['version']}")
        if "created_utc" in md: lines.append(f"Created (UTC): {md['created_utc']}")
        lines.append(f"Total questions: {len(self.questions)}")
        messagebox.showinfo("About this quiz", "\n".join(lines))

    # ---------- Question/answer rendering ----------
    def load_question(self, idx: int):
        if not (0 <= idx < len(self.questions)):
            return
        self.current_index = idx
        q = self.questions[idx]

        # Question text
        self.question_text.configure(state="normal")
        self.question_text.delete("1.0", "end")
        self.question_text.insert("1.0", q.get("question", ""))
        self.question_text.configure(state="disabled")

        # Options
        opts = q.get("options")
        if isinstance(opts, (list, tuple)) and len(opts) >= 4:
            for i in range(4):
                self.option_vars[i].set(str(opts[i]))
        else:
            # Fallback to plain letter labels
            for i in range(4):
                self.option_vars[i].set(f"{LETTER_CHOICES[i]})")

        # Reset selection for this question if not answered yet
        self.choice_var.set(self.user_answers.get(idx, ""))

        # Update colors (learning mode)
        self.update_option_colors()

        # Slides Mode answer + explanation
        self.update_answer_visibility()

        # Buttons state
        self.update_navigation_state()
        self.progress_var.set(self.progress_text())

    def record_choice(self):
        self.user_answers[self.current_index] = self.choice_var.get()
        self.progress_var.set(self.progress_text())
        self.update_option_colors()
        if self.slides_mode.get():
            self.update_answer_visibility()

    # ---------- Modes ----------
    def on_toggle_learning_mode(self):
        if self.learning_mode.get():
            self.legend_var.set("Learning Mode: choose an answer to see instant feedback (green = correct, red = your wrong choice).")
        else:
            self.legend_var.set("")
        self.update_option_colors()

    def toggle_slides_mode(self):
        self.slides_mode.set(not self.slides_mode.get())
        self.slides_btn.config(text=f"Slides Mode: {'ON' if self.slides_mode.get() else 'OFF'}")
        self.update_answer_visibility()

    def update_answer_visibility(self):
        if not self.questions:
            self.answer_var.set("")
            self.expl_var.set("")
            return

        q = self.questions[self.current_index]
        if self.slides_mode.get():
            letter = q.get("answer_letter") or ""
            opts = q.get("options", [])
            opt_text = None
            if isinstance(opts, (list, tuple)) and len(opts) >= 4 and letter in LETTER_CHOICES:
                try:
                    idx = LETTER_CHOICES.index(letter)
                    opt_text = opts[idx]
                except ValueError:
                    opt_text = None
            display = f"Answer: {opt_text}" if opt_text else f"Answer: {letter})"
            self.answer_var.set(display)

            expl = q.get("explanation", "")
            self.expl_var.set(expl if expl else "")
        else:
            self.answer_var.set("")
            self.expl_var.set("")

    def update_option_colors(self):
        # In Learning Mode, color the selected option as correct/incorrect
        if not self.questions:
            return
        q = self.questions[self.current_index]
        correct = q.get("answer_letter")

        for i, rb in enumerate(self.rb_widgets):
            # Reset first
            try:
                rb.configure(fg=self.default_fg)
            except Exception:
                pass

        if not self.learning_mode.get():
            return

        chosen = self.choice_var.get()
        if not chosen or chosen not in LETTER_CHOICES:
            return

        for i, rb in enumerate(self.rb_widgets):
            letter = LETTER_CHOICES[i]
            if letter == chosen:
                if chosen == correct:
                    try:
                        rb.configure(fg="green4")
                    except Exception:
                        pass
                else:
                    try:
                        rb.configure(fg="red3")
                    except Exception:
                        pass

    # ---------- Navigation & progress ----------
    def next_question(self):
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self.load_question(self.current_index)

    def prev_question(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_question(self.current_index)

    def jump_unanswered(self):
        for i in range(len(self.questions)):
            if i not in self.user_answers or not self.user_answers[i]:
                self.current_index = i
                self.load_question(i)
                return
        messagebox.showinfo("All answered", "There are no unanswered questions.")

    def update_navigation_state(self):
        if not self.questions:
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="disabled")
            return
        self.prev_btn.config(state="normal" if self.current_index > 0 else "disabled")
        self.next_btn.config(state="normal" if self.current_index < len(self.questions) - 1 else "disabled")

    def progress_text(self):
        total = len(self.questions)
        answered = sum(1 for i in range(total) if self.user_answers.get(i))
        qn = self.current_index + 1 if total > 0 else 0
        return f"Answered {answered}/{total} | Q {qn}/{total}"

    # ---------- Submit ----------
    def submit_quiz(self):
        if not self.questions:
            messagebox.showwarning("No quiz", "Load a quiz first.")
            return

        total = len(self.questions)
        correct = 0
        lines = ["Results:\n"]
        for i, q in enumerate(self.questions):
            user = self.user_answers.get(i, "(blank)")
            letter = q.get("answer_letter", "")
            ok = (user == letter)
            if ok:
                correct += 1
            item = f"Q{i+1}: {'✔' if ok else '✘'}  Your: {user or '(blank)'}   Correct: {letter}"
            lines.append(item)
        score = f"\nScore: {correct}/{total}  ({(100.0*correct/total):.1f}%)\n"
        lines.append(score)
        summary = "\n".join(lines)

        # Show & offer to save
        messagebox.showinfo("Quiz Summary", summary)
        save_path = filedialog.asksaveasfilename(
            title="Save results as...",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="quiz_results.txt"
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(summary)
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save results:\n{e}")

if __name__ == "__main__":
    app = QuizApp()
    app.mainloop()
