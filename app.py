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
    try:
        components.html(
            '<script>const audioCtx = new (window.AudioContext || window.webkitAudioContext)(); '
            'function p(f, t, d){setTimeout(()=>{const o = audioCtx.createOscillator(); const g = audioCtx.createGain(); '
            'o.type = "sine"; o.frequency.value = f; g.gain.setValueAtTime(0.1, audioCtx.currentTime); '
            'g.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + t); '
            'o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + t);}, d);} '
            'p(523.25, 0.2, 0); p(659.25, 0.2, 120); p(783.99, 0.4, 240);</script>',
            height=0, width=0
        )
    except Exception:
        pass

# ΑΣΦΑΛΗΣ ΣΥΝΑΡΤΗΣΗ ΜΕ AUTO-RETRY
def call_gemini_safe(client, model_name, contents):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            if response and response.text:
                return response.text
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
    return None

TRANSLATIONS = {
    "Ελληνικά": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*",
        "hw_section": "📖 Εκφώνηση & Σωστή Λύση",
        "hw_desc": "📸 Ανεβάστε την Εκφώνηση ΚΑΙ τη Σωστή Λύση:",
        "hw_saved": "σελίδα/σελίδες Εκφώνησης αποθηκεύτηκαν!",
        "sol_saved": "σελίδα/σελίδες Σωστής Λύσης αποθηκεύτηκαν!",
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
        "api_prompt": "🔑 Google Gemini API Key",
        "save_api": "💾 Αποθήκευση API Key",
        "audio_toggle": "🔊 Ηχητική ειδοποίηση κατά την ολοκλήρωση",
        "api_saved_success": "Το API Key αποθηκεύτηκε επιτυχώς!",
        "menu_title": "📌 Επιλέξτε Λειτουργία (Κάθετο Μενού):",
        "opt1": "📷 1. Υποβοηθούμενη Αξιολόγηση",
        "opt2": "📋 2. Εισαγωγή Καταλόγου",
        "opt3": "📊 3. Πίνακας Προόδου & Αναφορές",
        "batch_upload": "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων (συμπιέζονται αυτόματα):",
        "folder_found": "φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.",
        "clear_notebooks": "🗑️ Εκκαθάριση Φακέλου Τετραδίων",
        "btn_evaluate": "🔍 Δημιουργία Προτεινόμενων Αξιολογήσεων",
        "eval_success": "Η αξιολόγηση ολοκληρώθηκε και αποθηκεύτηκε στον πίνακα προόδου!",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "📸 Τραβήξτε φωτογραφία καταλόγου με κάμερα ή ανεβάστε αρχείο:",
        "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
        "stats_sec": "📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style)",
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.",
        "alert_box": "⚙️ Διαχειριστείτε τα τμήματα από την πλαϊνή μπάρα και εισάγετε το API Key σας παρακάτω.",
        "uploader_label_hw": "📸 Φωτογραφία Εκφώνησης (Homework)",
        "uploader_label_sol": "💡 Φωτογραφία Σωστής Λύσης / Απάντησης",
        "box1_title": "🗂️ Κουτάκι 1: Υποβοηθούμενη Αξιολόγηση Άσκησης",
        "box2_title": "🗂️ Κουτάκι 2: Εισαγωγή Καταλόγου",
        "box3_title": "🗂️ Κουτάκι 3: Πίνακας Προόδου & Αναφορές",
        "roster_photo_caption": "Φωτογραφία Καταλόγου",
        "no_classes_warn": "⚠️ Δεν υπάρχουν διαθέσιμα τμήματα. Δημιουργήστε ένα τμήμα από την πλαϊνή μπάρα για να ξεκινήσετε.",
        "no_students_yet": "Δεν έχουν προστεθεί μαθητές ακόμα.",
        "current_class_label": "Τρέχον Τμήμα:",
        "catalog_spinner": "⏳ Το AI αναλύει και οργανώνει τον κατάλογο της τάξης...",
        "workflow_info": "💡 <b>Υβριδική Λειτουργία:</b> Το AI συγκρίνει Εκφώνηση + Σωστή Λύση με το τετράδιο του μαθητή, προτείνει βαθμό και σχόλια. Ελέγξτε ή εγκρίνετε μαζικά!",
        "hw_warn_box1": "⚠️ Σημείωση: Ανεβάστε πρώτα την εκφώνηση της άσκησης από το πλαϊνό μενού (Sidebar).",
        "hw_err_eval": "⚠️ Παρακαλώ ανεβάστε πρώτα την εκφώνηση της άσκησης στο πλαϊνό μενού!",
        "no_notebooks_warn": "⚠️ Δεν βρέθηκαν φωτογραφίες τετραδίων. Ανεβάστε πρώτα φωτογραφίες τετραδίων.",
        "eval_complete_msg": "🎉 Η ανάλυση AI ολοκληρώθηκε επιτυχώς! Επιθεωρήστε, διορθώστε ή εγκρίνετε μαζικά παρακάτω.",
        "bulk_success_msg": "🎉 Όλες οι βαθμολογίες εγκρίθηκαν και αποθηκεύτηκαν μαζικά στον Πίνακα Προόδου!"
    },
    "English": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Smart Teacher Assistant*",
        "hw_section": "📖 Homework Prompt & Solution",
        "hw_desc": "📸 Upload Homework Assignment & Official Solution:",
        "hw_saved": "Homework page(s) saved & compressed!",
        "sol_saved": "Solution page(s) saved & compressed!",
        "class_mgmt": "⚙️ Class Management & Sections",
        "select_class": "Select Class/Section:",
        "add_new_class": "➕ Add New Section (e.g. B3):",
        "btn_add_class": "Add Section",
        "remove_class": "❌ Delete Section:",
        "btn_remove_class": "Delete Section",
        "students_in": "Students in Section",
        "add_student": "Add new student:",
        "btn_add": "➕ Add Student",
        "remove_student": "Remove student:",
        "btn_remove": "❌ Delete Student",
        "api_prompt": "🔑 Google Gemini API Key",
        "save_api": "💾 Save API Key",
        "audio_toggle": "🔊 Enable Sound Notification on Completion",
        "api_saved_success": "API Key saved successfully!",
        "menu_title": "📌 Select Mode (Vertical Menu):",
        "opt1": "📷 1. Assisted Grading",
        "opt2": "📋 2. Import Roster",
        "opt3": "📊 3. Progress Table & Reports",
        "batch_upload": "📸 Take photo with camera or select notebook files (compressed automatically):",
        "folder_found": "student notebook photos ready in folder.",
        "clear_notebooks": "🗑️ Clear Notebooks Folder",
        "btn_evaluate": "🔍 Generate Proposed Evaluations",
        "eval_success": "Successfully evaluated and saved to Progress Table!",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "📸 Take roster photo with camera or upload file:",
        "btn_read_names": "🤖 Read & Auto-Save Roster",
        "stats_sec": "📊 Class Progress Matrix (Excel Style)",
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.",
        "alert_box": "⚙️ Manage sections and language from the sidebar, and enter your API Key below.",
        "uploader_label_hw": "📸 Assignment Prompt Photo",
        "uploader_label_sol": "💡 Official Answer/Solution Photo",
        "box1_title": "🗂️ Box 1: AI-Assisted Homework Grading",
        "box2_title": "🗂️ Box 2: Import Roster",
        "box3_title": "🗂️ Box 3: Progress Table & Reports",
        "roster_photo_caption": "Roster Photo",
        "no_classes_warn": "⚠️ No sections available. Create a section from the sidebar to get started.",
        "no_students_yet": "No students added yet.",
        "current_class_label": "Current Section:",
        "catalog_spinner": "⏳ AI is analyzing and organizing the class list...",
        "workflow_info": "💡 <b>Hybrid Workflow:</b> AI compares homework + official solution vs student notebook. Review individually or use Fast-Track Bulk Approval!",
        "hw_warn_box1": "⚠️ Note: Please upload the homework prompt first from the sidebar.",
        "hw_err_eval": "⚠️ Please upload the homework prompt first in the sidebar!",
        "no_notebooks_warn": "⚠️ No notebook photos found. Please upload notebook photos first.",
        "eval_complete_msg": "🎉 AI analysis completed successfully! Review, correct, or approve in bulk below.",
        "bulk_success_msg": "🎉 All grades approved and saved in bulk to the Progress Table!"
    }
}

