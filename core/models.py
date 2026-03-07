from dataclasses import dataclass, field
from typing import List, Optional, Set

@dataclass(frozen=True, slots=True)
class Cube:
    name: str
    parent_multicube: str
    formula: Optional[str] = None

    @property
    def id(self) -> str:
        return f"{self.parent_multicube}:::{self.name}"
    
@dataclass(slots=True)
class CubeDefinition:
    name: str
    multicube: str
    formula: str

    def to_cube(self) -> Cube:
        return Cube(
            name=self.name,
            parent_multicube=self.multicube,
            formula=self.formula
        )