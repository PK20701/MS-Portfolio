import streamlit as st
import pandas as pd
import joblib
import os
import plotly.express as px
import plotly.graph_objects as go
from sklearn.feature_extraction.text import TfidfVectorizer
from src.preprocessing import DataPreprocessor
from src.feature_engineering import FeatureEngineer
from src.rule_engine import JiraRuleEngine
from src.hybrid_scorer import JiraHybridScorer
from src.chatbot_engine import JiraAuditChatbot

st.set_page_config(page_title="Jira Quality Framework", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_file" not in st.session_state:
    st.session_state.current_file = None

if "selected_issue" not in st.session_state:
    st.session_state.selected_issue = None

st.title("A Hybrid Scoring Framework for Jira Requirement Quality")

# Configuration
st.sidebar.header("Configuration")
weight_rule = st.sidebar.slider("Rule Engine Weight (%)", 0, 100, 60, step=10)
threshold = st.sidebar.slider("Quality Threshold (%)", 50, 90, 70)

uploaded_file = st.file_uploader("Upload Jira Dataset", type=["csv", "xls", "xlsx"])

# Clear chat history when new file is uploaded
if uploaded_file:
    file_identifier = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.current_file != file_identifier:
        st.session_state.messages = []
        st.session_state.current_file = file_identifier
        st.session_state.selected_issue = None
        st.rerun()

if uploaded_file:
    # 1. Data Loading
    @st.cache_data
    def get_data(file):
        df = pd.read_excel(file) if file.name.endswith(('.xls', '.xlsx')) else pd.read_csv(file)
        df.columns = [c.strip() for c in df.columns]
        df = DataPreprocessor.clean_data(df)
        return FeatureEngineer.engineer_features(df)

    df = get_data(uploaded_file)

    # 2. Hybrid Scoring Engine
    @st.cache_resource
    def load_model():
        if os.path.exists("models/best_model.pkl"):
            return joblib.load("models/best_model.pkl")
        return None

    pipeline = load_model()
    scorer = JiraHybridScorer(rule_engine_weight=weight_rule)
    
    # Extract or create vectorizer
    vectorizer = None
    if pipeline:
        try:
            for name, transformer, column in pipeline.named_steps['prep'].transformers_:
                if name == 'text':
                    vectorizer = transformer
                    break
        except:
            pass
    
    if vectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        search_corpus = df["Issue key"].fillna("") + " " + df["Summary"].fillna("") + " " + df["Description"].fillna("")
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), sublinear_tf=True)
        vectorizer.fit(search_corpus)
    
    # Calculate scores
    rule_scores, ml_scores, hybrid_scores, tiers, explanations = [], [], [], [], []
    failed_rules_list = []
    
    for _, row in df.iterrows():
        r_score, r_reasons = JiraRuleEngine.evaluate_issue_compliance(row)
        
        if pipeline:
            try:
                input_data = pd.DataFrame({
                    'Combined': [row['Combined']],
                    'vague_term_density': [row.get('vague_term_density', 0)]
                })
                ml_prob = pipeline.predict_proba(input_data)[0][1] * 100
            except:
                ml_prob = 50.0
        else:
            ml_prob = 50.0
        
        hybrid = scorer.execute_hybrid_score_calculation(r_score, ml_prob)
        tier = "GOOD" if hybrid >= threshold else "BAD"
        
        exp = []
        if tier == "BAD":
            if ml_prob < 50: exp.append("Semantic hollowness: Vague language.")
            exp.extend(r_reasons)
        else: exp.append("Ticket meets standards.")
        
        rule_scores.append(r_score)
        ml_scores.append(ml_prob)
        hybrid_scores.append(hybrid)
        tiers.append(tier)
        explanations.append(" | ".join(exp))
        failed_rules_list.append(r_reasons)
    
    df['Rule_Score'], df['ML_Score'], df['Hybrid_Score'] = rule_scores, ml_scores, hybrid_scores
    df['Tier'], df['Explanation'] = tiers, explanations
    df['Failed_Rules'] = failed_rules_list

    # 3. Universal Filtering
    st.sidebar.subheader("Universal Filters")
    filters = {}
    exclude_cols = ['Summary', 'Description', 'Acceptance criteria', 'Combined', 'Issue key', 
                    'Quality_Label', 'Explanation', 'Tier', 'Label_Numeric', 'Rule_Score', 'ML_Score', 
                    'Hybrid_Score', 'Failed_Rules']
    
    for col in df.select_dtypes(include=['object']).columns:
        if col not in exclude_cols:
            filters[col] = st.sidebar.multiselect(col, df[col].unique())
    
    res_df = df.copy()
    for col, vals in filters.items():
        if vals: 
            res_df = res_df[res_df[col].isin(vals)]

    # 4. Tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Data Analysis", "RAG Chatbot"])
    
    # ============ TAB 1: DASHBOARD (ENHANCED) ============
    with tab1:
        # Summary Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Issues", len(res_df))
        c2.metric("GOOD Issues", len(res_df[res_df['Tier']=='GOOD']))
        c3.metric("Review Required", len(res_df[res_df['Tier']=='BAD']))
        c4.metric("Avg Score", f"{res_df['Hybrid_Score'].mean():.1f}%")
        
        st.divider()
        
        # Row 1: Distribution of Quality Scores (Histogram)
        st.subheader("Distribution of Quality Scores")
        
        fig = px.histogram(
            res_df, 
            x='Hybrid_Score',
            nbins=20,
            color='Tier',
            color_discrete_map={'GOOD': '#2ecc71', 'BAD': '#e74c3c'},
            title="Hybrid Score Distribution",
            labels={'Hybrid_Score': 'Hybrid Score (%)', 'count': 'Number of Tickets'},
            barmode='group'
        )
        
        fig.update_layout(
            xaxis=dict(
                range=[0, 105],
                tickmode='linear',
                tick0=0,
                dtick=5,
                title='Hybrid Score (%)'
            ),
            yaxis=dict(
                title='Number of Tickets',
                gridcolor='lightgray'
            ),
            bargap=0.05,
            height=400,
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        fig.add_vline(
            x=threshold, 
            line_dash="dash", 
            line_color="orange", 
            annotation_text=f"Threshold: {threshold}%", 
            annotation_position="top"
        )
        fig.add_vline(
            x=50, 
            line_dash="dot", 
            line_color="red", 
            annotation_text="Attention: 50%", 
            annotation_position="bottom"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Row 2: Average Score by Priority + Count by Category (Restored as Count)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Average Score by Priority")
            if 'Priority' in res_df.columns:
                avg_by_priority = res_df.groupby('Priority')['Hybrid_Score'].mean().reset_index()
                avg_by_priority = avg_by_priority.sort_values('Hybrid_Score', ascending=True)
                
                fig = px.bar(
                    avg_by_priority,
                    x='Hybrid_Score',
                    y='Priority',
                    orientation='h',
                    title="Average Hybrid Score by Priority",
                    labels={'Hybrid_Score': 'Average Score (%)', 'Priority': 'Priority'},
                    color='Hybrid_Score',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )
                fig.update_layout(
                    height=350,
                    xaxis_range=[0, 105],
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis_title='Average Score (%)',
                    yaxis_title='Priority'
                )
                fig.add_vline(x=threshold, line_dash="dash", line_color="orange", 
                             annotation_text=f"Threshold: {threshold}%", annotation_position="top")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Priority column not available in dataset")
        
        with col2:
            st.subheader("Count by Category")
            if 'Category' in res_df.columns:
                category_counts = res_df['Category'].value_counts().reset_index()
                category_counts.columns = ['Category', 'Count']
                category_counts = category_counts.sort_values('Count', ascending=False)
                
                fig = px.bar(
                    category_counts,
                    x='Category',
                    y='Count',
                    title="Number of Tickets by Category",
                    labels={'Count': 'Number of Tickets', 'Category': 'Category'},
                    color='Count',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    height=350,
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis_title='Category',
                    yaxis_title='Number of Tickets'
                )
                # Add count labels on bars
                fig.update_traces(texttemplate='%{y}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Category column not available in dataset")
        
        st.divider()
        
        # Row 3: Count by Status (Restored as Count) + Issues Needing Attention
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("Count by Status")
            if 'Status' in res_df.columns:
                status_counts = res_df['Status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                status_counts = status_counts.sort_values('Count', ascending=False)
                
                fig = px.bar(
                    status_counts,
                    x='Status',
                    y='Count',
                    title="Number of Tickets by Status",
                    labels={'Count': 'Number of Tickets', 'Status': 'Status'},
                    color='Count',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(
                    height=350,
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis_title='Status',
                    yaxis_title='Number of Tickets'
                )
                # Add count labels on bars
                fig.update_traces(texttemplate='%{y}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Status column not available in dataset")
        
        with col4:
            st.subheader("Issues Needing Attention (Score < 50%)")
            attention_issues = res_df[res_df['Hybrid_Score'] < 50]
            
            if not attention_issues.empty:
                display_df = attention_issues[['Issue key', 'Summary', 'Hybrid_Score', 'Rule_Score', 'ML_Score', 'Tier']].copy()
                display_df = display_df.sort_values('Hybrid_Score', ascending=True)
                display_df['Hybrid_Score'] = display_df['Hybrid_Score'].map(lambda x: f"{x:.1f}%")
                display_df['Rule_Score'] = display_df['Rule_Score'].map(lambda x: f"{x:.1f}%")
                display_df['ML_Score'] = display_df['ML_Score'].map(lambda x: f"{x:.1f}%")
                
                issue_options = [f"{row['Issue key']} - {row['Summary'][:50]}..." for _, row in attention_issues.head(20).iterrows()]
                issue_keys = attention_issues['Issue key'].tolist()
                
                selected_idx = st.selectbox(
                    "Select an issue to see detailed breakdown:",
                    options=range(len(issue_options)),
                    format_func=lambda i: issue_options[i] if i < len(issue_options) else "Select an issue"
                )
                
                if selected_idx is not None and selected_idx < len(issue_keys):
                    st.session_state.selected_issue = issue_keys[selected_idx]
            else:
                st.success("🎉 No issues with score below 50%! All tickets meet the attention threshold.")
                st.session_state.selected_issue = None
        
        st.divider()
        
        # ============ DETAILED BREAKDOWN SECTION ============
        if st.session_state.selected_issue:
            st.subheader(f"📋 Detailed Breakdown: {st.session_state.selected_issue}")
            
            issue_data = res_df[res_df['Issue key'] == st.session_state.selected_issue].iloc[0]
            
            b1, b2, b3 = st.columns(3)
            
            with b1:
                st.markdown("**Score Summary**")
                st.metric("Hybrid Score", f"{issue_data['Hybrid_Score']:.1f}%")
                st.metric("Rule Score", f"{issue_data['Rule_Score']:.1f}%")
                st.metric("ML Score", f"{issue_data['ML_Score']:.1f}%")
                st.metric("Tier", issue_data['Tier'])
            
            with b2:
                st.markdown("**Failed Rules**")
                failed_rules = issue_data.get('Failed_Rules', [])
                if failed_rules:
                    for rule in failed_rules:
                        st.error(f"❌ {rule}")
                else:
                    st.success("✅ All rules passed!")
                
                if abs(issue_data['Rule_Score'] - issue_data['ML_Score']) > 20:
                    st.warning(f"⚠️ **ML Warning:** ML Score ({issue_data['ML_Score']:.1f}%) differs from Rule Score ({issue_data['Rule_Score']:.1f}%) by more than 20 points")
            
            with b3:
                st.markdown("**Suggested Improvements**")
                suggestions = []
                
                if issue_data['Tier'] == 'BAD':
                    if 'ML_Score' in issue_data and issue_data['ML_Score'] < 50:
                        suggestions.append("• Improve semantic quality: Add more context, specific details, and clear requirements")
                    
                    if 'Rule_Score' in issue_data and issue_data['Rule_Score'] < 50:
                        suggestions.append("• Address structural gaps: Ensure all required fields are filled properly")
                    
                    if 'Summary' in issue_data and len(str(issue_data['Summary'])) < 20:
                        suggestions.append("• Expand Summary: Be more descriptive (currently too short)")
                    
                    if 'Description' in issue_data and len(str(issue_data['Description'])) < 50:
                        suggestions.append("• Enhance Description: Add more details and context")
                    
                    if 'Acceptance criteria' in issue_data and (pd.isna(issue_data['Acceptance criteria']) or len(str(issue_data['Acceptance criteria'])) < 10):
                        suggestions.append("• Add Acceptance Criteria: Define clear acceptance criteria")
                    
                    if 'Priority' in issue_data and pd.isna(issue_data['Priority']):
                        suggestions.append("• Set Priority: Assign a priority level to this ticket")
                    
                    if 'Assignee' in issue_data and pd.isna(issue_data['Assignee']):
                        suggestions.append("• Assignee: Assign this ticket to a specific person")
                    
                    failed_rules = issue_data.get('Failed_Rules', [])
                    for rule in failed_rules:
                        if "Summary too short" in rule:
                            suggestions.append("• Write a more descriptive summary (at least 10 characters)")
                        if "Description too short" in rule:
                            suggestions.append("• Expand the description with more details (at least 30 characters)")
                        if "Missing Acceptance Criteria" in rule:
                            suggestions.append("• Add acceptance criteria to define what 'done' means")
                        if "Missing User Story format" in rule:
                            suggestions.append("• Use User Story format: 'As a... I want... so that...'")
                        if "Due date is missing or invalid" in rule:
                            suggestions.append("• Set a valid due date for this ticket")
                        if "Missing Priority" in rule:
                            suggestions.append("• Assign a priority level (High/Medium/Low)")
                        if "Missing Category" in rule:
                            suggestions.append("• Select a category for better organization")
                        if "Missing Assignee" in rule:
                            suggestions.append("• Assign this ticket to a specific team member")
                        if "Missing Sub-area" in rule:
                            suggestions.append("• Specify a sub-area for more detailed categorization")
                
                if not suggestions:
                    suggestions.append("✅ This ticket meets all quality standards!")
                
                for suggestion in suggestions:
                    st.info(suggestion)
            
            with st.expander("View Full Ticket Details", expanded=False):
                st.write(f"**Summary:** {issue_data.get('Summary', 'N/A')}")
                st.write(f"**Description:** {issue_data.get('Description', 'N/A')}")
                if 'Acceptance criteria' in issue_data:
                    st.write(f"**Acceptance Criteria:** {issue_data.get('Acceptance criteria', 'N/A')}")
                if 'Explanation' in issue_data:
                    st.write(f"**Quality Analysis:** {issue_data.get('Explanation', 'N/A')}")

    # ============ TAB 2: DATA ANALYSIS (UNCHANGED) ============
    with tab2:
        st.subheader("Data Analysis & Hypothesis Validation")
        rule_rejections = res_df[res_df['Rule_Score'] < threshold]
        ml_rejections = res_df[res_df['ML_Score'] < threshold]
        hybrid_rejections = res_df[res_df['Tier'] == 'BAD']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Rule-Only Rejections", len(rule_rejections))
        c2.metric("ML-Only Rejections", len(ml_rejections))
        c3.metric("Hybrid Rejections", len(hybrid_rejections))
        
        additional = max(0, len(hybrid_rejections) - len(rule_rejections))
        st.success(f"Framework Sensitivity: {additional} additional issues identified by Hybrid ML.")
        
        search_id = st.text_input("Filter by Issue ID:", key="audit_filter")
        view_df = res_df[res_df['Issue key'].astype(str).str.contains(search_id, case=False)] if search_id else res_df
        st.dataframe(view_df[['Issue key', 'Rule_Score', 'ML_Score', 'Hybrid_Score', 'Tier', 'Explanation', 'Summary', 'Description', 'Acceptance criteria']], use_container_width=True)

    # ============ TAB 3: RAG CHATBOT ============
    with tab3:
        st.subheader("Conversational Auditor")
        
        col1, col2, col3 = st.columns([1, 4, 1])
        with col1:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        with st.expander("📋 What I can help with", expanded=False):
            st.markdown("""
            **Ticket Lookup**
            • `what is AML-809` - Get full ticket details
            
            **Statistics**
            • `average rule score` - Get average scores
            • `average score for high priority tickets` - Average with filters
            
            **Distribution Analysis**
            • `distribution by status` - Breakdown by status
            • `distribution by priority` - Breakdown by priority
            
            **Filtered Lists**
            • `show me high priority tickets` - List tickets by priority
            • `show me tickets assigned to Sarah` - List by assignee
            
            **Count Queries**
            • `how many tickets are in backlog` - Count by status
            • `how many high priority tickets` - Count by priority
            
            **Due Date Queries**
            • `tickets due this month` - Upcoming tickets
            • `overdue tickets` - Past due tickets
            """)
        
        st.divider()
        
        if st.session_state.messages:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    if msg["role"] == "assistant":
                        st.markdown(msg["content"])
                    else:
                        st.write(msg["content"])
        else:
            st.info("💡 Ask me about your Jira tickets! Try: `average rule score` or `show me high priority tickets`")
        
        query = st.chat_input("Ask about tickets (e.g., AML-809) or analysis:")
        
        if query:
            st.session_state.messages.append({"role": "user", "content": query})
            
            bot = JiraAuditChatbot(df, vectorizer, pipeline)
            result = bot.evaluate_user_input_intent(query, threshold_gate=threshold)
            
            response = result.get("content", "I don't understand. Please try a different question.")
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()