# --- 3. SIDEBAR: ΓΛΩΣΣΑ, ΕΚΦΩΝΗΣΗ, ΣΩΣΤΗ ΛΥΣΗ & ΤΜΗΜΑΤΑ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
lang_keys = list(TRANSLATIONS.keys())
current_lang_index = lang_keys.index(st.session_state["app_lang"]) if st.session_state["app_lang"] in lang_keys else 0

selected_sidebar_lang = st.sidebar.selectbox("Choose UI Language:", lang_keys, index=current_lang_index, key="sidebar_lang_select")
if selected_sidebar_lang != st.session_state["app_lang"]:
    st.session_state["app_lang"] = selected_sidebar_lang
    st.rerun()

app_lang = st.session_state["app_lang"]
t = TRANSLATIONS.get(app_lang, TRANSLATIONS["Ελληνικά"])

st.markdown(t["title"])
st.markdown(t["subtitle"])

st.sidebar.markdown("---")
st.sidebar.header(t["hw_section"])
st.sidebar.write(t["hw_desc"])

hw_files = st.sidebar.file_uploader(
    t["uploader_label_hw"],
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="hw_high_res_uploader"
)

if hw_files:
    with st.sidebar.status("🔄 Επεξεργασία & συμπίεση εκφώνησης...", expanded=True) as status:
        old_hw = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('hw_page_')]
        for p in old_hw:
            try:
                os.remove(p)
            except:
                pass

        total_hw = len(hw_files)
        for idx, hw_f in enumerate(hw_files):
            st.write(f"Συμπίεση αρχείου {idx + 1} από {total_hw}...")
            compressed_bytes = compress_image(hw_f.getbuffer())
            hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{idx}.jpg")
            with open(hw_path, "wb") as f:
                f.write(compressed_bytes)
        status.update(label="✅ Η εκφώνηση αποθηκεύτηκε με επιτυχία!", state="complete", expanded=False)

