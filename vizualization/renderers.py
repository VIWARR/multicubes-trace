import json
import re

class Visualizer:
    def __init__(self, project):
        self.project = project

    def _js_safe(self, text):
        return re.sub(r'[^a-zA-Z0-9а-яА-Я_]', '_', str(text))

    def render(self, focus_mc: str):
        target_mcs = {focus_mc}
        edges_to_render = []

        for u, v, d in self.project.graph.edges(data=True):
            if d.get('type') == 'multicube_dependency':
                if u == focus_mc or v == focus_mc:
                    target_mcs.add(u)
                    target_mcs.add(v)
                    is_out = (u == focus_mc)
                    edges_to_render.append({
                        "from": self._js_safe(u), "to": self._js_safe(v),
                        "color": "#e67e22" if is_out else "#95a5a6",
                        "width": 3 if is_out else 1.5
                    })

        nodes_js = []
        for mc in target_mcs:
            is_focus = (mc == focus_mc)
            color = "#e67e22" if is_focus else "#2c3e50"
            
            # Оставляем только название (пункт 2 вашего запроса)
            html = f"""
            <div xmlns="http://www.w3.org/1999/xhtml" style="border:2px solid {color}; border-radius:4px; background:#fff; width:180px; padding:10px; font-family:sans-serif; text-align:center;">
                <div style="color:{color}; font-weight:bold; font-size:13px; word-wrap:break-word;">{mc}</div>
            </div>
            """.replace('\n', '').replace('"', "'")

            nodes_js.append({"id": self._js_safe(mc), "innerHtml": html})

        return f"""
        <html>
        <head><script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script></head>
        <body><div id="net" style="width:100vw; height:100vh;"></div><script>
            function createSvg(html) {{
                return "data:image/svg+xml;charset=utf-8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><foreignObject width="100%" height="100%">' + html + '</foreignObject></svg>');
            }}
            var nodes = new vis.DataSet({json.dumps(nodes_js)}.map(n => ({{ id: n.id, shape: 'image', image: createSvg(n.innerHtml), size: 50 }})));
            var edges = new vis.DataSet({json.dumps(edges_to_render)});
            var options = {{
                layout: {{ hierarchical: {{ enabled: true, direction: 'LR', sortMethod: 'hubsize', levelSeparation: 350 }} }},
                physics: {{ enabled: false }},
                edges: {{ arrows: 'to', smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal' }} }}
            }};
            new vis.Network(document.getElementById('net'), {{nodes: nodes, edges: edges}}, options).once('stabilizationIterationsDone', function() {{ this.fit(); }});
        </script></body></html>
        """