import pandas as pd
from typing import List
from core.models import CubeDefinition
from infrastructure.adapters.base import DataSourceAdapter

class DataFrameAdapter(DataSourceAdapter):
    REQUIRED_COLUMNS = {'multicubes', 'cubes', 'formula'}

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def validate_source(self) -> bool:
        return self.REQUIRED_COLUMNS.issubset(self.df.columns)
    
    def load_definitions(self) -> List[CubeDefinition]:
        if not self.validate_source():
            raise ValueError(f"DataFrame missing required columns: {self.REQUIRED_COLUMNS}")
        
        definitions = []
        for _, row in self.df.iterrows():
            definitions.append(CubeDefinition(
                name=row['cubes'],
                multicube=row['multicubes'],
                formula=row['formula']
            ))
        return definitions