import re
from typing import Set, Tuple, Dict

class MulticubesParser:
    EXT_REF_RE = re.compile(r"'([^']+)'\.'([^']+)'")
    ANY_QUOTED_RE = re.compile(r"'([^']+)'")

    @classmethod
    def parse_dependencies(
        cls,
        formula: str,
        current_mc: str,
        registry: Dict[str, Set[str]]
    ) -> Set[Tuple[str, str]]:
        if not formula or not isinstance(formula, str):
            return set()
        
        dependencies = set()

        # 1. Извлекаем внешние ссылки строго по паттерну 'MC'.'Cube'
        external_refs = cls.EXT_REF_RE.findall(formula)
        external_cubes_found = set()

        for mc, cube in external_refs:
            dependencies.add((mc, cube))
            external_cubes_found.add(cube)

        # 2. Извлекаем внутренние ссылки и системные элементы
        all_quoted = set(cls.ANY_QUOTED_RE.findall(formula))
        local_cubes = registry.get(current_mc, set())
        internal_refs = (all_quoted & local_cubes) - external_cubes_found

        for item in internal_refs:
            dependencies.add((current_mc, item))

        return dependencies