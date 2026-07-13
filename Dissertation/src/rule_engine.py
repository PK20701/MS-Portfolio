import pandas as pd

class JiraRuleEngine:
    @staticmethod
    def evaluate_issue_compliance(row):
        """
        Validates Jira issue against 10 rules with defined weights.
        Returns: (score, failed_reasons)
        """
        # --- 1. EDA Preprocessing ---
        def clean(val):
            s = str(val).strip()
            # Handle NaN, none, null strings or empty values
            return "" if s.lower() in ["nan", "none", "null"] else s
            
        summary = clean(row.get("Summary", ""))
        desc = clean(row.get("Description", ""))
        ac = clean(row.get("Acceptance criteria", ""))
        
        # --- 2. Valid Date Logic ---
        due_date_raw = row.get("Due Date")
        is_date_valid = False
        if pd.notnull(due_date_raw) and str(due_date_raw).lower() not in ["nan", "none", "null", ""]:
            try:
                # Attempts to parse valid date; if it fails, it remains False
                pd.to_datetime(due_date_raw)
                is_date_valid = True
            except (ValueError, TypeError):
                is_date_valid = False

        # --- 3. Rule Definitions & Weights ---
        # Format: (Weight, Condition, Failure Message)
        # Weights sum to exactly 100
        rules_config = [
            (10, len(summary) > 10, "Summary too short"),
            (15, len(desc) > 30, "Description too short"),
            (15, ac != "", "Missing Acceptance Criteria"),
            (10, len(ac) > 20 and any(x in ac.lower() for x in ["given", "when", "then"]), "AC not in Gherkin format"),
            (15, "as a" in desc.lower() and "i want" in desc.lower(), "Missing User Story format"),
            (10,  is_date_valid, "Due date is missing or invalid"), 
            (10, clean(row.get("Priority")) != "", "Missing Priority"),
            (5, clean(row.get("Category")) != "", "Missing Category"),
            (5, clean(row.get("Assignee")) != "", "Missing Assignee"),
            (10, clean(row.get("Sub-Area")) != "", "Missing Sub-area")
        ]

        # --- 4. Scoring Calculation ---
        score = 100
        failed_reasons = []
        
        for weight, passed, message in rules_config:
            if not passed:
                score -= weight
                failed_reasons.append(message)
        
        # Ensure score does not drop below 0
        return max(0, score), failed_reasons