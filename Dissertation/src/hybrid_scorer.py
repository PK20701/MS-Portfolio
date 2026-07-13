# src/hybrid_scorer.py

class JiraHybridScorer:
    def __init__(self, rule_engine_weight=60):
        # Allow configurable weighting for sensitivity analysis in your thesis
        self.w_rule = rule_engine_weight / 100.0
        self.w_ml = (100.0 - rule_engine_weight) / 100.0
        
    def execute_hybrid_score_calculation(self, rule_score, ml_good_prob):
        """Calculates final score using the weighted average methodology."""
        return (rule_score * self.w_rule) + (ml_good_prob * self.w_ml)

    def classify_quality_tier(self, hybrid_score, gate_threshold=70.0):
        """Applies the quality gate threshold."""
        return 'GOOD' if hybrid_score >= gate_threshold else 'BAD'

    def generate_rag_explanation(self, rule_details, ml_prob, final_tier):
        """
        Generates contextual natural language feedback for the RAG interface.
        Explains the "Why" behind the score.
        """
        feedback = []
        
        # 1. Syntactic Explainability
        failed_rules = [rule for rule, passed in rule_details.items() if passed == 0]
        if failed_rules:
            feedback.append(f"Structural gaps detected: Failed {len(failed_rules)} rule(s) (e.g., {failed_rules[0]}).")
            
        # 2. Semantic Explainability
        if ml_prob < 50.0:
            feedback.append("Semantic analysis indicates the context is vague or lacks actionable developer instructions (Semantic Hollowing detected).")
        elif ml_prob >= 80.0:
            feedback.append("Semantic actionability is strong; the requirement context is clear.")

        # 3. Final Verdict
        if final_tier == 'BAD':
            feedback.insert(0, "⚠️ REJECTED: Requirement requires revision.")
        else:
            feedback.insert(0, "✅ APPROVED: Requirement meets quality gate standards.")
            
        return " | ".join(feedback)