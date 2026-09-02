import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import plotly.express as px
from streamlit_agraph import agraph, Node, Edge, Config
import sys
import os

sys.path.append(os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm'))
from infrastructure.graph_db import GraphConnector

st.set_page_config(page_title="Project Olmec: Affirm Intelligence Command Center", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def get_db_driver():
    connector = GraphConnector()
    return connector.driver

driver = get_db_driver()

def get_runs():
    query = """
    MATCH (n) 
    WHERE n.run_id IS NOT NULL 
    RETURN DISTINCT n.run_id AS run_id, count(n) as node_count
    ORDER BY run_id DESC
    """
    with driver.session() as session:
        return [{"id": r["run_id"], "label": f"{r['run_id']} ({r['node_count']} findings)"} for r in session.run(query)]

def fetch_threat_matrix(run_id):
    query = f"""
    MATCH (n)
    WHERE n.run_id = '{run_id}' AND n.impact_score IS NOT NULL
    RETURN coalesce(n.jurisdiction, labels(n)[0]) AS Category, n.impact_score AS Impact, count(n) AS Count
    """
    with driver.session() as session:
        result = session.run(query)
        return pd.DataFrame([r.values() for r in result], columns=result.keys())

def fetch_knowledge_graph(run_id):
    query = f"""
    MATCH (n)-[r]-(t)
    WHERE (n.run_id = '{run_id}' OR t.run_id = '{run_id}')
    AND NOT 'Asset' IN labels(n) AND NOT 'Asset' IN labels(t)
    RETURN coalesce(n.title, n.name, labels(n)[0]) AS SourceTitle, 
           labels(n)[0] AS SourceType, 
           coalesce(t.name, t.title, 'Target') AS Target, 
           type(r) AS RelType
    LIMIT 40
    """
    with driver.session() as session:
        result = session.run(query)
        return [r.data() for r in result]

def fetch_sentiment_timeline(run_id):
    query = f"""
    MATCH (n)
    WHERE n.run_id = '{run_id}' AND (n.event_date IS NOT NULL OR n.timestamp IS NOT NULL)
    RETURN coalesce(n.event_date, n.timestamp) AS Date, 
           toFloat(coalesce(n.sentiment_score, n.confidence, 0.5)) AS Sentiment, 
           labels(n)[0] AS Source
    """
    with driver.session() as session:
        result = session.run(query)
        return pd.DataFrame([r.values() for r in result], columns=result.keys())

def fetch_human_queue(run_id):
    query = f"""
    MATCH (n)
    WHERE n.run_id = '{run_id}' AND NOT coalesce(n.title, '') CONTAINS 'Mock'
    OPTIONAL MATCH (n)-[]-(parent) WHERE parent.title IS NOT NULL
    WITH n, collect(parent)[0] AS p
    RETURN coalesce(n.url, p.url, '#') AS URL, 
           coalesce(n.title, p.title, 'Observation Record') AS Title, 
           coalesce(n.context, n.summary, n.compressed_summary, 'No summary extracted.') AS Snippet, 
           coalesce(n.impact_score, n.validation_status, 'Unrated') AS Status
    LIMIT 10
    """
    with driver.session() as session:
        result = session.run(query)
        return [r.data() for r in result]

st.title("Project Olmec: Affirm Intelligence Command Center")
st.markdown("Live regulatory telemetry and market confidence powered by the OpenClaw autonomous reasoning swarm.")

with st.sidebar:
    st.header("Intelligence Controls")
    
    runs = get_runs()
    selected_run_id = None
    if runs:
        default_idx = next((i for i, r in enumerate(runs) if r['id'] == 'run_1784269240'), 0)
        selected_run_label = st.selectbox("Active Swarm Run", [r['label'] for r in runs], index=default_idx)
        selected_run_id = selected_run_label.split(" ")[0]
    else:
        st.warning("No runs found in database.")

    st.divider()
    st.subheader("Human-in-the-Loop Triage")
    
    if selected_run_id:
        queue_items = fetch_human_queue(selected_run_id)
        if queue_items:
            for i, item in enumerate(queue_items):
                display_title = str(item['Title'])[:45] + "..."
                display_snippet = str(item['Snippet'])[:250] + "..."
                with st.expander(display_title):
                    st.write(display_snippet)
                    st.metric("Impact / Status", str(item['Status']).title())
                    if item['URL'] != '#':
                        st.write(f"[Review Document]({item['URL']})")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Validate", key=f"esc_{i}"):
                            st.success("Validated")
                    with col2:
                        if st.button("Reject", key=f"dis_{i}"):
                            st.info("Rejected")
        else:
            st.success("Triage queue clear for active run.")

if selected_run_id:
    top_col1, top_col2 = st.columns([1, 2])

    with top_col1:
        st.subheader("Active Run Threat Breakdown")
        df_matrix = fetch_threat_matrix(selected_run_id)
        if not df_matrix.empty:
            matrix_pivot = df_matrix.pivot(index='Category', columns='Impact', values='Count').fillna(0)
            fig_heat = px.imshow(matrix_pivot, text_auto=True, color_continuous_scale='Reds', aspect="auto")
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No scoped threat matrix records found for active run.")

    with top_col2:
        st.subheader("Run Sentiment & Confidence Flow")
        df_timeline = fetch_sentiment_timeline(selected_run_id)
        if not df_timeline.empty:
            def parse_date(d):
                try:
                    return pd.to_datetime(float(d), unit='s', utc=True)
                except:
                    return pd.to_datetime(d, errors='coerce', utc=True)
            df_timeline['Date'] = df_timeline['Date'].apply(parse_date)
            df_timeline = df_timeline.dropna(subset=['Date'])
            
            if not df_timeline.empty:
                df_timeline = df_timeline.sort_values(by='Date')
                fig_line = px.line(df_timeline, x='Date', y='Sentiment', color='Source', markers=True, color_discrete_sequence=['#10B981', '#3B82F6'])
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Awaiting valid timestamp telemetry for active run.")
        else:
            st.info("No timestamped telemetry in active run.")

    st.divider()

    st.subheader("Active Swarm Knowledge Graph")
    st.markdown("Entities and policy links mapped strictly during the selected run.")

    graph_data = fetch_knowledge_graph(selected_run_id)
    if graph_data:
        nodes = []
        edges = []
        node_ids = set()

        nodes.append(Node(id="Affirm", label="Affirm", size=30, color="#1D4ED8"))
        node_ids.add("Affirm")

        for record in graph_data:
            source_id = str(record['SourceTitle'])[:35] + "..." 
            source_type = record['SourceType']
            
            color = "#10B981" if source_type == "NewsArticle" else "#F59E0B" if source_type == "Observation" else "#EF4444"
            
            if source_id not in node_ids:
                nodes.append(Node(id=source_id, label=source_id, size=16, color=color))
                node_ids.add(source_id)
                
            edges.append(Edge(source=source_id, target="Affirm", label=record['RelType']))

        config = Config(width=1200, height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6", collapsible=True, physics={"barnesHut": {"gravitationalConstant": -30000}})
        agraph(nodes=nodes, edges=edges, config=config)
    else:
        st.info("Graph database is currently empty for active run.")
