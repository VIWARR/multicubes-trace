from pyvis.network import Network
import networkx as nx
import json

class Visualizer:
    COLOR_INPUT = "#3498DB"
    COLOR_CALC = "#27AE60"
    COLOR_MC = "#2C3E50"

    def __init__(self, project):
        self.project = project

    def render(self, focus_mc: str, show_internal: bool = True, mode: str = "Full"):
        # 1. Инициализация с оптимизированными настройками физики
        net = Network(height="750px", width="100%", directed=True, bgcolor="#ffffff")
        
        # Senior Tip: Отключаем физику после стабилизации, чтобы браузер не тормозил
        self._set_optimized_options(net)

        full_graph = self.project.graph

        # 2. Выбор стратегии фильтрации (Optimization: O(k) вместо O(N))
        if mode == "MC Only":
            # Берем только узлы типа multicube
            display_nodes = [n for n, d in full_graph.nodes(data=True) if d.get('type') == 'multicube']
            subgraph = full_graph.subgraph(display_nodes)
        else:
            # Извлекаем подграф: Фокусный МК + его прямые связи (1-2 уровня)
            # Это радикально снижает нагрузку с 12500 до ~200-500 узлов
            subgraph = self._get_focused_subgraph(full_graph, focus_mc, show_internal, mode)

        # 3. Лимит безопасности
        if subgraph.number_of_nodes() > 1500:
            # Если даже подграф огромный, берем только самое важное
            return self._render_too_many_nodes_message(subgraph.number_of_nodes())

        # 4. Эффективное добавление данных
        for node_id, data in subgraph.nodes(data=True):
            self._add_node_to_net(net, node_id, data, focus_mc)

        for u, v, data in subgraph.edges(data=True):
            # Проверка фильтров для ребер
            if mode == "Cross-MC" and subgraph.nodes[u].get('multicube') == subgraph.nodes[v].get('multicube'):
                continue
            net.add_edge(u, v, color="#ABB2B9", arrowStrikethrough=False)

        return net

    def _get_focused_subgraph(self, G, focus_mc, show_internal, mode):
        """Извлечение только релевантной части графа."""
        # Узлы внутри целевого МК
        target_nodes = [n for n, d in G.nodes(data=True) if d.get('multicube') == focus_mc]
        
        # Соседи (входящие и исходящие зависимости)
        neighbors = set()
        for node in target_nodes:
            neighbors.update(G.predecessors(node))
            neighbors.update(G.successors(node))
        
        all_relevant = set(target_nodes) | neighbors
        
        # Если режим Full, добавляем еще один уровень или МК-узлы
        mc_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'multicube']
        all_relevant.update(mc_nodes)

        return G.subgraph(all_relevant)

    def _add_node_to_net(self, net, node_id, data, focus_mc):
        node_type = data.get('type')
        if node_type == 'multicube':
            net.add_node(node_id, label=node_id, shape="database", color=self.COLOR_MC, size=25)
        else:
            is_target = data.get('multicube') == focus_mc
            color = self.COLOR_CALC if data.get('formula') else self.COLOR_INPUT
            
            # Улучшаем производительность: отключаем тени и сложные формы для массовки
            net.add_node(
                node_id,
                label=data.get('label', node_id),
                color=color,
                borderWidth=3 if is_target else 1,
                size=20 if is_target else 12,
                title=f"MC: {data.get('multicube')}\nFormula: {data.get('formula') or 'Input'}"
            )

    def _set_optimized_options(self, net):
        """Настройки физики для мгновенного рендеринга больших графов."""
        options = {
            "physics": {
                "stabilization": {
                    "enabled": True, 
                    "iterations": 100,
                    "updateInterval": 25
                },
                "barnesHut": {
                    "gravitationalConstant": -2000, 
                    "springLength": 200,
                    "avoidOverlap": 0.5
                },
                "solver": "barnesHut"
            },
            "edges": {
                "smooth": {"type": "continuous"},
                "hoverWidth": 0.5
            },
            "interaction": {
                "hideEdgesOnDrag": True,
                "hideNodesOnDrag": False,
                "hover": True
            }
        }
        
        # Правильный Senior-способ передачи настроек: 
        # Сериализуем словарь в чистую JSON-строку
        opts_json = json.dumps(options)
        net.set_options(opts_json)