sol_files = st.sidebar.file_uploader(
    t["uploader_label_sol"],
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="sol_high_res_uploader"
)

if sol_files:
    with st.sidebar.status("🔄 Επεξεργασία & συμπίεση σωστής λύσης...", expanded=True) as status:
        old_sol = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('sol_page_')]
        for p in old_sol:
            try:
                os.remove(p)
            except:
                pass

        total_sol = len(sol_files)
        for idx, sol_f in enumerate(sol_files):
            st.write(f"Συμπίεση λύσης {idx + 1} από {total_sol}...")
            compressed_bytes = compress_image(sol_f.getbuffer())
            sol_path = os.path.join(UPLOAD_FOLDER, f"sol_page_{idx}.jpg")
            with open(sol_path, "wb") as f:
                f.write(compressed_bytes)
        status.update(label="✅ Η σωστή λύση αποθηκεύτηκε με επιτυχία!", state="complete", expanded=False)

homework_images = []
hw_paths_in_folder = sorted([os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('hw_page_')])
for p in hw_paths_in_folder:
    try:
        homework_images.append(Image.open(p))
    except Exception:
        pass

solution_images = []
sol_paths_in_folder = sorted([os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('sol_page_')])
for p in sol_paths_in_folder:
    try:
        solution_images.append(Image.open(p))
    except Exception:
        pass

if homework_images or solution_images:
    if homework_images:
        st.sidebar.success(f"✅ {len(homework_images)} {t['hw_saved']}")
    if solution_images:
        st.sidebar.success(f"✅ {len(solution_images)} {t['sol_saved']}")
        
    if st.sidebar.button("🗑️ Εκκαθάριση Εκφώνησης & Λύσης", key="clear_hw_btn"):
        with st.spinner("🗑️ Διαγραφή αρχείων..."):
            for p in hw_paths_in_folder + sol_paths_in_folder:
                try:
                    os.remove(p)
                except:
                    pass
        st.rerun()

