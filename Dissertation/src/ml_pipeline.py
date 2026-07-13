import pandas as pd
import joblib
import os
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler
from imblearn.pipeline import Pipeline
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

class RequirementMLPipeline:
    def __init__(self, use_vague_feature=True):
        self.num_cols = ['vague_term_density']
        self.use_vague_feature = use_vague_feature
        
        # 1. Dampen TF-IDF impact to prevent overfitting
        text_transformer = TfidfVectorizer(max_features=1000, ngram_range=(1,2), sublinear_tf=True)
        transformers = [('text', text_transformer, 'Combined')]
        if self.use_vague_feature:
            transformers.append(('num', MinMaxScaler(), self.num_cols))
            
        self.preprocessor = ColumnTransformer(transformers)
        
        # 2. Balanced weights to address imbalance
        self.models = {
            "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42, class_weight='balanced'),
            "Logistic Regression": LogisticRegression(random_state=42, class_weight='balanced'),
            "SVM (Linear)": SVC(probability=True, kernel='linear', C=1.0, random_state=42, class_weight='balanced')
        }
        self.smote = SMOTE(random_state=42)
        os.makedirs("models", exist_ok=True)

    def execute_validation_matrix(self, df):
        train = df[df['Data_Split'] == 'Train']
        test = df[df['Data_Split'] == 'Test']
        features = ['Combined'] + (self.num_cols if self.use_vague_feature else [])
        
        results = []
        best_f1 = 0
        best_model_obj = None
        best_model_name = ""

        for name, model in self.models.items():
            pipe = Pipeline([
                ('prep', self.preprocessor), 
                ('smote', self.smote), 
                ('clf', model)
            ])
            
            pipe.fit(train[features], train['Label_Numeric'])
            preds = pipe.predict(test[features])
            
            # 3. DEBUG: Catch False Negatives explicitly
            test_res = test.copy()
            test_res['pred'] = preds
            fns = test_res[(test_res['Label_Numeric'] == 1) & (test_res['pred'] == 0)]
            if not fns.empty:
                print(f"[!] {name} - False Negatives found: {fns['Issue key'].tolist()}")
            
            f1 = f1_score(test['Label_Numeric'], preds)
            tn, fp, fn, tp = confusion_matrix(test['Label_Numeric'], preds).ravel()            

            results.append({
                "Model": name,
                "Accuracy": accuracy_score(test['Label_Numeric'], preds),
                "Precision": precision_score(test['Label_Numeric'], preds),
                "Recall": recall_score(test['Label_Numeric'], preds),
                "F1_Score": f1,
                "Confusion_Matrix": f"TN={tn}, FP={fp}, FN={fn}, TP={tp}"
            })
            
            if f1 > best_f1:
                best_f1 = f1
                best_model_obj = pipe
                best_model_name = name
                joblib.dump(pipe, "models/best_model.pkl")
            
        return pd.DataFrame(results), best_model_obj, best_model_name, best_f1