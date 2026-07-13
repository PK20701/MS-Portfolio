import pandas as pd

class DataPreprocessor:
    @staticmethod
    def clean_data(df):
        print("[*] Preprocessing: Cleaning text and handling nulls...")
        df = df.copy()
        text_cols = ['Summary', 'Description', 'Acceptance criteria']
        for col in text_cols:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df