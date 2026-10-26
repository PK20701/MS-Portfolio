import os

import joblib
import pandas as pd
import pytest

from conftest import ROOT
from src.feature_engineering import FeatureEngineer
from src.hybrid_scorer import JiraHybridScorer
from src.preprocessing import DataPreprocessor
from src.rule_engine import JiraRuleEngine

GOOD_ROW = {
    "Summary": "Set up Unix server for data ingestion",
    "Description": "As a data engineer I want to provision a Unix server so that incoming files can be stored",
    "Acceptance criteria": "Given a new server request When the team provisions it Then it must have 500GB storage",
    "Priority": "High",
    "Assignee": "dev.one",
    "Due Date": "2026-09-30",
    "Category": "Technical Implementation",
    "Sub-Area": "DevOps & CI/CD",
}


def test_rule_engine_scores_complete_ticket_100():
    score, failed = JiraRuleEngine.evaluate_issue_compliance(pd.Series(GOOD_ROW))
    assert score == 100
    assert failed == []


def test_rule_engine_penalises_hollow_ticket():
    row = pd.Series({**GOOD_ROW, "Summary": "Fix this", "Description": "TBD",
                     "Acceptance criteria": "", "Due Date": "TBD", "Priority": None})
    score, failed = JiraRuleEngine.evaluate_issue_compliance(row)
    assert score < 50
    assert "Missing Acceptance Criteria" in failed
    assert "Due date is missing or invalid" in failed


def test_rule_weights_sum_to_100():
    empty = pd.Series({k: None for k in GOOD_ROW})
    score, failed = JiraRuleEngine.evaluate_issue_compliance(empty)
    assert score == 0 and len(failed) == 10


@pytest.mark.parametrize("weight,rule,ml,expected", [(60, 100, 0, 60), (50, 80, 40, 60), (100, 70, 10, 70), (0, 70, 10, 10)])
def test_hybrid_score_is_weighted_average(weight, rule, ml, expected):
    assert JiraHybridScorer(rule_engine_weight=weight).execute_hybrid_score_calculation(rule, ml) == pytest.approx(expected)


def test_quality_gate_threshold():
    scorer = JiraHybridScorer()
    assert scorer.classify_quality_tier(70) == "GOOD"
    assert scorer.classify_quality_tier(69.9) == "BAD"


def test_feature_engineering_flags_vague_terms():
    df = pd.DataFrame([
        {"Summary": "Fix this TBD", "Description": "placeholder text", "Acceptance criteria": "", "Quality_Label": "BAD"},
        {"Summary": "Clear title", "Description": "As a user I want X so that Y", "Acceptance criteria": "Given A When B Then C", "Quality_Label": "GOOD"},
    ])
    out = FeatureEngineer.engineer_features(DataPreprocessor.clean_data(df))
    assert out.loc[0, "vague_term_count"] >= 2
    assert out.loc[1, "vague_term_count"] == 0
    assert list(out["Label_Numeric"]) == [0, 1]


@pytest.fixture(scope="module")
def labeled_df():
    df = pd.read_excel(os.path.join(ROOT, "data", "Jira_Requirements_Master_Dataset.xls"))
    return FeatureEngineer.engineer_features(DataPreprocessor.clean_data(df))


def test_labeled_dataset_schema(labeled_df):
    assert len(labeled_df) == 525
    assert set(labeled_df["Quality_Label"]) == {"GOOD", "BAD"}
    assert set(labeled_df["Data_Split"]) == {"Train", "Test"}
    assert labeled_df["Issue key"].is_unique


def test_shipped_model_predicts_probabilities(labeled_df):
    model = joblib.load(os.path.join(ROOT, "models", "best_model.pkl"))
    probs = model.predict_proba(labeled_df[["Combined", "vague_term_density"]])[:, 1]
    assert len(probs) == len(labeled_df)
    assert ((probs >= 0) & (probs <= 1)).all()


def test_shipped_model_beats_chance_on_test_split(labeled_df):
    model = joblib.load(os.path.join(ROOT, "models", "best_model.pkl"))
    test = labeled_df[labeled_df["Data_Split"] == "Test"]
    preds = model.predict(test[["Combined", "vague_term_density"]])
    assert (preds == test["Label_Numeric"]).mean() > 0.85
