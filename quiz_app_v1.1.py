
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

LETTER_CHOICES = ["A", "B", "C", "D"]

def extract_correct_letter(answer_field: str) -> str:
    # Normalize correct answer letter from formats like:
    # "B", "B.", "B. The Logic Theorist", "B - Something"
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
        self.geometry("880x600")
        self.minsize(800, 540)

        # Data
        self.questions = []        # list of dicts: {question, answer_letter, options?}
        self.user_answers = {}     # index -> "A"/"B"/"C"/"D"
        self.current_index = 0

        # Modes
        self.learning_mode = tk.BooleanVar(value=False)
        self.slides_mode = tk.BooleanVar(value=False)  # show Q + Answer

        # UI
        self.create_widgets()
        self.update_navigation_state()

    def create_widgets(self):
        # --- Top controls ---
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 5))
        top_frame.pack(fill="x")

        self.open_btn = ttk.Button(top_frame, text="Open JSON", command=self.open_json)
        self.open_btn.pack(side="left")

        # Quiz title label just below the top controls
        self.quiz_title_var = tk.StringVar(value="(no quiz loaded)")
        title_frame = ttk.Frame(self, padding=(10, 0, 10, 6))
        title_frame.pack(fill="x")
        self.title_label = ttk.Label(title_frame, textvariable=self.quiz_title_var)
        try:
            self.title_label.configure(font=tkfont.Font(size=12, weight="bold"))
        except Exception:
            pass
        self.title_label.pack(anchor="w")

        # Learning Mode toggle
        lm_check = ttk.Checkbutton(
            top_frame, text="Learning Mode (instant feedback)",
            variable=self.learning_mode, command=self.on_toggle_learning_mode
        )
        lm_check.pack(side="left", padx=(12, 6))

        # Slides Mode button (toggle)
        self.slides_btn = ttk.Button(top_frame, text="Slides Mode: OFF", command=self.toggle_slides_mode)
        self.slides_btn.pack(side="left", padx=(6, 12))

        self.submit_btn = ttk.Button(top_frame, text="Submit", command=self.submit_quiz, state="disabled")
        self.submit_btn.pack(side="right")

        self.progress_var = tk.StringVar(value="No file loaded")
        self.progress_label = ttk.Label(top_frame, textvariable=self.progress_var)
        self.progress_label.pack(side="right", padx=10)

        # --- Question area ---
        q_frame = ttk.LabelFrame(self, text="Question", padding=10)
        q_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.question_text = tk.Text(q_frame, wrap="word", height=6)
        self.question_text.pack(fill="both", expand=False)
        self.question_text.configure(state="disabled")

        # --- Options (A-D) ---
        opts_frame = ttk.Frame(q_frame)
        opts_frame.pack(fill="both", expand=True, pady=(10, 6))

        self.choice_var = tk.StringVar(value="")
        self.option_vars = [tk.StringVar(value=f"{LETTER_CHOICES[i]}) ") for i in range(4)]

        # Use tk.Radiobuttons (not ttk) so we can color text easily
        self.rb_widgets = []
        self.default_fg = None  # set after creating
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

        # --- Answer area (for Slides Mode) ---
        ans_frame = ttk.Frame(q_frame)
        ans_frame.pack(fill="x", pady=(4, 0))

        self.answer_var = tk.StringVar(value="")  # will show "Answer: B) ..."
        self.answer_label = ttk.Label(ans_frame, textvariable=self.answer_var, foreground="green4")
        self.answer_label.pack(anchor="w")

        # --- Legend (Learning Mode tip) ---
        self.legend_var = tk.StringVar(value="")
        self.legend_lbl = ttk.Label(self, textvariable=self.legend_var, padding=(10, 0, 10, 10))
        self.legend_lbl.pack(fill="x")

        # --- Navigation ---
        nav_frame = ttk.Frame(self, padding=10)
        nav_frame.pack(fill="x")

        self.prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self.prev_question, state="disabled")
        self.prev_btn.pack(side="left")

        self.next_btn = ttk.Button(nav_frame, text="Next ▶", command=self.next_question, state="disabled")
        self.next_btn.pack(side="right")

        self.unanswered_btn = ttk.Button(nav_frame, text="Jump to Unanswered", command=self.jump_unanswered, state="disabled")
        self.unanswered_btn.pack(side="right", padx=10)

    # ---------- Helpers ----------
    def update_navigation_state(self):
        total = len(self.questions)
        self.prev_btn.config(state=("normal" if total and self.current_index > 0 else "disabled"))
        self.next_btn.config(state=("normal" if total and self.current_index < total - 1 else "disabled"))

    def progress_text(self) -> str:
        total = len(self.questions)
        answered = sum(1 for i in range(total) if i in self.user_answers and self.user_answers[i])
        return f"Answered {answered}/{total} | Q {self.current_index+1 if total else 0}/{total}"

    def reset_option_colors(self):
        for rb in self.rb_widgets:
            rb.configure(fg=self.default_fg)

    def update_option_colors(self):
        # In learning mode: only color AFTER a selection is made.
        # - If correct: chosen turns green.
        # - If wrong: chosen turns red and the correct turns green.
        self.reset_option_colors()
        if not self.learning_mode.get() or not self.questions:
            return

        selected = self.choice_var.get()
        if not selected:
            # No selection yet -> no colors
            return

        q = self.questions[self.current_index]
        correct_letter = q.get("answer_letter", "")
        if not correct_letter:
            return

        try:
            sel_idx = LETTER_CHOICES.index(selected)
        except ValueError:
            return

        if selected == correct_letter:
            self.rb_widgets[sel_idx].configure(fg="green")
        else:
            self.rb_widgets[sel_idx].configure(fg="red")
            # show correct
            try:
                cor_idx = LETTER_CHOICES.index(correct_letter)
                self.rb_widgets[cor_idx].configure(fg="green")
            except ValueError:
                pass

    def update_answer_visibility(self):
        # Controls the 'Slides Mode' answer display under the question.
        if not self.questions:
            self.answer_var.set("")
            return

        if not self.slides_mode.get():
            self.answer_var.set("")
            return

        q = self.questions[self.current_index]
        letter = q.get("answer_letter", "")
        display = ""
        if letter:
            opt_text = None
            opts = q.get("options")
            if isinstance(opts, (list, tuple)) and len(opts) >= 4:
                try:
                    idx = LETTER_CHOICES.index(letter)
                    opt_text = opts[idx]
                except ValueError:
                    opt_text = None
            if opt_text:
                display = f"Answer: {opt_text}"
            else:
                display = f"Answer: {letter})"
        else:
            display = "Answer: (unknown)"
        self.answer_var.set(display)

    # ---------- Data loading ----------
    def open_json(self):
        file_path = filedialog.askopenfilename(
            title="Open quiz JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON root should be a list of question objects.")

            parsed = []
            for item in data:
                if "question" not in item or "answer" not in item:
                    continue
                qtext = str(item["question"]).strip()
                ans = item["answer"]
                correct_letter = extract_correct_letter(ans)

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
                    "answer_letter": correct_letter,
                    "options": display_options
                })

            if not parsed:
                raise ValueError("No valid questions found in JSON. Each item must include 'question' and 'answer'.")

            self.questions = parsed
            self.user_answers = {}
            self.current_index = 0
            self.load_question(0)
            self.update_navigation_state()
            self.submit_btn.config(state="normal")
            self.unanswered_btn.config(state="normal")
            self.progress_var.set(self.progress_text())
            # Update quiz title from file name
            base = os.path.basename(file_path)
            name, _ = os.path.splitext(base)
            self.quiz_title_var.set(f"Quiz: {name}")
            try:
                self.title(f"AI Quiz App — {name}")
            except Exception:
                pass

            messagebox.showinfo("Loaded", f"Loaded {len(self.questions)} questions.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{e}")

    # ---------- Navigation & display ----------
    def load_question(self, index: int):
        if not (0 <= index < len(self.questions)):
            return
        qobj = self.questions[index]

        # Set text
        self.question_text.configure(state="normal")
        self.question_text.delete("1.0", "end")
        self.question_text.insert("1.0", qobj["question"])
        self.question_text.configure(state="disabled")

        # Set options
        if qobj["options"] is None:
            for i, var in enumerate(self.option_vars):
                var.set(f"{LETTER_CHOICES[i]})")
        else:
            for i, var in enumerate(self.option_vars):
                var.set(qobj["options"][i])

        # Restore previous choice
        self.choice_var.set(self.user_answers.get(index, ""))

        # Legend
        if self.learning_mode.get():
            self.legend_var.set("Learning Mode: choose an answer to see instant feedback (green = correct, red = your wrong choice).")
        else:
            self.legend_var.set("")

        self.progress_var.set(self.progress_text())
        self.update_navigation_state()
        # Colors (Learning Mode) and Answer (Slides Mode)
        self.update_option_colors()
        self.update_answer_visibility()

    def record_choice(self):
        self.user_answers[self.current_index] = self.choice_var.get()
        self.progress_var.set(self.progress_text())
        self.update_option_colors()

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
        messagebox.showinfo("Unanswered", "All questions have an answer selected.")

    def on_toggle_learning_mode(self):
        # Update legend and recolor options based on current selection
        if self.learning_mode.get():
            self.legend_var.set("Learning Mode: choose an answer to see instant feedback (green = correct, red = your wrong choice).")
        else:
            self.legend_var.set("")
        self.update_option_colors()

    def toggle_slides_mode(self):
        # Toggle Slides Mode and update button label + answer visibility
        current = self.slides_mode.get()
        self.slides_mode.set(not current)
        self.slides_btn.config(text=f"Slides Mode: {'ON' if self.slides_mode.get() else 'OFF'}")
        self.update_answer_visibility()

    # ---------- Scoring ----------
    def submit_quiz(self):
        if not self.questions:
            return

        # Warn about unanswered
        unanswered = [i+1 for i in range(len(self.questions)) if i not in self.user_answers or not self.user_answers[i]]
        if unanswered:
            go = messagebox.askyesno("Unanswered",
                                     f"You have unanswered questions: {unanswered}\nSubmit anyway?")
            if not go:
                return

        correct = 0
        detailed_rows = []
        for idx, q in enumerate(self.questions):
            user_letter = self.user_answers.get(idx, "")
            correct_letter = q["answer_letter"]
            is_correct = (user_letter == correct_letter) if correct_letter else False
            correct += int(is_correct)
            detailed_rows.append((idx+1, user_letter or "-", correct_letter or "?", "✓" if is_correct else "✗"))

        total = len(self.questions)
        pct = (correct / total * 100.0) if total else 0.0

        # Summary text
        result_lines = [f"Score: {correct}/{total}  ({pct:.1f}%)", "", "#  Your  Correct  ✓/✗"]
        for row in detailed_rows:
            result_lines.append(f"{row[0]:<2} {row[1]:<5} {row[2]:<7} {row[3]}")
        summary = "\n".join(result_lines)

        # Popup + optional save
        if messagebox.askyesno("Quiz Submitted", summary + "\n\nSave results to file?"):
            save_path = filedialog.asksaveasfilename(
                title="Save Results",
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
