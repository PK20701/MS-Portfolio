# MS Portfolio — M.Tech Data Science & Engineering (BITS Pilani WILP, 2024–26)

Two folders, two purposes:

| Folder | What it is | Weight |
|---|---|---|
| [`Dissertation/`](Dissertation/) | **Capstone project** — *A Hybrid Scoring Framework for Jira Requirement Quality: Integrating Domain Rules with Machine Learning Classification*. Working Streamlit app, ML pipeline, tests, report, slides, demo video. | Main showcase |
| [`Coursework/`](Coursework/) | Assignments and practice notebooks from the programme (Python, ML, IR, data structures, data science). | Learning record |

## Dissertation at a glance
- **Problem:** vague ("semantically hollow") Jira requirements cause sprint spill-over and audit gaps; manual review costs hours per sprint.
- **Approach:** a 10-rule syntactic gate (weighted, sums to 100) blended with a TF-IDF text classifier (Random Forest / Logistic Regression / Linear SVM, SMOTE-balanced) into a tunable hybrid score and GOOD/BAD quality gate.
- **Result:** ~92% hold-out accuracy and ~0.96 F1 in 5-fold cross-validation on a 525-ticket labeled set.
- **Delivery:** Streamlit dashboard + conversational auditor over the scored tickets.

Start at [`Dissertation/README.md`](Dissertation/README.md).

## What I learned
Semester-by-semester summary of the programme, the assignments I delivered and how they add to my experience: **[LEARNING_JOURNEY.pdf](LEARNING_JOURNEY.pdf)**.

## Companion repository
The product-management side of the portfolio lives in the **AIPM** repo (linked from the portfolio site).

## Author
Prasanna Kamthekar — M.Tech Data Science & Engineering, BITS Pilani (WILP).
