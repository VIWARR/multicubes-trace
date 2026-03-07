import pandas as pd
from typing import List
from core.models import CubeDefinition
from infrastructure.adapters.base import DataSourceAdapter

class DataFrameAdapter(DataSourceAdapter):
    REQUIRED_COLUMNS = {'multicubes', 'cubes', 'formula'}

    def __init__(self, df: pd.DataFrame):
        self.df = df
    
    def load_definitions(self) -> List[CubeDefinition]:
        if not self.REQUIRED_COLUMNS.issubset(self.df.columns):
            raise ValueError(f"DataFrame missing required columns: {self.REQUIRED_COLUMNS}")
        
        return [
            CubeDefinition(
                name=r['cubes'], multicube=r['multicubes'], formula=r['formula']
                for r in self.df.to_dict('records')
            )
        ]