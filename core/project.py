import networkx as nx
from typing import Dict, Set, List, Optional
from core.models import Cube, Multicube, CubeDefinition
from logic.parser import MulticubesParser
from abc import ABC, abstractmethod
import pandas as pd

class Project:
    def __init__(self):
        self.multicubes: Dict[str, Multicube] = {}
        self.graph = nx.DiGraph()
        self._registry: Dict[str, Set[str]] = {}
        self._parser = MulticubesParser

    def build_from_definitions(self, definitions: List[Cube]):
        self._validate_definitions(definitions=definitions)
        self._create_multicubes(definitions=definitions)
        self._build_dependency_graph()

    def _validate_definitions(self, definitions: List[CubeDefinition]):
        if not definitions:
            raise ValueError("No cube definitions provided")
        
        seen = set()
        for definition in definitions:
            cube_id = Cube(definition.name, definition.multicube).id
            if cube_id in seen:
                raise ValueError(f"Duplicate cube definition: {cube_id}")
            seen.add(cube_id)
    
    def _create_multicubes(self, definitions: List[CubeDefinition]):
        mc_names = {d.multicube for d in definitions}
        for mc_name in mc_names:
            self.multicubes[mc_name] = Multicube(name=mc_name)
            self._registry[mc_name] = set()

        for c_def in definitions:
            cube = c_def.to_cube()
            self.multicubes[cube.parent_multicube].add_cube(cube)
            self._registry[cube.parent_multicube].add(cube.name)
            self.graph.add_node(
                cube.id,
                label=cube.name,
                multicube=cube.parent_multicube,
                formula=cube.formula,
                type='cube'
            )

        for mc_name in self.multicubes:
            self.graph.add_node(
                mc_name,
                label=mc_name,
                type='multicube'
            )

    def _build_dependency_graph(self):
        for mc_name, multicube in self.multicubes.items():
            for cube in multicube.cubes:
                if cube.formula:
                    deps = MulticubesParser.parse_dependencies(
                        formula=cube.formula,
                        current_mc=mc_name,
                        registry=self._registry
                    )
                    for src_mc, src_cube_name in deps:
                        src_cube_id = Cube(src_cube_name, src_mc).id
                        if self.graph.has_node(src_cube_id):
                            self.graph.add_edge(
                                src_cube_id, 
                                cube.id,
                                type='dependency'
                            )
                            if self.graph.has_node(src_mc) and self.graph.has_node(mc_name):
                                self.graph.add_edge(
                                    src_mc,
                                    mc_name,
                                    type='multicube_dependency'
                                )

    def get_cube(self, multicube: str, cube_name: str) -> Optional[Cube]:
        if multicube in self.multicubes:
            for cube in self.multicubes[multicube].cubes:
                if cube.name == cube_name:
                    return cube
        return None
    
    def get_all_cubes(self) -> List[Cube]:
        cubes = []
        for multicube in self.multicubes.values():
            cubes.extend(multicube.cubes)
        return cubes
    
    def get_dependencies(self, cube: Cube) -> List[Cube]:
        deps = []
        for src_id, _ in self.graph.in_edges(cube.id):
            if ':::' in src_id:
                src_mc, src_cube = src_id.split(':::')
                src_cube_obj = self.get_cube(src_mc, src_cube)
                if src_cube_obj:
                    deps.append(src_cube_obj)
        return deps
    
    def get_dependents(self, cube: Cube) -> List[Cube]:
        deps = []
        for _, target_id in self.graph.out_edges(cube.id):
            if ':::' in target_id:
                target_mc, target_cube = target_id.split(':::')
                target_cube_obj = self.get_cube(target_mc, target_cube)
                if target_cube_obj:
                    deps.append(target_cube_obj)
        return deps
    
    def get_calculation_order(self) -> List[Cube]:
        try:
            cube_nodes = [n for n in self.graph.nodes if ':::' in n]
            subgraph = self.graph.subgraph(cube_nodes)
            order = list(nx.topological_sort(subgraph))
            result = []
            for node_id in order:
                mc, cube_name = node_id.split(':::')
                cube = self.get_cube(mc, cube_name)
                if cube:
                    result.append(cube)
            return result
        except nx.NetworkXUnfeasible:
            raise ValueError("Cyclic dependencies detected!")
        
    def validate(self) -> List[str]:
        errors = []
        
        for mc_name, multicube in self.multicubes.items():
            for cube in multicube.cubes:
                if cube.formula:
                    deps = MulticubesParser.parse_dependencies(
                        formula=cube.formula,
                        current_mc=mc_name,
                        registry=self._registry
                    )
                    
                    for src_mc, src_cube in deps:
                        if not self.get_cube(src_mc, src_cube):
                            errors.append(
                                f"Invalid reference in {cube.id}: "
                                f"'{src_mc}.{src_cube}' does not exist"
                            )
        
        try:
            self.get_calculation_order()
        except ValueError as e:
            errors.append(str(e))
        
        return errors
