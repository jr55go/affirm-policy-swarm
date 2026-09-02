import streamlit as st
from neo4j import GraphDatabase
import sys
import os

sys.path.append(os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm"))
from infrastructure.graph_db import GraphConnector

st.set_page_config(page_title="Olmec | Executive Intelligence", layout="centered", initial_sidebar_state="collapsed")

hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stChatInputContainer {padding-bottom: 20px;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

@st.cache_resource
def get_db_driver():
    connector = GraphConnector()
    return connector.driver

driver = get_db_driver()

def extract_text(record):
    n_props = record.get("n_props") or {}
    p_props = record.get("p_props") or {}
    
    ignore_keys = {"run_id", "impact_score", "jurisdiction", "validation_status", "id", "labels", "type", "url"}
    
    candidates = []
    for props in [n_props, p_props]:
        for k, v in props.items():
            if k.lower() not in ignore_keys and isinstance(v, str) and len(v.strip()) > 5:
                candidates.append(v.strip())
    
    if candidates:
        candidates.sort(key=len, reverse=True)
        return candidates[0]
        
    return "Observation record verified in active intelligence graph."

