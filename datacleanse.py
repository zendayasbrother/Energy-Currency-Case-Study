import pandas as pd
import numpy as np
import wbgapi as wb
import json
from sklearn.linear_model import LinearRegression

class DataCleaner:
    def __init__(self, data_source):
        if isinstance(data_source, pd.DataFrame):
            self.df = data_source
            print("DataFrame ingested from API successfully.")
        else:
            self.df = pd.read_csv(data_source)
            print(f"File loaded successfully from {data_source}")

        self.standardize_columns()

    def standardize_columns(self):
        self.df.columns = (
            self.df.columns.str.strip()
            .str.replace(' ', '_')
            .str.replace('–', '_')
            .str.replace('-', '_')
            .str.lower()
        )

    def clean_data(self):
        target = 'electricity_access'
        feature = 'gdp' 

        if 'year' in self.df.columns:
            self.df['year'] = self.df['year'].astype(str).str.extract('(\d+)').astype(int)
    
        if feature in self.df.columns:
            self.df[feature] = self.df[feature] / 1_000_000_000

        print(f"\n--- HYBRID OLS IMPUTATION: {target.upper()} ---")
        data_full = self.df.dropna(subset=[target, feature])
        data_missing = self.df[self.df[target].isnull() & self.df[feature].notnull()]

        if not data_missing.empty and not data_full.empty:
            model = LinearRegression()
            model.fit(data_full[[feature]], data_full[target])
            predictions = model.predict(data_missing[[feature]])
            self.df.loc[self.df[target].isnull() & self.df[feature].notnull(), target] = predictions
            print(f"Successfully imputed {len(predictions)} values via OLS.")

        # Temporal Interpolation
        self.df = self.df.dropna(subset=['year']) 
        self.df['year'] = pd.to_datetime(self.df['year'].astype(int), format='%Y')
        self.df = self.df.set_index('year')
        self.df = self.df.infer_objects(copy=False) 
        self.df = self.df.interpolate(method='time')
        self.df = self.df.reset_index()
        self.df['year'] = self.df['year'].dt.year.astype(int)

        # Stage 5 Statistics logic
        final_stats_df = self.df.copy()
        final_stats_df['year'] = final_stats_df['year'].astype(str)
        final_stats_df['economy'] = final_stats_df['economy'].astype(str)
        summary = final_stats_df.describe(include='all').fillna(0)

        def formatter(val, row_name):
            if row_name == 'count':
                try: return f"{int(float(val))}"
                except: return val
            try:
                # Stats view follows the 4-digit precision logic
                return f"{float(val):.4g}" if not isinstance(val, str) else val
            except: return val

        formatted_summary = summary.apply(lambda col: [formatter(v, summary.index[i]) for i, v in enumerate(col)])
        formatted_summary.index = summary.index
        print(formatted_summary)
        
        return self.df
    
    def gen_json(self):
        data_dict = {
            "metadata": {"source": "Trilateral_API_Merge", "rows": len(self.df)},
            "cleaned_data": self.df.to_dict(orient='records')
        }
        self.json_output = json.dumps(data_dict, default=str, indent=4)
        with open('cleaned_data.json', 'w') as f:
            f.write(self.json_output)
        return self.json_output