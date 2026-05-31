"""
Environment variable helper — works in both local (.env) and Streamlit Cloud
(st.secrets) deployments without code changes in every module.

Priority:
  1. os.environ  (set by python-dotenv load_dotenv() from .env locally)
  2. st.secrets  (set in Streamlit Cloud's secrets UI)
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        import streamlit as st
        val = st.secrets.get(key, default)
        if val:
            os.environ[key] = str(val)   # cache for subsequent os.getenv() calls
        return str(val) if val else default
    except Exception:
        return default
