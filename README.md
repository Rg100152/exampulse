<div align="center">

# ExamPulse 1000

**Enterprise Mock Exam & Practice Test Platform · 1,000+ IT & CS Questions**
Developed by **Raj Gautam** · [github.com/Rg100152/exampulse](https://github.com/Rg100152/exampulse)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-0F172A?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Questions](https://img.shields.io/badge/Questions-1000-10B981)
![Tracks](https://img.shields.io/badge/Tracks-4-2563EB)
![License](https://img.shields.io/badge/License-MIT-8B5CF6)

![CBT UI](https://img.shields.io/badge/UI-Pro%20CBT-0F172A)
![Analytics](https://img.shields.io/badge/Analytics-Detailed-8B5CF6)
![PDF](https://img.shields.io/badge/Scorecard-PDF-EF4444)
![Author](https://img.shields.io/badge/Author-Raj%20Gautam-2563EB)

</div>

---

## What it does

ExamPulse 1000 is a full-stack, offline-friendly mock test engine. It stores **1,000 curated MCQs**
in modular JSON banks, indexes them into SQLite for instant loading even on a 4 GB RAM machine,
and delivers an NTA/TCS-iON inspired computer-based-test experience with a forensic result report.

- **4 tracks × 250 questions** — every question has 4 options, a difficulty tag, a topic tag and a detailed explanation.
- **3 practice modes** — Quick Practice (25 Q / 15 min), Subject Mock (100 Q / 60 min), Full Bank Explorer (250 Q / 120 min).
- **Pro CBT arena** — split-screen layout, live countdown, color-coded question palette, Save & Next, Mark for Review, Clear Response, auto-submit.
- **Analytics report** — score, accuracy, negative-marking breakdown, topic-wise weak areas, and a question-by-question solution review with filter tabs.
- **Study Bank mode** — search and browse all 1,000 Q&As with explanations visible.
- **PDF scorecard** — dependency-free, print-ready A4 report download.

---

## Data Flow Diagram (DFD)

```mermaid
flowchart TD
    S[Student / Candidate] -->|Select Subject & Mode| L[Exam Lobby]
    L -->|Fetch Randomized Set| DB[(SQLite: 1,000 Q&A Bank)]
    DB -->|Python / Data Mining / .NET / Web Design| CBT[Live CBT Exam Arena]
    CBT -->|Save & Next / Mark for Review / Timer| CBT
    CBT -->|Submit Responses + Timer Data| G[Auto-Grading & Feedback Engine]
    G -->|Score, Accuracy % & Detailed Explanations| R[Analytics Feedback Report]
    R -->|Export| PDF[PDF Scorecard]
    DB -->|Search & Browse| SB[Study Bank Mode]
```

---

## Question bank distribution

| Subject Track | Total Questions | Key Topics Covered |
| :--- | :---: | :--- |
| **Python Programming** | 250 | Core syntax, data structures, OOP, functions, generators, decorators, files, exceptions, libraries, advanced concepts |
| **Data Mining & Warehousing** | 250 | KDD, preprocessing, Apriori, decision trees, K-means, OLAP, star schema, evaluation metrics, text mining, big data |
| **.NET Framework & C#** | 250 | CLR, CTS, C# fundamentals, OOP, LINQ, ASP.NET Core, Entity Framework, memory, exceptions, async/await |
| **Web Design & Frontend** | 250 | Semantic HTML5, CSS Grid/Flexbox, responsive UI, JavaScript ES6, DOM events, UI/UX, accessibility, performance |

Marking scheme: **+1** for a correct answer, **−0.25** for a wrong answer, **0** for an unanswered question.

---

## Quick start

```bash
git clone https://github.com/Rg100152/exampulse.git
cd exampulse

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python seed_1000_questions.py     # builds database/exampulse.db from data/*.json
python app.py                     # http://127.0.0.1:5000
```

The database is created automatically on first run if the four JSON banks are present.
To regenerate banks from the authoring modules and re-index everything:

```bash
python generate_question_banks.py
python seed_1000_questions.py --force
python seed_1000_questions.py --check
python verify_banks.py                 # final integrity report: 1,000 unique, complete questions
```

Optional environment variables: `EXAMPULSE_DB`, `EXAMPULSE_SECRET`, `EXAMPULSE_HOST`,
`EXAMPULSE_PORT`, `EXAMPULSE_DEBUG`, `EXAMPULSE_CANDIDATE`.

---

## Project structure

```text
exampulse/
├── app.py                      # Flask server & app factory
├── exampulse_core.py           # Config, SQLite access, attempt creation, grading
├── generate_question_banks.py  # Validates generators/ and writes data/*.json
├── verify_banks.py             # Final 1,000-question integrity report
├── seed_1000_questions.py      # Indexes all 1,000 Q&As into SQLite
├── requirements.txt
├── README.md
├── .gitignore
├── generators/                 # Offline question authoring modules + bank contract
├── data/
│   ├── python_250.json
│   ├── datamining_250.json
│   ├── dotnet_250.json
│   └── webdesign_250.json
├── database/
│   └── exampulse.db            # Generated: questions + attempts + responses
├── routes/
│   ├── exam_routes.py          # Lobby, CBT arena, report, study bank, PDF export
│   └── api_routes.py           # JSON APIs for question sets and grading
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── exam_arena.html
│   ├── feedback_report.html
│   ├── bank_viewer.html
│   ├── results.html
│   └── not_found.html
├── static/
│   ├── css/cbt_ui.css
│   ├── js/examEngine.js
│   ├── js/analytics.js
│   └── assets/logo-exampulse.svg
└── utils/pdf_scorecard.py      # Pure-stdlib PDF generation
```

---

## Routes & API

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| GET | `/` | Exam lobby with 4 subject tracks |
| GET | `/exam/<subject>?mode=quick\|mock\|full` | Live CBT arena |
| GET | `/result/<attempt_code>` | Detailed analytics report |
| GET | `/result/<attempt_code>/pdf` | Download PDF scorecard |
| GET | `/bank/<subject>` | Study bank with search and filters |
| GET | `/results` | Attempt history |
| GET | `/api/subjects` | Subject metadata and available question counts |
| GET | `/api/stats` | Overall platform statistics |
| GET | `/api/questions/<subject>` | Searchable question set (`q`, `topic`, `difficulty`, `limit`, `offset`) |
| POST | `/api/attempts/start` | Create a randomized attempt (`subject`, `mode`) |
| GET | `/api/attempts/<code>` | Live attempt payload (answers withheld) |
| POST | `/api/attempts/<code>/submit` | Server-authoritative grading (`answers`, `elapsed_seconds`) |
| GET | `/api/attempts/<code>/report` | Full JSON report |
| GET | `/api/health` | Health check |

Example submission:

```bash
curl -X POST http://127.0.0.1:5000/api/attempts/start \
  -H 'Content-Type: application/json' \
  -d '{"subject":"python","mode":"quick"}'
```

---

## Design tokens

| Role | Color |
| :--- | :--- |
| Background | `#F1F5F9` cool slate |
| Header & palette | `#0F172A` deep navy |
| Answered | `#10B981` emerald |
| Marked for review | `#8B5CF6` royal purple |
| Not answered | `#EF4444` coral red |
| Current question | `#2563EB` electric blue |

---

## Integrity & performance

- `question_key` is a SHA-1 of subject + normalized question text with a UNIQUE constraint; duplicates cannot be seeded.
- The seeder validates schema, option count, distinct options, answer letter, topic vocabulary, difficulty and explanation length before any insert.
- Questions are fetched with indexed, server-side pagination, so all 1,000 Q&As never load into the browser at once.
- Grading reads correct answers from SQLite only; client-side answer data can never alter the score.

---

**Built with Flask + SQLite + HTML5 + CSS3 + Vanilla JS — no frontend framework, no paid services.**

© 2026 Raj Gautam · MIT License
