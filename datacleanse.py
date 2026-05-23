import pandas as pd
import numpy as np
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
        pass
        def formatter(val, row_name):
            if row_name == 'count':
                try: return f"{int(float(val))}"
                except: return val
            try:
                # Stats view follows the 4-digit precision logic
                return f"{float(val):.4g}" if not isinstance(val, str) else val
            except: return val

        pass # Prints the formatted version via lamda function
        
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