import streamlit as st
import pandas as pd
from core.project import Project
from vizualization.renderers import Visualizer
from infrastructure.adapters.dataframe_adapter import DataFrameAdapter
import re

st.set_page_config(layout="wide", page_title="CPM Audit Tool")

@st.cache_resource
def process_uploaded_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    adapter = DataFrameAdapter(df)
    definitions = adapter.load_definitions()
    project = Project()
    project.build_from_definitions(definitions)
    return project

st.title("🔍 Аудит модели")

# 1. Окно загрузки файла
uploaded_file = st.sidebar.file_uploader("Загрузите выгрузку модели (xlsx)", type="xlsx")

if uploaded_file:
    project = process_uploaded_file(uploaded_file)
    visualizer = Visualizer(project)

    all_mcs = sorted(list(project._registry.keys()))
    selected_mc = st.sidebar.selectbox("Выберите мультикуб:", all_mcs)

    if selected_mc:
        tab_map, tab_deps, tab_structure = st.tabs([
            "🗺 Карта связей", 
            "🔗 Просмотр зависимостей", 
            "📦 Кубы"
        ])

        with tab_map:
            st.components.v1.html(visualizer.render(selected_mc), height=600)

        with tab_deps:
            st.subheader(f"Анализ связей: {selected_mc}")
            
            # Инициализация состояний, если их нет
            if 'exp_all_cons' not in st.session_state: st.session_state.exp_all_cons = False
            if 'exp_all_src' not in st.session_state: st.session_state.exp_all_src = False

            col1, col2 = st.columns(2)
            
            # --- ЛЕВАЯ КОЛОНКА: Referenced By (Потребители) ---
            with col1:
                c1_head, c1_btn = st.columns([2, 1])
                c1_head.markdown("### 📥 Потребитель")
                
                # Динамический текст кнопки для Потребителей
                label_cons = "Развернуть/Свернуть"
                if c1_btn.button(label_cons, key="all_c"):
                    st.session_state.exp_all_cons = not st.session_state.exp_all_cons
                    st.rerun()

                # Сбор данных
                external_consumers = {}
                search_pattern = f"'{selected_mc}'."
                for c_id, cube in project.cubes.items():
                    if cube.parent_multicube != selected_mc and search_pattern in str(cube.formula):
                        cons_mc = cube.parent_multicube
                        if cons_mc not in external_consumers: external_consumers[cons_mc] = []
                        ref_match = re.search(f"'{re.escape(selected_mc)}'\.'([^']+)'", str(cube.formula))
                        ref_cube = ref_match.group(1) if ref_match else "не определен"
                        external_consumers[cons_mc].append({
                            "target_cube": cube.name, "source_cube": ref_cube, "formula": cube.formula
                        })
                
                if external_consumers:
                    for cons_mc in sorted(external_consumers.keys()):
                        # УРОВЕНЬ 1: Блок Мультикуба (скрывает кубы внутри)
                        with st.expander(f"👥 {cons_mc}", expanded=st.session_state.exp_all_cons):
                            for item in external_consumers[cons_mc]:
                                st.markdown(f"**{item['target_cube']}**")
                                st.caption(f"Источник: {item['source_cube']}")
                                st.code(item['formula'], language="sql")
                                st.markdown("---")
                else:
                    st.caption("Данные не используются в других модулях.")

            # --- ПРАВАЯ КОЛОНКА: Used In (Источники) ---
            with col2:
                c2_head, c2_btn = st.columns([2, 1])
                c2_head.markdown("### 📤 Источник")
                
                # Динамический текст кнопки для Источников
                label_src = "Развернуть/Свернуть"
                if c2_btn.button(label_src, key="all_s"):
                    st.session_state.exp_all_src = not st.session_state.exp_all_src
                    st.rerun()

                local_cubes = [c for c in project.cubes.values() if c.parent_multicube == selected_mc]
                external_sources = {}
                for c in local_cubes:
                    if c.formula:
                        matches = re.findall(r"'([^']+)'\.'([^']+)'", str(c.formula))
                        for src_mc, src_cube in matches:
                            if src_mc != selected_mc:
                                if src_mc not in external_sources: external_sources[src_mc] = []
                                external_sources[src_mc].append({
                                    "target_cube": c.name, "source_cube": src_cube, "formula": c.formula
                                })
                
                if external_sources:
                    for src_mc in sorted(external_sources.keys()):
                        # УРОВЕНЬ 1: Блок Мультикуба (скрывает кубы внутри)
                        with st.expander(f"📦 {src_mc}", expanded=st.session_state.exp_all_src):
                            for item in external_sources[src_mc]:
                                st.markdown(f"**{item['target_cube']}**")
                                st.caption(f"Ссылка на куб источника: {item['source_cube']}")
                                st.code(item['formula'], language="sql")
                                st.markdown("---")
                else:
                    st.caption("Внешние источники не найдены.")

        with tab_structure:
            st.subheader(f"Кубы внутри {selected_mc}")
            cubes_data = []
            for cube_name in sorted(list(project._registry.get(selected_mc, []))):
                cube_obj = project.get_cube(selected_mc, cube_name)
                cubes_data.append({
                    "Куб": cube_name,
                    "Формула": cube_obj.formula if cube_obj else ""
                })
            st.dataframe(pd.DataFrame(cubes_data), use_container_width=True)

else:
    st.info("Пожалуйста, загрузите XLSX файл для начала работы.")