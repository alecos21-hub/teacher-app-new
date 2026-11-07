import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
import pandas as pd
import datetime
import os
import json
import re
import time
import io

# --- 1. ΔΙΑΜΟΡΦΩΣΗ ΣΕΛΙΔΑΣ & CUSTOM CSS ---
st.set_page_config(
    page_title="GradeMind AI – Smart Homework & Test Grader", 
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
        .custom-alert-box {
            background-color: #ff4b4b;
            color: white;
            padding: 12px 18px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            text-align: center;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        }
        .custom-info-card {
            background-color: #eef6ff;
            color: #1e3a8a;
            padding: 15px 20px;
            border-radius: 10px;
            border-left: 5px solid #2563eb;
            font-size: 14px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .sidebar-stop-box {
            background-color: #ff4b4b;
            color: white;
            padding: 12px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
            text-align: center;
            margin-top: 15px;
            margin-bottom: 15px;
            box-shadow: 0 3px 5px rgba(0,0,0,0.25);
            border: 1px solid #ff0000;
        }
        [data-testid="stFileUploader"] {
            border: 2px dashed #ff4b4b !important;
            padding: 15px !important;
            border-radius: 12px !important;
            background-color: #fff5f5 !important;
        }
    </style>
""", unsafe_allow_html=True)

UPLOAD_FOLDER = "uploads_folder"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

STUDENTS_FILE = "students_db.json"
GRADES_FILE = "grades_db.csv"
CONFIG_FILE = "config.json"

# --- 2. ΣΥΜΠΙΕΣΗ ΕΙΚΟΝΩΝ ΜΕ ΟΠΤΙΚΗ ΕΝΗΜΕΡΩΣΗ ---
def compress_image(image_bytes, max_size=(1200, 1200), quality=80):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    except Exception:
        return image_bytes

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"api_key": "", "audio_target": True}

def save_config(config_dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_students():
    if os.path.exists(STUDENTS_FILE):
        try:
            with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_students(students_dict):
    try:
        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(students_dict, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_grades():
    if os.path.exists(GRADES_FILE):
        try:
            df = pd.read_csv(GRADES_FILE)
            if not df.empty and "Section" in df.columns:
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=["Section", "Student", "Date", "Score", "Feedback"])

def save_grades_df(df):
    try:
        df.to_csv(GRADES_FILE, index=False)
    except Exception:
        pass

# --- SESSION STATE INITIALIZATION ΜΕ PROGRESS BAR ---
if "initialized" not in st.session_state:
    with st.spinner("🔄 Εκκίνηση συστήματος και φόρτωση βάσης δεδομένων..."):
        progress_bar = st.progress(0)
        st.session_state["config"] = load_config()
        progress_bar.progress(33)
        time.sleep(0.2)
        st.session_state["students_db"] = load_students()
        progress_bar.progress(66)
        time.sleep(0.2)
        st.session_state["grades_df"] = load_grades()
        progress_bar.progress(100)
        time.sleep(0.2)
        progress_bar.empty()
        st.session_state["initialized"] = True

if "app_lang" not in st.session_state:
    st.session_state["app_lang"] = "Ελληνικά"

if "pending_evaluations" not in st.session_state:
    st.session_state["pending_evaluations"] = []

def play_success_sound():
    sound_html = """
        <script>
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            function playTone(freq, time, delay) {
                setTimeout(() => {
                    const osc = audioCtx.createOscillator();
                    const gain = audioCtx.createGain();
                    osc.type = 'sine';
                    osc.frequency
