import pandas as pd
import streamlit as st

class FeatureEngineer:
    VAGUE_TERMS = ['tbd', 'fix this', 'to be determined', 'fix later', 'placeholder', 'whatever', 'needful', 'update you later']

    @staticmethod
    def engineer_features(df):
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]
        
        # Combine text fields
        df['Combined'] = (df['Summary'].fillna("").astype(str) + " " + 
                          df['Description'].fillna("").astype(str) + " " + 
                          df['Acceptance criteria'].fillna("").astype(str))
        
        word_count = df['Description'].apply(lambda x: len(str(x).split()))
        
        def count_vague(text):
            return sum(term in str(text).lower() for term in FeatureEngineer.VAGUE_TERMS)

        df['vague_term_count'] = df['Combined'].apply(count_vague)
        df['vague_term_density'] = df['vague_term_count'] / word_count.replace(0, 1)
        
        # DYNAMIC LOGIC: If Quality_Label is present, prepare for training
        if 'Quality_Label' in df.columns:
            df['Label_Numeric'] = df['Quality_Label'].map({'GOOD': 1, 'BAD': 0})
        else:
            df['Label_Numeric'] = None
            
        return df