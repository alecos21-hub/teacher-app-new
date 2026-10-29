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
        .custom-spinner-box {
            background-color: #ff4b4b;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            text-align: center;
            margin: 15px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            border: 2px solid #8b0000;
        }
        .api-box {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ddd;
            margin-bottom: 20px;
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

def load_grades():
    if os.path.exists(GRADES_FILE):
        try:
            return pd.read_csv(GRADES_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["Section", "Student", "Date", "Score", "Feedback"])

def save_grades_df(df):
    try:
        df.to_csv(GRADES_FILE, index=False)
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
if "grades_df" not in st.session_state:
    st.session_state["grades_df"] = load_grades()

TRANSLATIONS = {
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
        "students_in": "Students in Section",
        "add_student": "Add new student:",
        "btn_add": "➕ Add Student",
        "remove_student": "Remove student:",
        "btn_remove": "❌ Delete Student",
        "api_prompt": "🔑 Google Gemini API Key",
        "save_api": "💾 Save API Key",
        "api_saved_success": "API Key saved successfully!",
        "menu_title": "📌 Select Mode (Vertical Menu):",
        "opt1": "📷 1. Automatic Grading",
        "opt2": "📋 2. Import Roster",
        "opt3": "📊 3. Progress Table & Reports",
        "notebook_sec": "✨ Capture & Upload Student Notebooks",
        "no_hw_warn": "⚠️ Note: You have not taken a Homework prompt photo from the left sidebar.",
        "batch_upload": "📸 Take photo with camera or select notebook files:",
        "folder_found": "student notebook photos ready in folder.",
        "btn_evaluate": "🚀 Start Grading (Fast Mode)",
        "eval_success": "Successfully evaluated and saved to Progress Table!",
        "view_eval": "🔍 View Latest Evaluation",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "📸 Take roster photo with camera or upload file:",
        "btn_read_names": "🤖 Read & Auto-Save Roster",
        "stats_sec": "📊 Class Progress Matrix (Excel Style)",
        "btn_close_day": "🚨 Mark Missing Homework for Today",
        "manual_delete": "🗑️ Delete Records",
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.<br><span style='font-size: 11px; font-weight: normal;'>(Scroll down to select Department)</span>",
        "alert_box": "⚙️ Manage sections and language from the sidebar, and enter your API Key below.",
        "uploader_label_hw": "📸 Camera or Assignment File",
        "uploader_label_notebook": "📸 Take photo with camera or select notebook files:",
        "expander_class": "🏫 Quick Class Selection & Management (Click here)",
        "expander_lang": "🌐 Quick UI Language Change (Click here)",
        "current_class_label": "Current Section:",
        "change_class_label": "Change Section:",
        "no_students_yet": "No students added yet.",
        "section_students_text": "Students in section",
        "lang_select_label": "UI Language / Language:",
        "box1_title": "🗂️ Box 1: Automatic Homework Grading",
        "box2_title": "🗂️ Box 2: Import Roster",
        "box3_title": "🗂️ Box 3: Progress Table & Reports",
        "view_photos_folder": "👁️ View folder photos",
        "clear_folder": "🗑️ Clear Folder",
        "roster_photo_caption": "Roster Photo",
        "no_classes_warn": "⚠️ No sections available. Create a section from the sidebar to get started.",
        "catalog_spinner": "⏳ AI is analyzing and organizing the class list... (Takes 1-2 minutes)",
        "eval_spinner": "⏳ AI is grading student submissions...",
        "catalog_success": "✅ Class list registered successfully!"
    },
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
        "api_prompt": "🔑 Google Gemini API Key",
        "save_api": "💾 Αποθήκευση API Key",
        "api_saved_success": "Το API Key αποθηκεύτηκε επιτυχώς!",
        "menu_title": "📌 Επιλέξτε Λειτουργία (Κάθετο Μενού):",
        "opt1": "📷 1. Αυτόματη Αξιολόγηση Άσκησης",
        "opt2": "📋 2. Εισαγωγή Καταλόγου",
        "opt3": "📊 3. Πίνακας Προόδου & Αναφορές",
        "notebook_sec": "✨ Φωτογράφηση & Μεταφόρτωση Τετραδίων Μαθητών",
        "no_hw_warn": "⚠️ Σημείωση: Δεν έχετε τραβήξει φωτογραφία Homework από το πλαϊνό μενού.",
        "batch_upload": "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων:",
        "folder_found": "φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.",
        "btn_evaluate": "🚀 Έναρξη Αξιολόγησης (Γρήγορη Λειτουργία)",
        "eval_success": "Η αξιολόγηση ολοκληρώθηκε και αποθηκεύτηκε στον πίνακα προόδου!",
        "view_eval": "🔍 Προβολή Τελευταίας Αξιολόγησης",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "📸 Τραβήξτε φωτογραφία καταλόγου με κάμερα ή ανεβάστε αρχείο:",
        "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
        "stats_sec": "📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style)",
        "btn_close_day": "🚨 Καταγραφή Απουσιών/Ελλείψεων για Σήμερα",
        "manual_delete": "🗑️ Διαγραφή Δεδομένων",
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.",
        "alert_box": "⚙️ Διαχειριστείτε τα τμήματα από την πλαϊνή μπάρα και εισάγετε το API Key σας παρακάτω.",
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
        "no_classes_warn": "⚠️ Δεν υπάρχουν διαθέσιμα τμήματα. Δημιουργήστε ένα τμήμα από την πλαϊνή μπάρα για να ξεκινήσετε.",
        "catalog_spinner": "⏳ Το AI αναλύει και οργανώνει τον κατάλογο της τάξης... (Διαρκεί 1-2 λεπτά)",
        "eval_spinner": "⏳ Το AI αξιολογεί τα τετράδια των μαθητών...",
        "catalog_success": "✅ Ο κατάλογος της τάξης καταχωρήθηκε με επιτυχία!"
    }
}

