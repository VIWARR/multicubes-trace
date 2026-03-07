from abc import ABC, abstractmethod
from typing import List
from core.models import CubeDefinition

class DataSourceAdapter(ABC):
    @abstractmethod
    def load_definitions(self) -> List[CubeDefinition]:
        pass