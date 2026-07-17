import streamlit as st
import pandas as pd
import joblib
import pickle
import os
import base64
import plotly.express as px
import plotly.graph_objects as go
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler
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
        file_name = file.name.lower()
        
        try:
            if file_name.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')
            elif file_name.endswith('.xls'):
                try:
                    df = pd.read_excel(file, engine='xlrd')
                except:
                    file.seek(0)
                    df = pd.read_csv(file, encoding='utf-8')
            else:
                df = pd.read_csv(file, encoding='utf-8')
        except Exception as e:
            st.warning(f"Excel reading failed ({e}), trying as CSV...")
            file.seek(0)
            df = pd.read_csv(file, encoding='utf-8')
        
        df.columns = [c.strip() for c in df.columns]
        df = DataPreprocessor.clean_data(df)
        return FeatureEngineer.engineer_features(df)

    df = get_data(uploaded_file)

    # ============ 2. MODEL LOADING OR TRAINING ============
    @st.cache_resource
    def get_or_train_model(data_df):
        """Load existing model or train a new one if labels exist"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Create models directory if it doesn't exist
            models_dir = os.path.join(current_dir, "models")
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
            
            model_path = os.path.join(models_dir, "best_model.pkl")
            vectorizer_path = os.path.join(models_dir, "vectorizer.pkl")
            
            # Check if we have training labels
            has_labels = 'Label_Numeric' in data_df.columns
            
            # Try to load existing model
            if os.path.exists(model_path):
                try:
                    model = joblib.load(model_path)
                    vectorizer = None
                    if os.path.exists(vectorizer_path):
                        vectorizer = joblib.load(vectorizer_path)
                    return model, vectorizer, False
                except Exception as e:
                    st.sidebar.warning(f"Model load failed, retraining...")
            
            # Train new model if labels exist
            if has_labels:
                st.sidebar.info("📊 Training ML model...")
                
                X = data_df[['Combined', 'vague_term_density']]
                y = data_df['Label_Numeric']
                
                # Remove rows with missing labels
                valid_mask = y.notna()
                X = X[valid_mask]
                y = y[valid_mask]
                
                if len(X) > 0 and y.nunique() >= 2:
                    try:
                        # Create pipeline
                        text_transformer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), sublinear_tf=True)
                        preprocessor = ColumnTransformer([
                            ('text', text_transformer, 'Combined'),
                            ('num', MinMaxScaler(), ['vague_term_density'])
                        ])
                        
                        model = Pipeline([
                            ('prep', preprocessor),
                            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
                        ])
                        
                        # Train
                        model.fit(X, y)
                        
                        # Save model
                        joblib.dump(model, model_path)
                        
                        # Save vectorizer
                        vectorizer = model.named_steps['prep'].named_transformers_['text']
                        joblib.dump(vectorizer, vectorizer_path)
                        
                        st.sidebar.success(f"✅ Model trained ({len(X)} samples)")
                        return model, vectorizer, True
                        
                    except Exception as e:
                        st.sidebar.error(f"Training failed: {e}")
                        return None, None, False
                else:
                    st.sidebar.warning("⚠️ Need both GOOD and BAD samples")
                    return None, None, False
            else:
                st.sidebar.warning("⚠️ No Quality_Label column found")
                return None, None, False
                
        except Exception as e:
            st.sidebar.error(f"Model error: {str(e)}")
            return None, None, False

    pipeline, vectorizer, is_newly_trained = get_or_train_model(df)
    scorer = JiraHybridScorer(rule_engine_weight=weight_rule)
    
    # ============ 2.5 DOWNLOAD MODEL (IF NEWLY TRAINED) ============
    if is_newly_trained:
        st.sidebar.markdown("---")
        st.sidebar.info("📥 Model trained successfully! Download it to persist:")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "models", "best_model.pkl")
        
        # Read and create download button for model
        with open(model_path, "rb") as f:
            model_bytes = f.read()
            b64_model = base64.b64encode(model_bytes).decode()
            href_model = f'<a href="data:file/pkl;base64,{b64_model}" download="best_model.pkl" style="text-decoration:none;background-color:#4CAF50;color:white;padding:8px 16px;border-radius:4px;display:inline-block;">📥 Download best_model.pkl</a>'
            st.sidebar.markdown(href_model, unsafe_allow_html=True)
        
        # Read and create download button for vectorizer
        vectorizer_path = os.path.join(current_dir, "models", "vectorizer.pkl")
        if os.path.exists(vectorizer_path):
            with open(vectorizer_path, "rb") as f:
                vectorizer_bytes = f.read()
                b64_vectorizer = base64.b64encode(vectorizer_bytes).decode()
                href_vectorizer = f'<a href="data:file/pkl;base64,{b64_vectorizer}" download="vectorizer.pkl" style="text-decoration:none;background-color:#2196F3;color:white;padding:8px 16px;border-radius:4px;display:inline-block;">📥 Download vectorizer.pkl</a>'
                st.sidebar.markdown(href_vectorizer, unsafe_allow_html=True)
        
        st.sidebar.markdown("---")
        st.sidebar.info("📌 Upload these files to your GitHub repository to persist the model.")
    
    # ============ 3. VECTORIZER FALLBACK ============
    if vectorizer is None:
        search_corpus = df["Issue key"].fillna("") + " " + df["Summary"].fillna("") + " " + df["Description"].fillna("")
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), sublinear_tf=True)
        vectorizer.fit(search_corpus)
    
    # ============ 4. ML PREDICTIONS ============
    if pipeline is not None:
        try:
            input_df = pd.DataFrame({
                'Combined': df['Combined'],
                'vague_term_density': df.get('vague_term_density', 0)
            })
            df['precalc_ml_prob'] = pipeline.predict_proba(input_df)[:, 1] * 100
        except Exception as e:
            st.sidebar.error(f"❌ Prediction failed: {e}")
            df['precalc_ml_prob'] = 50.0
    else:
        df['precalc_ml_prob'] = 50.0

    # ============ 5. CALCULATE SCORES ============
    rule_scores, ml_scores, hybrid_scores, tiers, explanations = [], [], [], [], []
    failed_rules_list = []
    
    for _, row in df.iterrows():
        r_score, r_reasons = JiraRuleEngine.evaluate_issue_compliance(row)
        
        ml_prob = row['precalc_ml_prob']
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
    
    df['Desc_Length'] = df['Description'].fillna("").astype(str).apply(len)

    # ============ 6. UNIVERSAL FILTERING ============
    st.sidebar.subheader("Universal Filters")
    filters = {}
    exclude_cols = ['Summary', 'Description', 'Acceptance criteria', 'Combined', 'Issue key', 
                    'Quality_Label', 'Explanation', 'Tier', 'Label_Numeric', 'Rule_Score', 'ML_Score', 
                    'Hybrid_Score', 'Failed_Rules', 'precalc_ml_prob', 'Desc_Length']
    
    for col in df.select_dtypes(include=['object', 'string']).columns:
        if col not in exclude_cols:
            filters[col] = st.sidebar.multiselect(col, df[col].unique())
    
    res_df = df.copy()
    for col, vals in filters.items():
        if vals: 
            res_df = res_df[res_df[col].isin(vals)]

    # --- UI Helper Function ---
    def create_count_bar_chart(df_counts, x_col, y_col, title, color_scale):
        fig = px.bar(
            df_counts, x=x_col, y=y_col, title=title,
            labels={y_col: 'Number of Tickets', x_col: x_col},
            color=y_col, color_continuous_scale=color_scale
        )
        fig.update_layout(height=350, showlegend=False, coloraxis_showscale=False)
        fig.update_traces(texttemplate='%{y}', textposition='outside')
        return fig

    # 4. Tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Data Analysis", "RAG Chatbot"])
    
    # ============ TAB 1: DASHBOARD ============
    with tab1:
        # Summary Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Issues", len(res_df))
        c2.metric("GOOD Issues", len(res_df[res_df['Tier']=='GOOD']))
        c3.metric("Review Required", len(res_df[res_df['Tier']=='BAD']))
        c4.metric("Avg Score", f"{res_df['Hybrid_Score'].mean():.1f}%")
        
        st.divider()
        
        # Row 1: Distribution of Quality Scores
        st.subheader("Distribution of Quality Scores")
        fig_hist = px.histogram(
            res_df, x='Hybrid_Score', nbins=20, color='Tier',
            color_discrete_map={'GOOD': '#2ecc71', 'BAD': '#e74c3c'},
            title="Hybrid Score Distribution",
            labels={'Hybrid_Score': 'Hybrid Score (%)', 'count': 'Number of Tickets'},
            barmode='group'
        )
        fig_hist.update_layout(
            xaxis=dict(range=[0, 105], tickmode='linear', tick0=0, dtick=5),
            yaxis=dict(title='Number of Tickets', gridcolor='lightgray'),
            bargap=0.05, height=400, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        fig_hist.add_vline(x=threshold, line_dash="dash", line_color="orange", annotation_text=f"Threshold: {threshold}%")
        fig_hist.add_vline(x=50, line_dash="dot", line_color="red", annotation_text="Attention: 50%")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.divider()
        
        # Row 2: Average Score by Priority & Count by Category
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Average Score by Priority")
            if 'Priority' in res_df.columns:
                avg_by_priority = res_df.groupby('Priority')['Hybrid_Score'].mean().reset_index()
                avg_by_priority = avg_by_priority.sort_values('Hybrid_Score', ascending=True)
                fig_pri = px.bar(
                    avg_by_priority, x='Hybrid_Score', y='Priority', orientation='h',
                    color='Hybrid_Score', color_continuous_scale='RdYlGn', range_color=[0, 100]
                )
                fig_pri.update_layout(height=350, xaxis_range=[0, 105], showlegend=False, coloraxis_showscale=False, xaxis_title='Average Score (%)', yaxis_title='Priority')
                fig_pri.add_vline(x=threshold, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_pri, use_container_width=True)
            else:
                st.info("Priority column not available in dataset")
        
        with col2:
            st.subheader("Count by Category")
            if 'Category' in res_df.columns:
                category_counts = res_df['Category'].value_counts().reset_index(name='Count')
                fig_cat = create_count_bar_chart(category_counts, 'Category', 'Count', "", 'Blues')
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("Category column not available in dataset")
        
        st.divider()

        # Row 3: Count by Status & Issues Needing Attention
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Count by Status")
            if 'Status' in res_df.columns:
                status_counts = res_df['Status'].value_counts().reset_index(name='Count')
                fig_stat = create_count_bar_chart(status_counts, 'Status', 'Count', "", 'Viridis')
                st.plotly_chart(fig_stat, use_container_width=True)
            else:
                st.info("Status column not available in dataset")
        
        with col4:
            st.subheader("Issues Needing Attention (Score < 50%)")
            attention_issues = res_df[res_df['Hybrid_Score'] < 50]
            if not attention_issues.empty:
                display_df = attention_issues.sort_values('Hybrid_Score', ascending=True)
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

        # Row 4: Advanced Analytics
        st.subheader("Advanced Analytics")
        adv1, adv2 = st.columns(2)
        
        with adv1:
            st.markdown("**Hybrid Score vs. Description Length**")
            fig_scatter = px.scatter(
                res_df, x='Desc_Length', y='Hybrid_Score', color='Tier',
                color_discrete_map={'GOOD': '#2ecc71', 'BAD': '#e74c3c'},
                hover_data=['Issue key'],
                labels={'Desc_Length': 'Description Length (Characters)', 'Hybrid_Score': 'Hybrid Score (%)'},
                opacity=0.7
            )
            fig_scatter.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with adv2:
            st.markdown("**Score Distribution by Assignee**")
            if 'Assignee' in res_df.columns and res_df['Assignee'].nunique() > 0:
                top_assignees = res_df['Assignee'].value_counts().nlargest(10).index
                box_df = res_df[res_df['Assignee'].isin(top_assignees)]
                
                fig_box = px.box(
                    box_df, x='Assignee', y='Hybrid_Score', color='Assignee',
                    labels={'Hybrid_Score': 'Hybrid Score (%)', 'Assignee': 'Ticket Assignee'}
                )
                fig_box.update_layout(height=400, showlegend=False, xaxis={'categoryorder':'median descending'})
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.info("Assignee data unavailable or insufficient for visualization.")

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
                    st.warning(f"⚠️ **ML Warning:** ML Score differs from Rule Score by more than 20 points")
            
            with b3:
                st.markdown("**Suggested Improvements**")
                suggestions = []
                if issue_data['Tier'] == 'BAD':
                    if issue_data.get('ML_Score', 100) < 50:
                        suggestions.append("• Improve semantic quality: Add more context, specific details, and clear requirements")
                    if issue_data.get('Rule_Score', 100) < 50:
                        suggestions.append("• Address structural gaps: Ensure all required fields are filled properly")
                    if len(str(issue_data.get('Summary', ''))) < 20:
                        suggestions.append("• Expand Summary: Be more descriptive (currently too short)")
                    
                    failed_rules = issue_data.get('Failed_Rules', [])
                    for rule in failed_rules:
                        if "Missing Acceptance Criteria" in rule: suggestions.append("• Add acceptance criteria to define what 'done' means")
                        if "Missing User Story format" in rule: suggestions.append("• Use User Story format: 'As a... I want... so that...'")
                        if "Missing Priority" in rule: suggestions.append("• Assign a priority level")
                
                if not suggestions: suggestions.append("✅ This ticket meets all quality standards!")
                for suggestion in suggestions: st.info(suggestion)
            
            with st.expander("View Full Ticket Details", expanded=False):
                st.write(f"**Summary:** {issue_data.get('Summary', 'N/A')}")
                st.write(f"**Description:** {issue_data.get('Description', 'N/A')}")
                if 'Acceptance criteria' in issue_data: st.write(f"**Acceptance Criteria:** {issue_data.get('Acceptance criteria', 'N/A')}")
                st.write(f"**Quality Analysis:** {issue_data.get('Explanation', 'N/A')}")

    # ============ TAB 2: DATA ANALYSIS ============
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
        st.dataframe(view_df[['Issue key', 'Rule_Score', 'ML_Score', 'Hybrid_Score', 'Tier', 'Explanation', 'Summary', 'Description']], use_container_width=True)

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
            **Ticket Lookup:** `what is AML-809`
            **Statistics:** `average rule score for high priority tickets`
            **Distributions:** `distribution by status`
            **Counts:** `how many high priority tickets`
            """)
        
        st.divider()
        
        # Display chat messages
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