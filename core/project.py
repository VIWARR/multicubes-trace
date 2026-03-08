import networkx as nx
from typing import Dict, Set, List, Optional
from core.models import Cube, CubeDefinition
from logic.parser import MulticubesParser

class Project:
    def __init__(self):
        self.cubes: Dict[str, Cube] = {}
        self.graph = nx.DiGraph()
        self._registry: Dict[str, Set[str]] = {}

    def build_from_definitions(self, definitions: List[CubeDefinition]):
        self.cubes.clear()
        self.graph.clear()
        self._registry.clear()

        for d in definitions:
            cube = d.to_cube()
            c_id = cube.id
            if c_id in self.cubes:
                raise ValueError(f"Duplicate cube definition: {c_id}")

            self.cubes[c_id] = cube
            self._registry.setdefault(cube.parent_multicube, set()).add(cube.name)
            
            self.graph.add_node(
                c_id, 
                type='cube', 
                multicube=cube.parent_multicube,
                formula=cube.formula
            )
            
            if cube.parent_multicube not in self.graph:
                self.graph.add_node(cube.parent_multicube, type='multicube')

        edges_to_add = []
        mc_edges_to_add = set()
        
        for c_id, cube in self.cubes.items():
            if not cube.formula:
                continue

            deps = MulticubesParser.parse_dependencies(cube.formula, cube.parent_multicube, self._registry)

            for src_mc, src_cube_name in deps:
                src_id = f"{src_mc}:::{src_cube_name}"
                
                if src_id in self.cubes:
                    edges_to_add.append((src_id, c_id))
                    if src_mc != cube.parent_multicube:
                        mc_edges_to_add.add((src_mc, cube.parent_multicube))
                else:
                    print(f"⚠️ Куб '{c_id}' ссылается на '{src_id}', но он не найден в базе!")

        self.graph.add_edges_from(edges_to_add, type='dependency')
        self.graph.add_edges_from(mc_edges_to_add, type='multicube_dependency')

    def get_cube(self, mc_name: str, cube_name: str) -> Optional[Cube]:
        return self.cubes.get(f"{mc_name}:::{cube_name}")
    
    def get_calculation_order(self) -> List[Cube]:
        cube_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'cube']
        subgraph = self.graph.subgraph(cube_nodes)
        try:
            return [self.cubes[n] for n in nx.topological_sort(subgraph)]
        except nx.NetworkXUnfeasible:
            raise ValueError("Cyclic dependencies detected!")