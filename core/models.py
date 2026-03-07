from dataclasses import dataclass, field
from typing import List, Optional, Set

@dataclass(frozen=True)
class Cube:
    name: str
    parent_multicube: str
    formula: Optional[str] = None

    @property
    def id(self) -> str:
        return f"{self.parent_multicube}:::{self.name}"
    
@dataclass
class Multicube:
    name: str
    cubes: List[Cube] = field(default_factory=list)

    def add_cube(self, cube: Cube):
        self.cubes.append(cube)

    def get_cube_names(self) -> Set[str]:
        return {cube.name for cube in self.cubes}
    
@dataclass(frozen=True)
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