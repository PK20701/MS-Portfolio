import pandas as pd
import numpy as np
import os
from faker import Faker

def main():
    """
    Generates a synthetic customer accounts dataset and saves it as a CSV file.
    This function creates a pandas DataFrame with various customer attributes,
    introduces some correlations related to churn, adds missing values, and
    saves the result to 'data/raw/customer_accounts.csv'.
    """
    # Initialize Faker to generate synthetic data
    fake = Faker()
    Faker.seed(42) # for reproducibility
    np.random.seed(42)

    # --- 1. Define Data Characteristics ---
    num_records = 1000
    churn_rate = 0.26  # Approximate churn rate

    # --- 2. Generate Customer IDs ---
    # Create a list of unique customer IDs
    customer_ids = [fake.unique.uuid4() for _ in range(num_records)]

    # --- 3. Generate Customer Data using List Comprehension ---
    # This is the corrected section. A list of dictionaries is created,
    # where each dictionary represents a customer's record.
    customer_data = [
        {
            'customerID': cid,
            'gender': np.random.choice(['Male', 'Female'], p=[0.51, 0.49]),
            'SeniorCitizen': np.random.choice([0, 1], p=[0.84, 0.16]),
            'Partner': np.random.choice(['Yes', 'No'], p=[0.48, 0.52]),
            'Dependents': np.random.choice(['Yes', 'No'], p=[0.3, 0.7]),
            'tenure': np.random.randint(1, 73),
            'PhoneService': np.random.choice(['Yes', 'No'], p=[0.9, 0.1]),
            'MultipleLines': np.random.choice(['Yes', 'No', 'No phone service'], p=[0.42, 0.48, 0.1]),
            'InternetService': np.random.choice(['DSL', 'Fiber optic', 'No'], p=[0.34, 0.44, 0.22]),
            'OnlineSecurity': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.28, 0.49, 0.23]),
            'OnlineBackup': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.34, 0.43, 0.23]),
            'DeviceProtection': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.34, 0.43, 0.23]),
            'TechSupport': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.29, 0.49, 0.22]),
            'StreamingTV': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.38, 0.39, 0.23]),
            'StreamingMovies': np.random.choice(['Yes', 'No', 'No internet service'], p=[0.39, 0.38, 0.23]),
            'Contract': np.random.choice(['Month-to-month', 'One year', 'Two year'], p=[0.55, 0.21, 0.24]),
            'PaperlessBilling': np.random.choice(['Yes', 'No'], p=[0.59, 0.41]),
            'PaymentMethod': np.random.choice(['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)'], p=[0.34, 0.23, 0.22, 0.21]),
            'MonthlyCharges': round(np.random.uniform(18.25, 118.75), 2),
            'TotalCharges': round(np.random.uniform(18.8, 8684.8), 2),
            'Churn': 'No' # Default value, will be updated next
        }
        for cid in customer_ids
    ]

    # --- 4. Create DataFrame ---
    df = pd.DataFrame(customer_data)

    # --- 5. Introduce Correlations and Set the Churn Target Variable ---
    churn_indices = df.sample(frac=churn_rate, random_state=42).index
    df.loc[churn_indices, 'Churn'] = 'Yes'

    # Adjust tenure for churned customers (tend to be lower)
    df.loc[df['Churn'] == 'Yes', 'tenure'] = df.loc[df['Churn'] == 'Yes', 'tenure'].apply(
        lambda x: max(1, int(x * 0.5))
    )
    # Adjust contract for churned customers
    df.loc[df['Churn'] == 'Yes', 'Contract'] = np.random.choice(
        ['Month-to-month', 'One year'], p=[0.85, 0.15], size=len(churn_indices)
    )

    # Introduce some missing values to simulate real-world data
    num_missing = int(num_records * 0.05) # 5% missing values
    for _ in range(num_missing):
        row_idx = np.random.randint(0, num_records)
        col_name = 'TotalCharges'
        df.loc[row_idx, col_name] = np.nan

    # --- 6. Save to CSV ---
    # Determine the project root directory (assuming this script is in a 'src' folder)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'data', 'raw')
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, 'customer_accounts.csv')
    df.to_csv(output_filename, index=False)

    print(f"Successfully generated '{output_filename}' with {len(df)} records.")
    print("\nFirst 5 rows of the generated data:")
    print(df.head())

if __name__ == "__main__":
    main()