# --- 3. SIDEBAR: ΜΟΝΟ ΓΛΩΣΣΑ, ΕΚΦΩΝΗΣΗ & ΤΜΗΜΑΤΑ ---
if "app_lang" not in st.session_state:
    st.session_state["app_lang"] = "English"

st.sidebar.header("🌐 App Language / Γλώσσα")
selected_sidebar_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=list(TRANSLATIONS.keys()).index(st.session_state["app_lang"]), key="sidebar_lang_select")
if selected_sidebar_lang != st.session_state["app_lang"]:
    st.session_state["app_lang"] = selected_sidebar_lang
    st.rerun()

app_lang = st.session_state["app_lang"]
t = TRANSLATIONS.get(app_lang, TRANSLATIONS["English"])

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

homework_images = []
if hw_files:
    for idx, hw_f in enumerate(hw_files):
        hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{idx}.jpg")
        with open(hw_path, "wb") as f:
            f.write(hw_f.getbuffer())
        try:
            img = Image.open(hw_path)
            img.verify()
            homework_images.append(Image.open(hw_path))
        except Exception:
            pass
    st.sidebar.success(f"✅ {len(homework_images)} {t['hw_saved']}")

st.sidebar.markdown(f"""
    <div class="sidebar-stop-box">
        {t["sidebar_stop_text"]}
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header(t["class_mgmt"])

new_class_input = st.sidebar.text_input(t["add_new_class"])
if st.sidebar.button(t["btn_add_class"]):
    n_class = new_class_input.strip().upper()
    if n_class:
        if n_class not in students_db:
            students_db[n_class] = []
            save_students(students_db)
            st.sidebar.success(f"Created section: {n_class}")
            st.session_state["selected_class"] = n_class
            st.rerun()
        else:
            st.sidebar.warning("Section already exists.")

if students_db:
    class_to_remove = st.sidebar.selectbox(t["remove_class"], ["-- Select --"] + list(students_db.keys()))
    if st.sidebar.button(t["btn_remove_class"]):
        if class_to_remove != "-- Select --":
            del students_db[class_to_remove]
            save_students(students_db)
            st.sidebar.warning(f"Deleted section: {class_to_remove}")
            if students_db:
                st.session_state["selected_class"] = list(students_db.keys())[0]
            else:
                if "selected_class" in st.session_state:
                    del st.session_state["selected_class"]
            st.rerun()

if not students_db:
    st.warning(t["no_classes_warn"])
else:
    if "selected_class" not in st.session_state or st.session_state["selected_class"] not in students_db:
        st.session_state["selected_class"] = list(students_db.keys())[0]

    selected_class_sidebar = st.sidebar.selectbox(
        t["select_class"], 
        list(students_db.keys()), 
        index=list(students_db.keys()).index(st.session_state["selected_class"])
    )
    if selected_class_sidebar != st.session_state["selected_class"]:
        st.session_state["selected_class"] = selected_class_sidebar
        st.rerun()

    selected_class = st.session_state["selected_class"]

    st.sidebar.subheader(f"{t['students_in']} {selected_class}")
    new_student = st.sidebar.text_input(t["add_student"])
    if st.sidebar.button(t["btn_add"]):
        if new_student and new_student not in students_db[selected_class]:
            students_db[selected_class].append(new_student)
            save_students(students_db)
            st.sidebar.success(f"Added {new_student}")
            st.rerun()

    if students_db[selected_class]:
        student_to_remove = st.sidebar.selectbox(t["remove_student"], ["-- Select --"] + students_db[selected_class])
        if st.sidebar.button(t["btn_remove"]):
            if student_to_remove != "-- Select --":
                students_db[selected_class].remove(student_to_remove)
                save_students(students_db)
                st.sidebar.warning(f"Removed {student_to_remove}")
                st.rerun()
    else:
        st.sidebar.info(t["no_students_yet"])

# --- 4. ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ & API KEY ΣΤΗ ΔΕΞΙΑ/ΚΕΝΤΡΙΚΗ ΟΘΟΝΗ ---
st.markdown(f"""
    <div class="custom-alert-box">
        {t["alert_box"]}
    </div>
""", unsafe_allow_html=True)

# Κεντρικό πεδίο API Key
with st.container():
    st.markdown("### " + t["api_prompt"])
    current_api_key = config_data.get("api_key", "")
    api_key_input = st.text_input("API Key:", value=current_api_key, type="password", key="main_api_key_input", label_visibility="collapsed")
    if st.button(t["save_api"]):
        if api_key_input.strip():
            config_data["api_key"] = api_key_input.strip()
            save_config(config_data)
            st.success(t["api_saved_success"])
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Please enter a valid API Key.")

st.markdown("---")

if not students_db:
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
            st.warning(t["no_hw_warn"])
        
        notebook_files = st.file_uploader(
            t["batch_upload"],
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="notebook_batch_uploader"
        )
        
        if notebook_files:
            clear_upload_folder()
            for idx, nb_file in enumerate(notebook_files):
                nb_path = os.path.join(UPLOAD_FOLDER, f"student_page_{idx}.jpg")
                with open(nb_path, "wb") as f:
                    f.write(nb_file.getbuffer())
            
            notebook_count = len(notebook_files)
            st.success(f"✅ {notebook_count} {t['folder_found']}")
        
        if st.button(t["btn_evaluate"]):
            api_key_val = config_data.get("api_key", "").strip()
            if not api_key_val:
                st.error("⚠️ Please enter your Gemini API Key first above!")
            else:
                try:
                    spinner_placeholder = st.empty()
                    spinner_placeholder.markdown(f"""
                        <div class="custom-spinner-box">
                            {t["eval_spinner"]}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    client = genai.Client(api_key=api_key_val)
                    
                    nb_images_paths = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('student_page_')]
                    
                    if not nb_images_paths:
                        spinner_placeholder.empty()
                        st.warning("⚠️ No student notebook photos found. Please upload or take photos first.")
                    else:
                        new_records = []
                        today_str = datetime.date.today().strftime("%Y-%m-%d")
                        
                        for nb_p in nb_images_paths:
                            nb_img = Image.open(nb_p)
                            contents_to_send = homework_images + [nb_img, "Analyze this student's solution against the homework prompt. Identify the student's name if written, give a score from 0 to 100, and short feedback. Return ONLY valid JSON format: {\"student_name\": \"...\", \"score\": 85, \"feedback\": \"...\"}"]
                            
                            resp_text = call_gemini_with_retry(client, 'gemini-3.8-flash', contents_to_send)
                            if resp_text:
                                clean_resp = resp_text.replace("```json", "").replace("```", "").strip()
                                try:
                                    res_data = json.loads(clean_resp)
                                    s_name = res_data.get("student_name", "Unknown")
                                    s_score = res_data.get("score", 0)
                                    s_feedback = res_data.get("feedback", "")
                                    
                                    new_records.append({
                                        "Section": selected_class,
                                        "Student": s_name,
                                        "Date": today_str,
                                        "Score": s_score,
                                        "Feedback": s_feedback
                                    })
                                except Exception:
                                    pass
                        
                        spinner_placeholder.empty()
                        
                        if new_records:
                            df_new = pd.DataFrame(new_records)
                            st.session_state["grades_df"] = pd.concat([st.session_state["grades_df"], df_new], ignore_index=True)
                            save_grades_df(st.session_state["grades_df"])
                            st.success(f"✅ {t['eval_success']}")
                        else:
                            st.error("⚠️ Could not extract grading data from the submissions. Please try again.")
                except Exception as e:
                    if 'spinner_placeholder' in locals():
                        spinner_placeholder.empty()
                    st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == t["opt2"]:
        st.subheader(t["box2_title"])
        st.write(f"**{t['current_class_label']} {selected_class}**")
        
        catalog_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="catalog_uploader")
        if catalog_file:
            catalog_path = os.path.join(UPLOAD_FOLDER, "catalog_temp.jpg")
            with open(catalog_path, "wb") as f:
                f.write(catalog_file.getbuffer())
            
            st.image(catalog_path, caption=t["roster_photo_caption"], width=300)
            
            if st.button(t["btn_read_names"]):
                api_key_val = config_data.get("api_key", "").strip()
                if not api_key_val:
                    st.error("⚠️ Please enter your Gemini API Key first above!")
                else:
                    try:
                        spinner_placeholder = st.empty()
                        spinner_placeholder.markdown(f"""
                            <div class="custom-spinner-box">
                                {t["catalog_spinner"]}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        client = genai.Client(api_key=api_key_val)
                        img_to_send = Image.open(catalog_path)
                        
                        prompt = (
                            "Look at this image containing a class roster or list of student names. "
                            "Extract all student names. Return ONLY a valid JSON list of strings, "
                            "where each string is a student's full name (e.g., [\"John Doe\", \"Maria Smith\"]). "
                            "Do not include any extra text, markdown formatting blocks like ```json, or explanations."
                        )
                        
                        response_text = call_gemini_with_retry(client, 'gemini-3.8-flash', [img_to_send, prompt])
                        
                        spinner_placeholder.empty()
                        
                        if response_text:
                            clean_text = response_text.replace("```json", "").replace("```", "").strip()
                            parsed_names = json.loads(clean_text)
                            
                            if isinstance(parsed_names, list) and parsed_names:
                                added_count = 0
                                for name in parsed_names:
                                    clean_name = str(name).strip()
                                    if clean_name and clean_name not in students_db[selected_class]:
                                        students_db[selected_class].append(clean_name)
                                        added_count += 1
                                
                                save_students(students_db)
                                st.success(f"✅ Successfully read! Added {added_count} new students to section {selected_class}.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("⚠️ No clear names found in the image. Please try a clearer picture.")
                        else:
                            st.error("⚠️ Error reading roster, please try again.")
                    except Exception as e:
                        if 'spinner_placeholder' in locals():
                            spinner_placeholder.empty()
                        st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == t["opt3"]:
        st.subheader(t["box3_title"])
        st.write(f"📊 {t['stats_sec']} - {selected_class}")
        
        section_grades = st.session_state["grades_df"][st.session_state["grades_df"]["Section"] == selected_class] if not st.session_state["grades_df"].empty else pd.DataFrame()
        
        if students_db[selected_class]:
            students_list = students_db[selected_class]
            df_progress = pd.DataFrame({"Student": students_list})
            
            if not section_grades.empty:
                df_progress = pd.merge(df_progress, section_grades[["Student", "Date", "Score", "Feedback"]], on="Student", how="left")
            
            st.dataframe(df_progress, use_container_width=True)
        else:
            st.info(t["no_students_yet"])
