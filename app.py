import streamlit as st
import requests

st.set_page_config(page_title="WebUI Streamlit", layout="wide")

st.title("WebUI Streamlit Application")
st.markdown("This interface connects to the FastAPI backend.")

# Sidebar for controls
st.sidebar.header("Controls")
if st.sidebar.button("Ping Backend"):
    try:
        response = requests.get("http://127.0.0.1:8000/")
        if response.status_code == 200:
            st.success(f"Backend says: {response.json()}")
        else:
            st.error(f"Backend returned status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Make sure api.py is running.")

# Main area
st.subheader("Data View")
if st.button("Fetch Data"):
    try:
        response = requests.get("http://127.0.0.1:8000/data")
        if response.status_code == 200:
            data = response.json().get("data", [])
            st.line_chart(data)
        else:
            st.warning("Failed to fetch data.")
    except Exception as e:
        st.error(f"Error: {e}")
