# AI Quiz Sets — *Artificial Intelligence: A Guide for Thinking Humans*

This repository contains study/quiz sets (JSON)  for practicing concepts inspired by **_Artificial Intelligence: A Guide for Thinking Humans_** (Melanie Mitchell). The question sets are original, paraphrased MCQs created for learning and review; they are **not** excerpts from the book.

---

## What’s here

### Quiz JSON files (by Part)
All files share the same schema and can be used interchangeably by the app.

| Part | File name | Chapters covered | Approx. # of Qs |
|------|-----------|------------------|------------------|
| Part 1 | `Part 1 Background.json` | 1–3 | 90 |
| Part 2 | `Part 2 Loking and Seeing.json` | 4–7 | 120 |
| Part 3 | `Part 3 Learning to Play.json` | 8–10 | 90 |
| Part 4 | `Part 4 Thinking & Knowing.json` | 11–13 | 90 |
| Part 5 | `Part 5 Building & Deploying AI in the World.json` | 14–16 | 90 |


### Chapter-only JSONs
You may also find per‑chapter files like `ai_ch8_quiz_questions.json`, `ai_ch9_quiz_questions.json`, … `ai_ch16_quiz_questions.json`. These follow the same schema and can be combined into “Part” files (we’ve provided several).

---

## JSON schema

Each question is a single object with **four options** and a single‑letter correct answer.

```json
[
  {
    "question": "What is deep learning?",
    "options": [
      "A) A type of ML that uses hierarchical representations",
      "B) A type of ML that uses shallow neural networks",
      "C) A type of ML that uses linear models",
      "D) A type of ML that uses decision trees"
    ],
    "answer": "A"
  }
]
```

**Rules & tips**
- Exactly **4 options**; keep the leading `"A) "`, `"B) "`, etc.
- `"answer"` is a **single letter** (`"A"`, `"B"`, `"C"`, or `"D"`).  
  The app is forgiving and also accepts forms like `"B."`, `"B) Correct choice"`, etc.
- Keep questions concise and avoid quoting long passages from the book.

---


## License

 MIT for code, and CC BY‑NC for content.

 ## By 
 Anatolie Jentimir 2025
