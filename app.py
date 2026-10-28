import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
import pandas as pd
import datetime
import os
import shutil
import json
import re
import time

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
        .red-badge {
            background-color: #8b0000;
            color: white;
            padding: 3px 8px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 18px;
            border: 1px solid #ff4b4b;
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

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": ""}

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
                return json.load(f)
        except Exception:
            pass
    return {}

def save_students(students_dict):
    try:
        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(students_dict, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def clear_upload_folder():
    for f in os.listdir(UPLOAD_FOLDER):
        if not f.startswith('hw_page_'):
            file_path = os.path.join(UPLOAD_FOLDER, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception:
                pass

def call_gemini_with_retry(client, model_name, contents, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            if response and response.text:
                return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay)
            delay *= 2
    return None

students_db = load_students()
config_data = load_config()

TRANSLATIONS = {
    "Ελληνικά": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*",
        "hw_section": "📖 Φωτογραφίες Εκφώνησης (Homework)",
        "hw_desc": "📸 Τραβήξτε φωτογραφία κάμερας ή ανεβάστε εκφώνηση:",
        "hw_saved": "σελίδα/σελίδες Homework αποθηκεύτηκαν!",
        "class_mgmt": "⚙️ Διαχείριση Τάξης & Τμημάτων",
        "select_class": "Επιλογή Τμήματος:",
        "add_new_class": "➕ Δημιουργία Νέου Τμήματος (π.χ. Β3):",
        "btn_add_class": "Προσθήκη Τμήματος",
        "remove_class": "❌ Διαγραφή Τμήματος:",
        "btn_remove_class": "Διαγραφή Τμήματος",
        "students_in": "Μαθητές Τμήματος",
        "add_student": "Προσθήκη νέου μαθητή:",
        "btn_add": "➕ Προσθήκη Μαθητή",
        "remove_student": "Αφαίρεση μαθητή:",
        "btn_remove": "❌ Διαγραφή Μαθητή",
        "api_prompt": "Εισάγετε Google Gemini API Key",
        "save_api": "💾 Αποθήκευση API Key",
        "api_saved_success": "Το API Key αποθηκεύτηκε επιτυχώς!",
        "menu_title": "📌 Επιλέξτε Λειτουργία (Κάθετο Μενού):",
        "opt1": "📷 1. Αυτόματη Αξιολόγηση Άσκησης",
        "opt2": "📋 2. Εισαγωγή Καταλόγου",
        "opt3": "📊 3. Πίνακας Προόδου & Αναφορές",
        "notebook_sec": "✨ Φωτογράφηση & Μεταφόρτωση Τετραδίων Μαθητών",
        "no_hw_warn": "⚠️ Σημείωση: Δεν έχετε τραβήξει φωτογραφία Homework από την αριστερή στήλη.",
        "batch_upload": "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων:",
        "folder_found": "φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.",
        "btn_evaluate": "🚀 Έναρξη Αξιολόγησης (Γρήγορη Λειτουργία)",
        "eval_success": "Αποθηκεύτηκαν επιτυχώς στον πίνακα προόδου!",
        "view_eval": "🔍 Προβολή Τελευταίας Αξιολόγησης",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "📸 Τραβήξτε φωτογραφία καταλόγου με κάμερα ή ανεβάστε αρχείο:",
        "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
        "stats_sec": "📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style)",
        "btn_close_day": "🚨 Καταγραφή Απουσιών/Ελλείψεων για Σήμερα",
        "manual_delete": "🗑️ Διαγραφή Δεδομένων",
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.<br><span style='font-size: 11px; font-weight: normal;'>(Scroll down to select Department)</span>",
        "alert_box": "⚙️ Πατήστε τα βελάκια <span class=\"red-badge\">&gt;&gt;</span> πάνω αριστερά για Τμήματα &amp; Γλώσσα",
        "uploader_label_hw": "📸 Κάμερα ή Αρχείο Εκφώνησης",
        "uploader_label_notebook": "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων:",
        "expander_class": "🏫 Γρήγορη Επιλογή & Διαχείριση Τμήματος (Πατήστε εδώ)",
        "expander_lang": "🌐 Γρήγορη Αλλαγή Γλώσσας UI (Πατήστε εδώ)",
        "current_class_label": "Τρέχον Τμήμα:",
        "change_class_label": "Αλλαγή Τμήματος:",
        "no_students_yet": "Δεν έχουν προστεθεί μαθητές ακόμα.",
        "section_students_text": "Μαθητές τμήματος",
        "lang_select_label": "Επιλογή Γλώσσας / Language:",
        "box1_title": "🗂️ Κουτάκι 1: Αυτόματη Αξιολόγηση Άσκησης",
        "box2_title": "🗂️ Κουτάκι 2: Εισαγωγή Καταλόγου",
        "box3_title": "🗂️ Κουτάκι 3: Πίνακας Προόδου & Αναφορές",
        "view_photos_folder": "👁️ Προβολή φωτογραφιών στον φάκελο",
        "clear_folder": "🗑️ Εκκαθάριση Φακέλου",
        "roster_photo_caption": "Φωτογραφία Καταλόγου",
        "no_classes_warn": "⚠️ Δεν υπάρχουν διαθέσιμα τμήματα. Δημιουργήστε ένα τμήμα από την αριστερή στήλη για να ξεκινήσετε.",
        "catalog_spinner": "⏳ Το AI αναλύει και οργανώνει τον κατάλογο της τάξης... (Διαρκεί 1-2 λεπτά)",
        "catalog_success": "✅ Ο κατάλογος της τάξης καταχωρήθηκε με επιτυχία!"
    },
    "English": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Smart Teacher Assistant*",
        "hw_section": "📖 Homework Prompt Photos",
        "hw_desc": "📸 Take camera photo or upload assignment pages:",
        "hw_saved": "Homework page(s) saved!",
        "class_mgmt": "⚙️ Class Management & Sections",
        "select_class": "Select Class/Section:",
        "add_new_class": "➕ Add New Section (e.g. B3):",
        "btn_add_class": "Add Section",
        "remove_class": "❌ Delete Section:",
        "btn_remove_class": "Delete Section",
        "students_
