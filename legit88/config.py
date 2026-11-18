"""Reads the secret keys.

Keys are never written in the code. Locally they live in `.streamlit/secrets.toml`
(or in environment variables); on Streamlit Cloud you paste them in the app settings.
"""

import os


def get_secret(name: str):
    """Return a secret from environment variables or Streamlit secrets, or None."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


# The AI model used for extraction (via OpenRouter). Cheap, fast, reads images.
LLM_MODEL = "google/gemini-2.5-flash"
