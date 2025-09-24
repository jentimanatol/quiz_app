
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

LETTER_CHOICES = ["A", "B", "C", "D"]

def extract_correct_letter(answer_field: str) -> str:
    # Normalize the correct answer letter from a variety of formats:
    # e.g., "B", "B.", "B. The Logic Theorist", "B - Something"
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
        self.title("AI Quiz App")
        self.geometry("800x520")
        self.minsize(760, 480)

        self.questions = []
        self.user_answers = {}
        self.current_index = 0

        self.create_widgets()
        self.update_navigation_state()

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 5))
        top_frame.pack(fill="x")

        self.open_btn = ttk.Button(top_frame, text="Open JSON", command=self.open_json)
        self.open_btn.pack(side="left")

        self.submit_btn = ttk.Button(top_frame, text="Submit", command=self.submit_quiz, state="disabled")
        self.submit_btn.pack(side="right")

        self.progress_var = tk.StringVar(value="No file loaded")
        self.progress_label = ttk.Label(top_frame, textvariable=self.progress_var)
        self.progress_label.pack(side="right", padx=10)

        q_frame = ttk.LabelFrame(self, text="Question", padding=10)
        q_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.question_text = tk.Text(q_frame, wrap="word", height=6)
        self.question_text.pack(fill="both", expand=False)
        self.question_text.configure(state="disabled")

        self.choice_var = tk.StringVar(value="")
        self.option_vars = [tk.StringVar(value=f"{LETTER_CHOICES[i]}) ") for i in range(4)]
        opts_frame = ttk.Frame(q_frame)
        opts_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.rb_widgets = []
        for i in range(4):
            rb = ttk.Radiobutton(
                opts_frame, textvariable=self.option_vars[i],
                variable=self.choice_var, value=LETTER_CHOICES[i],
                command=self.record_choice
            )
            rb.pack(anchor="w", pady=4)
            self.rb_widgets.append(rb)

        nav_frame = ttk.Frame(self, padding=10)
        nav_frame.pack(fill="x")

        self.prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self.prev_question, state="disabled")
        self.prev_btn.pack(side="left")

        self.next_btn = ttk.Button(nav_frame, text="Next ▶", command=self.next_question, state="disabled")
        self.next_btn.pack(side="right")

        self.unanswered_btn = ttk.Button(nav_frame, text="Jump to Unanswered", command=self.jump_unanswered, state="disabled")
        self.unanswered_btn.pack(side="right", padx=10)

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
            for idx, item in enumerate(data):
                if "question" not in item or "answer" not in item:
                    continue
                qtext = str(item["question"]).strip()
                ans = item["answer"]
                correct_letter = extract_correct_letter(ans)
                display_options = None
                if "options" in item and isinstance(item["options"], (list, tuple)) and len(item["options"]) >= 4:
                    disp = []
                    for i, opt in enumerate(item["options"][:4]):
                        t = str(opt)
                        prefix = f"{LETTER_CHOICES[i]}) "
                        if t.strip().upper().startswith(f"{LETTER_CHOICES[i]})"):
                            disp.append(t.strip())
                        else:
                            disp.append(prefix + t.strip())
                    display_options = disp
                parsed.append({
                    "question": qtext,
                    "answer_letter": correct_letter,
                    "options": display_options
                })
            if not parsed:
                raise ValueError("No valid questions found in JSON.")
            self.questions = parsed
            self.user_answers = {}
            self.current_index = 0
            self.load_question(0)
            self.update_navigation_state()
            self.submit_btn.config(state="normal")
            self.unanswered_btn.config(state="normal")
            self.progress_var.set(self.progress_text())
            messagebox.showinfo("Loaded", f"Loaded {len(self.questions)} questions.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON:\n{e}")

    def load_question(self, index: int):
        if not (0 <= index < len(self.questions)):
            return
        qobj = self.questions[index]
        self.question_text.configure(state="normal")
        self.question_text.delete("1.0", "end")
        self.question_text.insert("1.0", qobj["question"])
        self.question_text.configure(state="disabled")

        if qobj["options"] is None:
            for i, var in enumerate(self.option_vars):
                var.set(f"{LETTER_CHOICES[i]})")
        else:
            for i, var in enumerate(self.option_vars):
                var.set(qobj["options"][i])

        prev_choice = self.user_answers.get(index, "")
        self.choice_var.set(prev_choice)

        self.progress_var.set(self.progress_text())

        # Enable/disable nav buttons depending on where we are
        self.prev_btn.config(state=("normal" if index > 0 else "disabled"))
        self.next_btn.config(state=("normal" if index < len(self.questions) - 1 else "disabled"))

    def record_choice(self):
        self.user_answers[self.current_index] = self.choice_var.get()
        self.progress_var.set(self.progress_text())

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

    def progress_text(self) -> str:
        total = len(self.questions)
        answered = sum(1 for i in range(total) if i in self.user_answers and self.user_answers[i])
        return f"Answered {answered}/{total} | Q {self.current_index+1 if total else 0}/{total}"

    def submit_quiz(self):
        if not self.questions:
            return

        unanswered = [i+1 for i in range(len(self.questions)) if i not in self.user_answers or not self.user_answers[i]]
        if unanswered:
            if not messagebox.askyesno("Unanswered", f"You have unanswered questions: {unanswered}\nSubmit anyway?"):
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

        result_lines = [f"Score: {correct}/{total}  ({pct:.1f}%)", "", "#  Your  Correct  ✓/✗"]
        for row in detailed_rows:
            result_lines.append(f"{row[0]:<2} {row[1]:<5} {row[2]:<7} {row[3]}")
        summary = "\n".join(result_lines)

        # Show popup and also offer to save results
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
