import pandas as pd
import os
import joblib
from src.preprocessing import DataPreprocessor
from src.feature_engineering import FeatureEngineer
from src.ml_pipeline import RequirementMLPipeline
from src.rule_engine import JiraRuleEngine
from src.hybrid_scorer import JiraHybridScorer

# 1. Logging: Execution start
print("="*60)
print("--- [LOG] Starting Dissertation Mid-Sem Demo ---")
print("="*60)

# Load data
print("[*] Loading data from ./data/Jira_Requirements_Master_Dataset.xls...")
df = pd.read_excel("./data/Jira_Requirements_Master_Dataset.xls")
print(f"[✓] Data loaded successfully. Total records: {len(df)}")



# Preprocessing
print("[*] Running Data Preprocessing...")
df = DataPreprocessor.clean_data(df)

# Feature Engineering
print("[*] Running Feature Engineering...")
df = FeatureEngineer.engineer_features(df)

# 2. Pipeline Execution
print("\n" + "="*60)
print("--- ML PIPELINE EXECUTION ---")
pipeline = RequirementMLPipeline(use_vague_feature=True)

# Now trains and returns the metrics and the best model object
metrics_df, best_model, best_name, best_f1 = pipeline.execute_validation_matrix(df)

print("\n--- ACADEMIC PERFORMANCE METRICS ---")
print(metrics_df.to_string(index=False))

print("\n" + "="*60)
print(f"BEST MODEL SELECTED: {best_name}")
print(f"F1 Score of Best Model: {best_f1:.4f}")
print("Best Model Pipeline Steps:", list(best_model.named_steps.keys()))
print("="*60)

# 3. Hybrid Scoring for Test Set (BATCH PROCESSING FIX)
print("\n[*] Running Hybrid Scoring on dataset...")
# 1. Filter only for Test records
test_df = df[df['Data_Split'] == 'Test'].copy()
# Pass the entire dataframe to the pipeline to ensure consistent TF-IDF transformation
# The pipeline handles the ColumnTransformer internally
test_features = test_df[['Combined', 'vague_term_density']]
ml_probs = best_model.predict_proba(test_features)[:, 1] * 100
test_df['ml_score_final'] = ml_probs

scorer = JiraHybridScorer()
report_data = []
# 4. Loop ONLY through test_df
for _, row in test_df.iterrows():
    # Calculate Rule Score
    rule_score, rule_reasons = JiraRuleEngine.evaluate_issue_compliance(row)
    
    # Use the pre-calculated ML score
    ml_prob = row['ml_score_final']
    
    # Hybrid Calculation
    hybrid = scorer.execute_hybrid_score_calculation(rule_score, ml_prob)
    tier = scorer.classify_quality_tier(hybrid)
    
    # 5. Explanation Logic
    explanation_list = []
    if tier == "BAD":
        # Semantic hollowness check
        if ml_prob < 50:
            explanation_list.append("Semantic hollowness: Vague statement detected")
        
        # Add ALL rule failures
        explanation_list.extend(rule_reasons)
        final_explanation = " | ".join(explanation_list)
    else:
        final_explanation = "Ticket meets quality standards"
    
    # Populate record
    entry = {
        "Issue Key": row['Issue key'],
        "Rule Score": round(rule_score, 2),
        "ML Score": round(ml_prob, 2),
        "Hybrid Score": round(hybrid, 2),
        "Tier": tier
    }
    
    # Add Details
    entry["Explanation"] = final_explanation
    entry["Summary"] = row.get('Summary', "")
    entry["Acceptance criteria"] = row.get('Acceptance criteria', "")
    entry["Description"] = row.get('Description', "")
    
    report_data.append(entry)

# Save Report
os.makedirs("reports", exist_ok=True)
pd.DataFrame(report_data).to_csv("reports/hybrid_scoring_report.csv", index=False)
print("[✓] Report saved to reports/hybrid_scoring_report.csv")
print("="*60)