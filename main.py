import streamlit as st
import pandas as pd
import re
import networkx as nx
from core.project import Project
from visualization.renderers import Visualizer
from infrastructure.adapters.dataframe_adapter import DataFrameAdapter

st.set_page_config(layout="wide", page_title="CPM Audit Tool", page_icon="🔍")

@st.cache_resource
def process_uploaded_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    adapter = DataFrameAdapter(df)
    definitions = adapter.load_definitions()
    project = Project()
    project.build_from_definitions(definitions)
    return project

st.title("🔍 CPM Model Auditor & Optimizer")

uploaded_file = st.sidebar.file_uploader("Загрузите выгрузку модели (xlsx)", type="xlsx")

if uploaded_file:
    try:
        project = process_uploaded_file(uploaded_file)
        visualizer = Visualizer(project)
        all_mcs = project._registry.keys()

        # --- ГЛОБАЛЬНЫЙ АУДИТ ---
        st.header("📊 Глобальный аудит модели")
        g_tab_hardcode, g_tab_chains, g_tab_star = st.tabs([
            "🛠 Хардкод и Справочники", 
            "🔗 Цепочки пересчета", 
            "⭐️ Нарушение топологии (Star)"
        ])

        with g_tab_hardcode:
            st.subheader("Глубокий синтаксический анализ формул")
            hardcode_data, dict_refs = [], []
            
            # Числа (исключаем те, что в именах или кавычках)
            num_pattern = r"(?<![\w\.'])\b(?![01]\b)\d+(?:\.\d+)?\b(?![\w\.'])"
            # Текст в двойных кавычках
            text_pattern = r'\"([^\"]+)\"'
            # Ссылки формата 'Объект1'.'Объект2'
            ref_pair_pattern = r'\'([^\']+)\'\.\'([^\']+)\''

            for c_id, cube in project.cubes.items():
                f = str(cube.formula)
                if not f or f in ['nan', '']: continue
                
                # --- ПОИСК КОНСТАНТ ---
                found_nums = re.findall(num_pattern, f)
                raw_text = re.findall(text_pattern, f)
                found_text = [t for t in raw_text if t not in all_mcs]
                
                if found_nums or found_text:
                    hardcode_data.append({
                        "Мультикуб": cube.parent_multicube,
                        "Куб": cube.name,
                        "Найдено": f"Числа: {found_nums}, Текст: {found_text}",
                        "Формула": f
                    })
                
                # --- ПОИСК ССЫЛОК НА ЭЛЕМЕНТЫ ---
                matches = re.findall(ref_pair_pattern, f)
                for src, target in matches:
                    t_clean = target.strip()
                    # Исключения: свойства (p.) и ссылки на справочники (L)
                    is_prop = t_clean.lower().startswith('p.')
                    is_dimension = t_clean.upper().startswith('L')
                    
                    # Проверка на существование объекта в реестре
                    is_known_obj = (src in project._registry and t_clean in project._registry[src]) or (t_clean in all_mcs)
                    
                    # Если это ссылка на справочник, но не свойство, не другое измерение и не куб — это элемент
                    if src.startswith('L') and not is_prop and not is_dimension and not is_known_obj:
                        dict_refs.append({
                            "Мультикуб": cube.parent_multicube,
                            "Куб": cube.name,
                            "Справочник": src,
                            "Элемент": t_clean,
                            "Формула": f
                        })

            col_cfg = {"Формула": st.column_config.TextColumn("Формула", width="large")}
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown(f"#### 🔢 Константы: {len(hardcode_data)}")
                if hardcode_data:
                    st.dataframe(pd.DataFrame(hardcode_data).head(100), use_container_width=True, column_config=col_cfg)
            with col_h2:
                st.markdown(f"#### 📚 Элементы справочников: {len(dict_refs)}")
                if dict_refs:
                    st.dataframe(pd.DataFrame(dict_refs).head(100), use_container_width=True, column_config=col_cfg)

        with g_tab_chains:
            st.subheader("Анализ глубины расчетов")
            try:
                longest_path = nx.dag_longest_path(project.graph)
                st.warning(f"Критический путь: {len(longest_path)} шагов")
                chain_df = [{"№": i+1, "Мультикуб": n.split(":::")[0], "Куб": n.split(":::")[1]} 
                            for i, n in enumerate(longest_path)]
                st.table(pd.DataFrame(chain_df))
            except Exception:
                st.info("Цепочки не обнаружены.")

        with g_tab_star:
            st.subheader("Нарушение архитектуры Hub & Spoke")
            mc_graph = nx.DiGraph()
            for u, v in project.graph.edges():
                mu, mv = u.split(":::")[0], v.split(":::")[0]
                if mu != mv: mc_graph.add_edge(mu, mv)
            
            star_violations = []
            for mc in all_mcs:
                ind = mc_graph.in_degree(mc) if mc in mc_graph else 0
                outd = mc_graph.out_degree(mc) if mc in mc_graph else 0
                if ind > 2 and outd > 2:
                    star_violations.append({"Мультикуб": mc, "Вход (МК)": ind, "Выход (МК)": outd})
            
            if star_violations:
                st.dataframe(pd.DataFrame(star_violations), use_container_width=True)
            else:
                st.success("Архитектура соответствует стандарту.")

        # --- ДЕТАЛЬНЫЙ АНАЛИЗ МК ---
        st.divider()
        st.header("🎯 Детальный анализ выбранного блока")
        selected_mc = st.sidebar.selectbox("Выберите мультикуб:", sorted(list(all_mcs)))

        if selected_mc:
            if 'exp_all_cons' not in st.session_state: st.session_state.exp_all_cons = False
            if 'exp_all_src' not in st.session_state: st.session_state.exp_all_src = False

            t_map, t_deps, t_struct = st.tabs(["🗺 Карта", "🔗 Dependencies", "📦 Кубы"])

            with t_map:
                st.components.v1.html(visualizer.render(selected_mc), height=600)

            with t_deps:
                c1, c2 = st.columns(2)
                with c1:
                    l_c = "Свернуть всё" if st.session_state.exp_all_cons else "Развернуть всё"
                    if st.button(l_c, key="bc"):
                        st.session_state.exp_all_cons = not st.session_state.exp_all_cons
                        st.rerun()

                    ext_cons = {}
                    pat = f"'{selected_mc}'."
                    for cid, cube in project.cubes.items():
                        if cube.parent_multicube != selected_mc and pat in str(cube.formula):
                            mc = cube.parent_multicube
                            if mc not in ext_cons: ext_cons[mc] = []
                            m = re.search(f"'{re.escape(selected_mc)}'\.'([^']+)'", str(cube.formula))
                            ext_cons[mc].append({"t": cube.name, "s": m.group(1) if m else "N/A", "f": cube.formula})
                    
                    for mc, items in sorted(ext_cons.items()):
                        with st.expander(f"👥 ПОТРЕБИТЕЛЬ: {mc}", expanded=st.session_state.exp_all_cons):
                            for it in items:
                                st.markdown(f"**{it['t']}** ← *{it['s']}*")
                                st.code(it['f'], language="sql")

                with c2:
                    l_s = "Свернуть всё" if st.session_state.exp_all_src else "Развернуть всё"
                    if st.button(l_s, key="bs"):
                        st.session_state.exp_all_src = not st.session_state.exp_all_src
                        st.rerun()

                    local = [c for c in project.cubes.values() if c.parent_multicube == selected_mc]
                    ext_src = {}
                    for c in local:
                        ms = re.findall(r"'([^']+)'\.'([^']+)'", str(c.formula))
                        for smc, sc in ms:
                            if smc != selected_mc:
                                if smc not in ext_src: ext_src[smc] = []
                                ext_src[smc].append({"t": c.name, "s": sc, "f": c.formula})
                    
                    for mc, items in sorted(ext_src.items()):
                        with st.expander(f"📦 ИСТОЧНИК: {mc}", expanded=st.session_state.exp_all_src):
                            for it in items:
                                st.markdown(f"**{it['t']}** → *{it['s']}*")
                                st.code(it['f'], language="sql")

            with t_struct:
                mc_c = [c for c in project.cubes.values() if c.parent_multicube == selected_mc]
                st.dataframe(pd.DataFrame([{"Куб": c.name, "Формула": c.formula} for c in mc_c]), 
                             use_container_width=True, column_config=col_cfg)

    except Exception as e:
        st.error(f"Ошибка аудита: {e}")
else:
    st.info("Загрузите XLSX файл для начала аудита.")