st.sidebar.markdown(f"""
    <div class="sidebar-stop-box">
        {t['sidebar_stop_text']}
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header(t["class_mgmt"])

new_class_input = st.sidebar.text_input(t["add_new_class"])
if st.sidebar.button(t["btn_add_class"]):
    n_class = new_class_input.strip().upper()
    if n_class:
        if n_class not in st.session_state["students_db"]:
            with st.spinner(f"📁 Δημιουργία τμήματος {n_class}..."):
                st.session_state["students_db"][n_class] = []
                save_students(st.session_state["students_db"])
            st.sidebar.success(f"Created section: {n_class}")
            st.session_state["selected_class"] = n_class
            st.rerun()
        else:
            st.sidebar.warning("Section already exists.")

if st.session_state["students_db"]:
    class_to_remove = st.sidebar.selectbox(t["remove_class"], ["-- Select --"] + list(st.session_state["students_db"].keys()))
    if st.sidebar.button(t["btn_remove_class"]):
        if class_to_remove != "-- Select --":
            with st.spinner(f"🗑️ Διαγραφή τμήματος {class_to_remove}..."):
                del st.session_state["students_db"][class_to_remove]
                save_students(st.session_state["students_db"])
            st.sidebar.warning(f"Deleted section: {class_to_remove}")
            if st.session_state["students_db"]:
                st.session_state["selected_class"] = list(st.session_state["students_db"].keys())[0]
            else:
                if "selected_class" in st.session_state:
                    del st.session_state["selected_class"]
            st.rerun()

if not st.session_state["students_db"]:
    st.warning(t["no_classes_warn"])
else:
    if "selected_class" not in st.session_state or st.session_state["selected_class"] not in st.session_state["students_db"]:
        st.session_state["selected_class"] = list(st.session_state["students_db"].keys())[0]

    selected_class_sidebar = st.sidebar.selectbox(
        t["select_class"], 
        list(st.session_state["students_db"].keys()), 
        index=list(st.session_state["students_db"].keys()).index(st.session_state["selected_class"])
    )
    if selected_class_sidebar != st.session_state["selected_class"]:
        st.session_state["selected_class"] = selected_class_sidebar
        st.rerun()

    selected_class = st.session_state["selected_class"]

    st.sidebar.subheader(f"{t['students_in']} {selected_class}")
    new_student = st.sidebar.text_input(t["add_student"])
    if st.sidebar.button(t["btn_add"]):
        if new_student and new_student not in st.session_state["students_db"][selected_class]:
            with st.spinner("➕ Προσθήκη μαθητή..."):
                st.session_state["students_db"][selected_class].append(new_student)
                save_students(st.session_state["students_db"])
            st.sidebar.success(f"Added {new_student}")
            st.rerun()

    if st.session_state["students_db"][selected_class]:
        student_to_remove = st.sidebar.selectbox(t["remove_student"], ["-- Select --"] + st.session_state["students_db"][selected_class])
        if st.sidebar.button(t["btn_remove"]):
            if student_to_remove != "-- Select --":
                with st.spinner("❌ Αφαίρεση μαθητή..."):
                    st.session_state["students_db"][selected_class].remove(student_to_remove)
                    save_students(st.session_state["students_db"])
                st.sidebar.warning(f"Removed {student_to_remove}")
                st.rerun()
    else:
        st.sidebar.info(t["no_students_yet"])

# --- 4. ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ, API KEY & AUDIO TOGGLE ---
st.markdown(f"""
    <div class="custom-alert-box">
        {t['alert_box']}
    </div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown("### " + t["api_prompt"])
    current_api_key = st.session_state["config"].get("api_key", "")
    api_key_input = st.text_input("API Key:", value=current_api_key, type="password", key="main_api_key_input", label_visibility="collapsed")
    
    audio_enabled_val = st.session_state["config"].get("audio_target", True)
    audio_toggle = st.checkbox(t["audio_toggle"], value=audio_enabled_val, key="audio_toggle_box")
    if audio_toggle != audio_enabled_val:
        st.session_state["config"]["audio_target"] = audio_toggle
        save_config(st.session_state["config"])

    if st.button(t["save_api"]):
        if api_key_input.strip():
            with st.spinner("💾 Αποθήκευση ρυθμίσεων & API Key..."):
                st.session_state["config"]["api_key"] = api_key_input.strip()
                save_config(st.session_state["config"])
            st.success(t["api_saved_success"])
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Please enter a valid API Key.")

st.markdown("---")

st.markdown(f"""
    <div class="custom-info-card">
        {t['workflow_info']}
    </div>
""", unsafe_allow_html=True)

if not st.session_state["students_db"]:
    st.info("👈 Please create at least one section from the sidebar to get started.")
else:
    mode = st.radio(
        t["menu_title"],
        (t["opt1"], t["opt2"], t["opt3"]),
        horizontal=True
    )

    if mode == t["opt1"]:
        st.subheader(t["box1_title"])
        if not homework_images:
            st.warning(t["hw_warn_box1"])
        
        notebook_files = st.file_uploader(
            t["batch_upload"],
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="notebook_batch_uploader"
        )
        
        if notebook_files:
            with st.status("🔄 Συμπίεση & αποθήκευση φωτογραφιών τετραδίων...", expanded=True) as nb_status:
                for idx, nb_file in enumerate(notebook_files):
                    st.write(f"Επεξεργασία τετραδίου {idx + 1} από {len(notebook_files)}...")
                    compressed_bytes = compress_image(nb_file.getbuffer())
                    unique_filename = f"student_page_{int(time.time())}_{idx}.jpg"
                    nb_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    with open(nb_path, "wb") as f:
                        f.write(compressed_bytes)
                nb_status.update(label="✅ Τα
