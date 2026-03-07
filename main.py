import streamlit as st
import pandas as pd
import tempfile
import time
import os
import sys

# Добавляем текущую директорию в путь, чтобы импорты работали корректно
sys.path.append(os.path.dirname(__file__))

from core.project import Project
from infrastructure.adapters.dataframe_adapter import DataFrameAdapter
from vizualization.renderers import Visualizer

# --- ИНИЦИАЛИЗАЦИЯ ИНТЕРФЕЙСА ---
st.set_page_config(
    page_title="OptiTrace Pro | Graph Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 OptiTrace Professional")
st.markdown("---")

# --- ЛОГИКА ОБРАБОТКИ ДАННЫХ (КЭШИРУЕМАЯ) ---
@st.cache_resource(show_spinner="Анализ связей и парсинг формул...")
def build_project_cached(df: pd.DataFrame):
    """
    Строит проект один раз и хранит его в памяти. 
    Пересборка только при изменении данных в Excel.
    """
    adapter = DataFrameAdapter(df)
    definitions = adapter.load_definitions()
    
    project = Project()
    project.build_from_definitions(definitions)
    return project

def clean_input_data(df: pd.DataFrame) -> pd.DataFrame:
    """Очистка данных перед обработкой (Senior Safety Check)"""
    # 1. Приводим колонки к нижнему регистру
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # 2. Маппинг имен (если в Excel они отличаются)
    rename_map = {
        'multicube': 'multicubes',
        'cube': 'cubes',
        'multicubes': 'multicubes',
        'cubes': 'cubes'
    }
    df = df.rename(columns=rename_map)
    
    # 3. Удаляем строки без имен кубов или мультикубов (фикс вашей ошибки TypeError)
    df = df.dropna(subset=['cubes', 'multicubes'])
    
    # 4. Принудительно в строку (чтобы исключить float/int в названиях)
    df['cubes'] = df['cubes'].astype(str).str.strip()
    df['multicubes'] = df['multicubes'].astype(str).str.strip()
    
    return df

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Управление")
        
        uploaded_file = st.file_uploader(
            "Загрузите Excel файл модели", 
            type=['xlsx', 'xls'],
            help="Колонки: cubes, multicubes, formula"
        )
        
        if not uploaded_file:
            st.info("Пожалуйста, загрузите файл для визуализации.")
            return

        # Загрузка и первичная очистка
        try:
            raw_df = pd.read_excel(uploaded_file)
            df = clean_input_data(raw_df)
            
            # Строим проект
            project = build_project_cached(df)
            
            st.success(f"Анализ завершен! Кубов: {len(project.cubes)}")
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")
            return

        st.markdown("---")
        st.subheader("🔍 Фильтры графа")
        
        # Безопасное получение списка МК (фикс TypeError со сравнением float)
        all_mc = sorted([str(k) for k in project._registry.keys() if k])
        
        target_mc = st.selectbox("Фокусный мультикуб", all_mc)
        
        mode = st.radio(
            "Режим отображения",
            ["Full", "Cross-MC", "MC Only"],
            index=1,
            help="Full - все связи, Cross-MC - только между МК, MC Only - только агрегаты МК"
        )
        
        show_internal = st.checkbox("Внутренние связи кубов", value=False)
        
        st.markdown("---")
        st.metric("Узлов в базе", project.graph.number_of_nodes())
        st.metric("Связей выявлено", project.graph.number_of_edges())

    # --- ОСНОВНАЯ ОБЛАСТЬ ---
    col_viz, col_data = st.columns([3, 1])

    with col_viz:
        st.subheader(f"Граф зависимостей: {target_mc}")
        
        with st.spinner("Генерация визуализации..."):
            viz = Visualizer(project)
            net = viz.render(
                focus_mc=target_mc,
                show_internal=show_internal,
                mode=mode
            )
            
            # Сохранение и отображение
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp:
                net.save_graph(tmp.name)
                with open(tmp.name, 'r', encoding='utf-8') as f:
                    st.components.v1.html(f.read(), height=800)
                os.unlink(tmp.name)

    with col_data:
        st.subheader("📋 Состав МК")
        
        # Информация о кубах в выбранном МК
        mc_cubes = [c for c in project.cubes.values() if c.parent_multicube == target_mc]
        
        st.write(f"**Мультикуб:** `{target_mc}`")
        st.write(f"**Количество кубов:** {len(mc_cubes)}")
        
        # Поиск по кубам (удобно при 12к элементах)
        search = st.text_input("Поиск куба в этом МК", "")
        
        for c in mc_cubes:
            if search.lower() in c.name.lower():
                icon = "🟢" if c.formula else "🔵"
                with st.expander(f"{icon} {c.name}"):
                    st.code(c.formula if c.formula else "Manual Input", language='sql')

if __name__ == "__main__":
    main()