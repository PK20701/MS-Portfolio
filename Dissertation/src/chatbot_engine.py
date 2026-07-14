# chatbot_engine.py
# Optimized for server - LLM calls disabled on Streamlit Cloud

import pandas as pd
import requests
import re
from datetime import datetime
import os

class JiraAuditChatbot:
    def __init__(self, df, vectorizer, ml_pipeline=None):
        self.project_data = df
        self.text_vectorizer = vectorizer
        self.ml_pipeline = ml_pipeline
        self.support_contact = "Prasanna Kamthekar"
        self.bot_name = "Jira Quality Assistant"
        
        # Detect if running on server
        self.is_server = os.environ.get('STREAMLIT_SHARING') == 'true' or 'STREAMLIT_SERVER' in os.environ
        
        # Only initialize Ollama if NOT on server
        if not self.is_server:
            self.ollama_endpoint = "http://127.0.0.1:11434/api/generate"
            self.local_model_name = "llama3:latest"
        else:
            self.ollama_endpoint = None
            self.local_model_name = None
    
    def check_ollama_health(self):
        """Skip Ollama check on server"""
        if self.is_server:
            return False
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def extract_ticket_keys(self, text):
        pattern = r'[A-Z]+-\d+'
        return re.findall(pattern, text.upper())
    
    def get_ticket_data(self, ticket_key):
        match = self.project_data[self.project_data["Issue key"].astype(str).str.strip().str.upper() == ticket_key]
        if not match.empty:
            return match.iloc[0]
        return None
    
    def format_ticket_response(self, record):
        response = f"**Ticket:** {record['Issue key']}\n\n"
        response += f"• **Rule Score:** {record['Rule_Score']:.1f}%\n"
        response += f"• **ML Score:** {record['ML_Score']:.1f}%\n"
        response += f"• **Hybrid Score:** {record['Hybrid_Score']:.1f}% ({record['Tier']})\n"
        response += f"• **Summary:** {record['Summary']}\n"
        if 'Priority' in record and pd.notna(record['Priority']):
            response += f"• **Priority:** {record['Priority']}\n"
        if 'Status' in record and pd.notna(record['Status']):
            response += f"• **Status:** {record['Status']}\n"
        if 'Assignee' in record and pd.notna(record['Assignee']):
            response += f"• **Assignee:** {record['Assignee']}\n"
        if 'Due Date' in record and pd.notna(record['Due Date']):
            due_date = str(record['Due Date'])
            if ' ' in due_date:
                due_date = due_date.split(' ')[0]
            response += f"• **Due Date:** {due_date}\n"
        if 'Category' in record and pd.notna(record['Category']):
            response += f"• **Category:** {record['Category']}\n"
        response += f"• **Quality Analysis:** {record.get('Explanation', 'N/A')}"
        return response
    
    def format_ticket_list_response(self, tickets, title="Found matching tickets"):
        if tickets.empty:
            return "No tickets found."
        
        response = f"**{title}:**\n\n"
        for i, (_, row) in enumerate(tickets.iterrows(), 1):
            response += f"{i}. **{row['Issue key']}**\n"
            response += f"   • Score: {row['Hybrid_Score']:.1f}% ({row['Tier']})\n"
            if 'Priority' in row and pd.notna(row['Priority']):
                response += f"   • Priority: {row['Priority']}\n"
            if 'Status' in row and pd.notna(row['Status']):
                response += f"   • Status: {row['Status']}\n"
            if 'Assignee' in row and pd.notna(row['Assignee']):
                response += f"   • Assignee: {row['Assignee']}\n"
            response += f"   • Summary: {row['Summary'][:80]}...\n\n"
        return response
    
    def is_irrelevant_query(self, query_lower):
        irrelevant_patterns = [
            r'what is your name', r'who are you', r'what are you',
            r'how are you', r'hello', r'hi there', r'good morning',
            r'thanks', r'thank you', r'bye', r'goodbye'
        ]
        for pattern in irrelevant_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def get_irrelevant_response(self):
        return f"I am **{self.bot_name}**.\n\nI can help with:\n• Ticket lookup (e.g., 'what is AML-809')\n• Statistics (e.g., 'average rule score')\n• Distributions (e.g., 'distribution by status')\n• Filtered lists (e.g., 'show me high priority tickets')\n• Counts (e.g., 'how many tickets in backlog')\n\nAsk me about your Jira data!"
    
    def parse_query_conditions_structural(self, query_lower):
        conditions = {
            'priority': None,
            'status': None,
            'assignee': None,
            'score_type': 'Hybrid_Score',
            'score_operator': '<',
            'score_threshold': None,
            'is_average_query': False
        }
        
        if 'average' in query_lower or 'avg' in query_lower or 'mean' in query_lower:
            conditions['is_average_query'] = True
        
        priority_keywords = {
            'critical': ['critical', 'highest'],
            'high': ['high', 'major'],
            'medium': ['medium', 'normal'],
            'low': ['low', 'minor']
        }
        for priority, keywords in priority_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                conditions['priority'] = priority
                break
        
        status_keywords = ['backlog', 'todo', 'in progress', 'open', 'closed', 'done', 'review', 'testing']
        for status in status_keywords:
            if status in query_lower:
                conditions['status'] = status
                break
        
        common_words = ['tickets', 'score', 'priority', 'status', 'distribution', 'review', 'all', 'any', 'high', 'medium', 'low', 'critical']
        assignee_match = re.search(r'(?:to|for|by|assigned to)\s+([a-zA-Z_\.]+)', query_lower)
        if assignee_match:
            assignee_name = assignee_match.group(1).lower()
            if assignee_name not in common_words:
                conditions['assignee'] = assignee_name
        
        score_match = re.search(r'(?:less than|<|<=)\s*(\d+)%', query_lower)
        if score_match:
            conditions['score_threshold'] = int(score_match.group(1))
            conditions['score_operator'] = '<'
        
        if 'rule' in query_lower and 'ml' not in query_lower:
            conditions['score_type'] = 'Rule_Score'
        elif 'ml' in query_lower or 'machine learning' in query_lower:
            conditions['score_type'] = 'ML_Score'
        
        return conditions
    
    def execute_query_from_conditions(self, conditions):
        filtered = self.project_data.copy()
        filter_description = []
        
        if conditions.get('priority'):
            if 'Priority' in filtered.columns:
                filtered = filtered[filtered['Priority'].astype(str).str.lower().str.contains(conditions['priority'], na=False)]
                filter_description.append(f"Priority: {conditions['priority'].title()}")
        
        if conditions.get('status'):
            if 'Status' in filtered.columns:
                filtered = filtered[filtered['Status'].astype(str).str.lower().str.contains(conditions['status'], na=False)]
                filter_description.append(f"Status: {conditions['status'].title()}")
        
        if conditions.get('assignee'):
            if 'Assignee' in filtered.columns:
                filtered = filtered[filtered['Assignee'].astype(str).str.lower().str.contains(conditions['assignee'].lower(), na=False)]
                filter_description.append(f"Assignee: {conditions['assignee']}")
        
        if conditions.get('score_threshold') is not None:
            score_col = conditions.get('score_type', 'Hybrid_Score')
            if score_col in filtered.columns:
                filtered = filtered[filtered[score_col] < conditions['score_threshold']]
                filter_description.append(f"{score_col.replace('_', ' ')} < {conditions['score_threshold']}%")
        
        return filtered, filter_description
    
    def handle_average_query(self, query_lower):
        conditions = self.parse_query_conditions_structural(query_lower)
        filtered_data, filter_description = self.execute_query_from_conditions(conditions)
        total_count = len(filtered_data)
        
        if total_count == 0:
            response = "**No tickets found.**\n\n"
            if filter_description:
                response += "Filters applied:\n"
                for desc in filter_description:
                    response += f"• {desc}\n"
            response += f"\nTotal in dataset: {len(self.project_data)} tickets"
            return response
        
        score_col = conditions.get('score_type', 'Hybrid_Score')
        avg_score = filtered_data[score_col].mean()
        
        response = f"**Average {score_col.replace('_', ' ')} for {total_count} tickets**\n\n"
        for desc in filter_description:
            response += f"• {desc}\n"
        response += f"\n• **Average:** {avg_score:.1f}%\n"
        response += f"• **Range:** {filtered_data[score_col].min():.1f}% - {filtered_data[score_col].max():.1f}%\n"
        
        if 'Tier' in filtered_data.columns:
            good = len(filtered_data[filtered_data['Tier'] == 'GOOD'])
            bad = len(filtered_data[filtered_data['Tier'] == 'BAD'])
            response += f"• **GOOD:** {good} | **BAD:** {bad}\n"
        
        if total_count > 0:
            response += f"\n**Sample tickets:**\n"
            for i, (_, row) in enumerate(filtered_data.head(3).iterrows(), 1):
                response += f"{i}. {row['Issue key']} - {row[score_col]:.1f}%\n"
        
        return response
    
    def handle_distribution_query(self, query_lower, conditions):
        filtered_data, filter_description = self.execute_query_from_conditions(conditions)
        total_count = len(filtered_data)
        
        dist_type = None
        if "priority" in query_lower:
            dist_type = "Priority"
        elif "status" in query_lower:
            dist_type = "Status"
        elif "assignee" in query_lower or "assigned" in query_lower:
            dist_type = "Assignee"
        elif "category" in query_lower:
            dist_type = "Category"
        
        if dist_type is None:
            for col in ['Priority', 'Status', 'Assignee', 'Category']:
                if col.lower() in query_lower:
                    dist_type = col
                    break
        
        if dist_type is None:
            if 'Tier' in filtered_data.columns:
                response = f"**Ticket Distribution**"
                if filter_description:
                    response += " (" + ", ".join([d.lower() for d in filter_description]) + ")"
                
                if total_count == 0:
                    response += "\n\nNo tickets found."
                else:
                    response += f"\nTotal: {total_count} tickets\n\n"
                    dist = filtered_data['Tier'].value_counts()
                    for item, count in dist.items():
                        pct = (count / total_count) * 100
                        response += f"• {item}: {count} tickets ({pct:.1f}%)\n"
                return response
        
        if total_count == 0:
            response = f"**No tickets found for {dist_type or 'distribution'}.**\n\n"
            if filter_description:
                response += "Filters applied:\n"
                for desc in filter_description:
                    response += f"• {desc}\n"
            response += f"\nTotal in dataset: {len(self.project_data)} tickets"
            return response
        
        if dist_type and dist_type in filtered_data.columns:
            dist_data = filtered_data[filtered_data[dist_type].notna()]
            dist_data = dist_data[dist_data[dist_type].astype(str).str.strip() != '']
            
            if dist_data.empty:
                return f"No valid {dist_type.lower()} data found for these tickets."
            
            response = f"**{dist_type} Distribution**"
            if filter_description:
                response += " (" + ", ".join([d.lower() for d in filter_description]) + ")"
            response += f"\nTotal: {total_count} tickets\n\n"
            
            dist = dist_data[dist_type].value_counts()
            for item, count in dist.items():
                pct = (count / total_count) * 100
                response += f"• {item}: {count} tickets ({pct:.1f}%)\n"
            
            return response
        else:
            response = f"**{dist_type} column not found.**\n\nAvailable columns for distribution:\n"
            for col in ['Priority', 'Status', 'Assignee', 'Category', 'Tier']:
                if col in filtered_data.columns:
                    response += f"• {col}\n"
            return response
    
    def evaluate_user_input_intent(self, query, threshold_gate=70.0):
        """Main entry point - No LLM on server"""
        try:
            clean_query = query.strip()
            query_lower = clean_query.lower()
            
            # ============ STEP 1: CHECK IRRELEVANT QUERIES ============
            if self.is_irrelevant_query(query_lower):
                return {"type": "irrelevant", "content": self.get_irrelevant_response()}
            
            # ============ STEP 2: TICKET LOOKUP ============
            ticket_keys = self.extract_ticket_keys(query)
            
            if not ticket_keys:
                no_hyphen_match = re.search(r'([A-Za-z]+)(\d{2,4})', query.upper())
                if no_hyphen_match:
                    possible_ticket = f"{no_hyphen_match.group(1)}-{no_hyphen_match.group(2)}"
                    if possible_ticket in self.project_data["Issue key"].astype(str).values:
                        ticket_keys = [possible_ticket]
            
            if ticket_keys:
                found_tickets = []
                for ticket in ticket_keys:
                    record = self.get_ticket_data(ticket)
                    if record is not None:
                        found_tickets.append(record)
                
                if found_tickets:
                    if len(found_tickets) > 1:
                        response = "**Multiple Tickets Found:**\n\n"
                        for record in found_tickets:
                            response += self.format_ticket_response(record) + "\n\n"
                        return {"type": "ticket_data", "content": response}
                    else:
                        return {"type": "ticket_data", "content": self.format_ticket_response(found_tickets[0])}
                
                return {
                    "type": "ticket_not_found",
                    "content": f"**Ticket not found.**\n\nPlease use format: **'AML-829'** (with hyphen).\n\nContact {self.support_contact} if needed."
                }
            
            # ============ STEP 3: AVERAGE QUERIES ============
            if "average" in query_lower or "avg" in query_lower or "mean" in query_lower:
                response = self.handle_average_query(query_lower)
                return {"type": "metric_display", "content": response}
            
            # ============ STEP 4: DISTRIBUTION QUERIES ============
            if "distribution" in query_lower or "breakdown" in query_lower or "wise" in query_lower:
                conditions = self.parse_query_conditions_structural(query_lower)
                response = self.handle_distribution_query(query_lower, conditions)
                return {"type": "metric_display", "content": response}
            
            # ============ STEP 5: COUNT QUERIES ============
            if "how many" in query_lower or "count" in query_lower:
                conditions = self.parse_query_conditions_structural(query_lower)
                filtered_data, filter_description = self.execute_query_from_conditions(conditions)
                total_count = len(filtered_data)
                response = f"**Found {total_count} tickets**"
                if filter_description:
                    response += "\n\nFilters applied:\n"
                    for desc in filter_description:
                        response += f"• {desc}\n"
                return {"type": "metric_display", "content": response}
            
            # ============ STEP 6: SHOW/LIST QUERIES ============
            if "show" in query_lower or "list" in query_lower or "find" in query_lower:
                conditions = self.parse_query_conditions_structural(query_lower)
                filtered_data, filter_description = self.execute_query_from_conditions(conditions)
                total_count = len(filtered_data)
                
                if total_count == 0:
                    response = "**No tickets found.**\n\n"
                    if filter_description:
                        for desc in filter_description:
                            response += f"• {desc}\n"
                    return {"type": "metric_display", "content": response}
                
                response = f"**Found {total_count} tickets**\n\n"
                if filter_description:
                    for desc in filter_description:
                        response += f"• {desc}\n"
                    response += "\n"
                
                for i, (_, row) in enumerate(filtered_data.head(10).iterrows(), 1):
                    response += f"{i}. **{row['Issue key']}**\n"
                    response += f"   • Score: {row['Hybrid_Score']:.1f}% ({row['Tier']})\n"
                    if 'Priority' in row and pd.notna(row['Priority']):
                        response += f"   • Priority: {row['Priority']}\n"
                    if 'Status' in row and pd.notna(row['Status']):
                        response += f"   • Status: {row['Status']}\n"
                    response += f"   • {row['Summary'][:80]}...\n\n"
                
                if total_count > 10:
                    response += f"\n... and {total_count - 10} more tickets."
                return {"type": "metric_display", "content": response}
            
            # ============ STEP 7: DUE DATE QUERIES ============
            if "due" in query_lower or "overdue" in query_lower:
                if 'Due Date' in self.project_data.columns:
                    try:
                        self.project_data['Due_Date_DateTime'] = pd.to_datetime(
                            self.project_data['Due Date'], 
                            errors='coerce'
                        )
                        
                        if "overdue" in query_lower:
                            today = pd.Timestamp.now()
                            overdue_tickets = self.project_data[
                                self.project_data['Due_Date_DateTime'] < today
                            ]
                            overdue_tickets = overdue_tickets[overdue_tickets['Due_Date_DateTime'].notna()]
                            
                            if not overdue_tickets.empty:
                                response = f"**Overdue Tickets ({len(overdue_tickets)} tickets)**\n\n"
                                for _, row in overdue_tickets.head(10).iterrows():
                                    due_date_str = row['Due_Date_DateTime'].strftime('%b %d, %Y')
                                    response += f"• {row['Issue key']} - Due: {due_date_str} - {row['Summary'][:60]}...\n"
                                return {"type": "metric_display", "content": response}
                            else:
                                return {"type": "metric_display", "content": "**No overdue tickets found.**"}
                        
                        if "this month" in query_lower:
                            current_month = datetime.now().month
                            current_year = datetime.now().year
                            due_tickets = self.project_data[
                                (self.project_data['Due_Date_DateTime'].dt.month == current_month) & 
                                (self.project_data['Due_Date_DateTime'].dt.year == current_year)
                            ]
                            due_tickets = due_tickets[due_tickets['Due_Date_DateTime'].notna()]
                            
                            if not due_tickets.empty:
                                month_name = datetime.now().strftime('%B')
                                response = f"**Tickets Due in {month_name} ({len(due_tickets)} tickets)**\n\n"
                                for _, row in due_tickets.head(10).iterrows():
                                    due_date_str = row['Due_Date_DateTime'].strftime('%b %d, %Y')
                                    response += f"• {row['Issue key']} - Due: {due_date_str} - {row['Summary'][:60]}...\n"
                                return {"type": "metric_display", "content": response}
                            else:
                                return {"type": "metric_display", "content": f"**No tickets due this month.**"}
                    except:
                        pass
            
            # ============ STEP 8: ANOMALY DETECTION ============
            if "max rule" in query_lower and ("ml" in query_lower or "low ml" in query_lower):
                if 'Rule_Score' in self.project_data.columns and 'ML_Score' in self.project_data.columns:
                    self.project_data["Variance"] = self.project_data["Rule_Score"] - self.project_data["ML_Score"]
                    target = self.project_data.sort_values(by="Variance", ascending=False).iloc[0]
                    return {
                        "type": "anomaly",
                        "content": f"**High-Rule / Low-ML Divergence**\n\n"
                                  f"• Ticket: {target['Issue key']}\n"
                                  f"• Rule Score: {target['Rule_Score']:.1f}%\n"
                                  f"• ML Score: {target['ML_Score']:.1f}%\n"
                                  f"• Difference: {target['Variance']:.1f}%\n\n"
                                  f"Summary: {target['Summary']}\n\n"
                                  f"Description: {target['Description']}"
                    }
            
            # ============ STEP 9: SEMANTIC SEARCH (FALLBACK) ============
            if self.text_vectorizer is not None:
                try:
                    search_corpus = self.project_data["Issue key"].fillna("") + " " + \
                                  self.project_data["Summary"].fillna("") + " " + \
                                  self.project_data["Description"].fillna("")
                    
                    corpus_vectors = self.text_vectorizer.transform(search_corpus)
                    query_vector = self.text_vectorizer.transform([query])
                    
                    dot_product_scores = (corpus_vectors * query_vector.T).toarray().flatten()
                    matched_indices = [idx for idx in dot_product_scores.argsort()[::-1] 
                                     if dot_product_scores[idx] > 0.05][:3]
                    
                    if matched_indices:
                        matched_tickets = self.project_data.loc[matched_indices]
                        response = f"**Found matching tickets:**\n\n"
                        for i, (_, row) in enumerate(matched_tickets.iterrows(), 1):
                            response += f"{i}. **{row['Issue key']}**\n"
                            response += f"   • Score: {row['Hybrid_Score']:.1f}% ({row['Tier']})\n"
                            if 'Priority' in row and pd.notna(row['Priority']):
                                response += f"   • Priority: {row['Priority']}\n"
                            if 'Status' in row and pd.notna(row['Status']):
                                response += f"   • Status: {row['Status']}\n"
                            response += f"   • {row['Summary'][:80]}...\n\n"
                        return {"type": "text_matches", "content": response}
                except:
                    pass
            
            # ============ STEP 10: UNMATCHED QUERY ============
            return {
                "type": "unmatched_fallback",
                "content": f"**I don't understand that query.**\n\nTry these examples:\n• 'AML-809' - Look up a ticket\n• 'average rule score' - Statistics\n• 'distribution by status' - Distribution\n• 'show me high priority tickets' - List tickets\n• 'how many tickets in backlog' - Count\n\nContact {self.support_contact} if stuck."
            }
            
        except Exception as e:
            return {
                "type": "error",
                "content": f"**Sorry, I encountered an error.**\n\nError: {str(e)}\n\nPlease try rephrasing your question or contact {self.support_contact} for assistance."
            }