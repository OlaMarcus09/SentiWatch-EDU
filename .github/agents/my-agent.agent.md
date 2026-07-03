Agent instructions

Use any available default model (do not use gpt-5.3-codex).
If unavailable, auto-fallback to supported model and continue.

# CONTEXT
You are working in my existing SentiWatch codebase — a reputation intelligence
SaaS. I am forking/adapting it into "SentiWatch EDU" for a university hackathon
submission. This is a PIVOT of business logic, NOT a rewrite. Preserve all
existing architecture, auth, DB connections, and API contracts unless a task
below explicitly requires a schema change.

STACK:
- Frontend: Next.js 15 (App Router), TypeScript, Tailwind CSS
- Backend: FastAPI (Python)
- DB: Supabase (Postgres, RLS enabled)
- AI: Groq API, llama-3.3-70b-versatile
- Tables: monitored_entities, mentions, sentiment_results, risk_scores, recommendations

# TASK 1 — Recommendation Engine Matrix
Locate the recommendation matrix logic in the backend (likely in a file like
recommendations.py or engine.py). Show me the current implementation first.
Then rewrite the matrix so recommendations are addressed to university
stakeholders (Registrar, Bursary, IT/Portal team, Student Affairs) instead of
PR/brand stakeholders. Keep the same function signature and return shape so
nothing downstream breaks. Example mapping:
  - "fraud_rumor" -> "portal_downtime" advice for IT team
  - "pr_crisis" -> "welfare_concern" advice for Student Affairs
Ask me to confirm category names before finalizing so they match Task 2.

# TASK 2 — AI Category Update
Find where allowed sentiment/mention categories are defined (likely a Python
enum, constant list, or the Groq prompt template itself). Show me that code.
Then update it to this fixed category set:
  ["exams", "portal_issues", "lecturers", "fees", "hostels", "admissions",
   "scholarships", "campus_life"]
If categories are referenced in the Groq classification prompt, update the
prompt text too, and flag any other file that imports/uses the old category
list so I can check for breakage.

# TASK 3 — Frontend Copy Pass
Search the Next.js frontend for these exact strings and list every file/line
where they appear before changing anything:
  - "Brand Reputation"
  - "Automated Crisis Consultant"
  - "Reputation Risk Index" (if present)
Propose replacements ("Campus Health", "Student Welfare Insights", "Campus
Health Score") and show me a diff-style preview per file before applying.
Do not touch component logic, only copy/labels/props that render text.

# CONSTRAINTS
- Do NOT modify RLS policies, auth flow, or the scoring pipeline math.
- Do NOT rename database columns/tables — only display labels and category
  string values.
- After each task, output a short list of files changed so I can review
  before committing.
- Do this task by task, wait for my confirmation after Task 1 before
  starting Task 2.
