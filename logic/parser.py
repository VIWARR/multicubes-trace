import re
from typing import Set, Tuple, Dict

class MulticubesParser:
    """
    Парсер для извлечения зависимостей из синтаксиса формул Optimacros
    """

    # Паттерн для внешних ссылок: 'Multicube'.'Cube'
    EXT_REF_RE = re.compile(r"'([^']+)'\.'([^']+)'")
    # Паттерн для лбых строк в кавычках
    ANY_QUOTED_RE = re.compile(r"'([^']+)'")

    @classmethod
    def parse_dependencies(
        cls,
        formula: str,
        current_mc: str,
        registry: Dict[str, Set[str]]
    ) -> Set[Tuple[str, str]]:
        """
        registry: словарь {название_мультикуба: {сет_имен_кубов}}
        Возвращает: Set[(multicube_name, cube_name)]
        """
        dependencies = set()
        if not formula or not isinstance(formula, str):
            return set()

        # 1. Извлекаем явные внешние ссылки
        external_refs = cls.EXT_REF_RE.findall(formula)
        for mc, cube in external_refs:
            dependencies.add((mc, cube))

        # 2. Извлекаем внутренние ссылки и системные элементы
        # (Ищем все 'Value', которые не являются частью внешних ссылок)
        all_quoted = cls.ANY_QUOTED_RE.findall(formula)
        external_full_refs = {f"{mc}.{cube}" for mc, cube in external_refs}

        local_cubes = registry.get(current_mc, set())

        for item in all_quoted:
            is_external = False
            for mc, cube in external_refs:
                if cube == item:
                    is_external = True
                    break
            if item in local_cubes and not is_external:
                dependencies.add((current_mc, item))

        return dependencies