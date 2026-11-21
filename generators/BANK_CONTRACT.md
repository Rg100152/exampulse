# Question Bank Contract

Each subject generator module must define exactly one module-level list named `QUESTIONS`
containing **exactly 250 dictionaries** with this exact schema:

```python
QUESTIONS = [
    {
        "question": "Which Python keyword is used to define a function?",
        "options": ["def", "function", "func", "lambda"],
        "correct_option": "A",          # one of "A", "B", "C", "D"
        "difficulty": "Easy",           # one of "Easy", "Medium", "Hard"
        "topic": "Core Syntax",         # must belong to the subject's topic list
        "explanation": "The 'def' statement creates a named function object ...",
    },
    ...
]
```

## Hard rules

1. Exactly 250 items. No randomness, no external API calls, no dynamic generation at import time.
2. Every string field is non-empty after `.strip()`.
3. `options` is a list of exactly 4 distinct non-empty strings, in a deliberately shuffled order
   (the correct answer must NOT always be option A).
4. `correct_option` is one of `"A"`, `"B"`, `"C"`, `"D"` and points at the factually correct option.
5. `difficulty` is one of `"Easy"`, `"Medium"`, `"Hard"`; aim for roughly 40% Easy, 40% Medium, 20% Hard.
6. `explanation` must be at least 60 characters and must state **why the correct option is right**
   and briefly **why the main distractors are wrong**.
7. Question text must be unique across all 250 items (case-insensitive), and no two items may
   share the same full options tuple.
8. Content must be technically accurate, realistic, and exam-oriented (NTA/TCS-iON style).
   Avoid vague wording and trivial "what is Python" filler.
9. Fields must use double quotes in compatible Python dict literals; plain Python source is fine.

## Topic vocabularies

- Python: Core Syntax, Data Structures, OOP, Functions, Generators & Decorators,
  Files & Exceptions, Libraries, Advanced Concepts
- Data Mining: KDD & Preprocessing, Association Rules, Classification, Clustering,
  Data Warehousing & OLAP, Evaluation Metrics, Text Mining, Big Data Concepts
- .NET: CLR & CTS, C# Fundamentals, OOP in C#, LINQ, ASP.NET Core,
  Entity Framework, Memory & Exceptions, Advanced C#
- Web Design: HTML5 Semantics, CSS3 & Layout, Responsive Design, JavaScript ES6,
  DOM & Events, UI/UX Principles, Accessibility, Performance & Tools

## Self-check (run before finishing)

```bash
python3 - <<'PY'
import importlib.util, collections
spec = importlib.util.spec_from_file_location("bank", "generators/<subject>_bank.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
q = m.QUESTIONS
assert len(q) == 250, len(q)
seen = set()
for i, item in enumerate(q):
    assert set(item) == {"question","options","correct_option","difficulty","topic","explanation"}, i
    for field in ("question", "correct_option", "difficulty", "topic", "explanation"):
        assert isinstance(item[field], str) and item[field].strip(), (i, field)
    assert len(item["options"]) == 4 and all(isinstance(o, str) and o.strip() for o in item["options"]), i
    assert len(set(item["options"])) == 4, i
    assert item["correct_option"] in "ABCD", i
    assert item["difficulty"] in {"Easy","Medium","Hard"}, i
    assert len(item["explanation"]) >= 60, i
    key = item["question"].lower().strip()
    assert key not in seen, (i, key)
    seen.add(key)
print("OK", len(q), collections.Counter(x["difficulty"] for x in q))
print(collections.Counter(x["topic"] for x in q))
PY
```
