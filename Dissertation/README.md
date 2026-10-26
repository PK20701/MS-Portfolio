# A Hybrid Scoring Framework for Jira Requirement Quality

> Integrating domain rules with machine-learning classification to flag vague, non-actionable Jira requirements before they reach development.

M.Tech Data Science & Engineering dissertation, BITS Pilani WILP (2026).

## What it does
1. **Rule engine** (`src/rule_engine.py`) — 10 weighted checks (summary/description length, acceptance criteria present and in Gherkin form, user-story format, due date, priority, category, assignee, sub-area). Weights sum to 100.
2. **ML classifier** (`src/ml_pipeline.py`) — TF-IDF (1–2-grams, 1000 features) + a vague-term density feature, SMOTE for class balance, three candidate models compared.
3. **Hybrid scorer** (`src/hybrid_scorer.py`) — `hybrid = w·rule + (1−w)·ML`, default w = 60 %, quality gate at 70 %. Both are tunable in the UI.
4. **Streamlit app** (`app.py`) — upload a Jira export (CSV/XLS/XLSX) → dashboard, per-ticket breakdown with suggested fixes, and a chatbot (`src/chatbot_engine.py`) for ticket lookups and statistics. An optional local Ollama LLM is used when available (disabled on hosted Streamlit).

## Quick start
```bash
cd Dissertation
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py          # then upload data/sample_upload_unlabeled.xls
pytest tests                  # 12 smoke/unit tests
```

## Layout
```
Dissertation/
├── app.py                    Streamlit entry point (inference only, loads models/)
├── src/                      preprocessing, feature engineering, rules, ML pipeline, hybrid scorer, chatbot
├── models/                   best_model.pkl (Random Forest pipeline), vectorizer.pkl
├── data/
│   ├── Jira_Requirements_Master_Dataset.xls   525 labeled tickets (GOOD/BAD, Train/Test split)
│   ├── sample_upload_unlabeled.xls            same tickets without labels — use this to try the app
│   └── data_analysis_summary.xlsx
├── notebooks/01_EDA.ipynb    exploratory analysis and model comparison charts
├── scripts/
│   ├── train_and_evaluate.py hold-out training, model selection, hybrid report
│   └── cross_validate.py     5-fold CV of the three candidates
├── reports/                  scoring report, feature importance, scenario comparison, app_exports/
├── tests/                    pytest suite
├── docs/                     dissertation-report.pdf, final-presentation.pptx (public, redacted copies)
└── demo/                     demo-with-voiceover.mp4
```

## Data
The 525 tickets (`AML-001 …`) are a **synthetic / sanitised** requirements dataset written to cover data-ingestion, AML-scenario and non-functional requirement areas, balanced between actionable and "semantically hollow" tickets. Assignee / creator names are placeholders. No real production tickets are included.

## Results (reproducible from this repo)
| Evaluation | Random Forest | Logistic Regression | Linear SVM |
|---|---|---|---|
| Hold-out test (147 tickets) — F1 | 0.913 | 0.913 | 0.919 |
| 5-fold CV on all 525 — F1 | 0.964 | 0.964 | 0.964 |

Hold-out: `python scripts/train_and_evaluate.py`. CV: `python scripts/cross_validate.py`.

## Known gaps / honest notes
- `scripts/train_and_evaluate.py` selects the best hold-out model by F1 (currently Linear SVM) **and overwrites** `models/`. The committed `best_model.pkl` is the Random Forest used for the demo and report screenshots; retrain only if you want to replace it.
- The report's cross-validation table (Logistic Regression F1 0.959) and the CSVs `reports/all_scenarios_comparison.csv` / `feature_importance.csv` come from experiment code that was not committed. `cross_validate.py` re-implements the protocol and agrees to within ~0.5 pt F1, not to the last decimal.
- The chatbot's LLM mode needs a local [Ollama](https://ollama.com) server with `llama3`; without it, rule-based answers are used.

## Documents
- [Dissertation report (PDF)](docs/dissertation-report.pdf) — employer and individual names redacted for public release.
- [Final presentation](docs/final-presentation.pptx)
- [Demo video](demo/demo-with-voiceover.mp4)
