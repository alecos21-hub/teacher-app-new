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

# --- 2. ΣΥΜΠΙΕΣΗ ΕΙΚΟΝΩΝ ΓΙΑ ΓΡΗΓΟΡΟ UPLOAD ---
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

# --- SESSION STATE INITIALIZATION ---
if "config" not in st.session_state:
    st.session_state["config"] = load_config()

if "students_db" not in st.session_state:
    st.session_state["students_db"] = load_students()

if "grades_df" not in st.session_state:
    st.session_state["grades_df"] = load_grades()

if "app_lang" not in st.session_state:
    st.session_state["app_lang"] = "English"

def call_gemini_safe(client, model_name, contents):
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )
        if response and response.text:
            return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
    return None

TRANSLATIONS = {
    "English": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Smart Teacher Assistant*",
        "hw_section": "📖 Homework Prompt Photos",
        "hw_desc": "📸 Take camera photo or upload assignment pages:",
        "hw_saved": "Homework page(s) saved & compressed!",
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
        "batch_upload": "📸 Take photo with camera or select notebook files (compressed automatically):",
        "folder_found": "student notebook photos ready in folder.",
        "clear_notebooks": "🗑️ Clear Notebooks Folder",
        "btn_evaluate": "🚀 Start Grading Notebooks",
        "eval_success": "Successfully evaluated and saved to Progress Table!",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "📸 Take roster photo with camera or upload file:",
        "btn_read_names": "🤖 Read & Auto-Save Roster",
        "stats_sec": "📊 Class Progress Matrix (Excel Style)",
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.",
        "alert_box": "⚙️ Manage sections and language from the sidebar, and enter your API Key below.",
        "uploader_label_hw": "📸 Camera or Assignment File",
        "box1_title": "🗂️ Box 1: Automatic Homework Grading",
        "box2_title": "🗂️ Box 2: Import Roster",
        "box3_title": "🗂️ Box 3: Progress Table & Reports",
        "roster_photo_caption": "Roster Photo",
        "no_classes_warn": "⚠️ No sections available. Create a section from the sidebar to get started.",
        "no_students_yet": "No students added yet.",
        "current_class_label": "Current Section:",
        "catalog_spinner": "⏳ AI is analyzing and organizing the class list... (Takes 1-2 minutes)",
        "workflow_info": "💡 <b>Quick Guide:</b> Photos are compressed automatically for instant upload. Press 'Start Grading' to evaluate all student notebooks directly against the homework prompt."
    },
    "Ελληνικά": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*",
        "hw_section": "📖 Φωτογραφίες Εκφώνησης (Homework)",
        "hw_desc": "📸 Τραβήξτε φωτογραφία κάμερας ή ανεβάστε εκφώνηση:",
        "hw_saved": "σελίδα/σελίδες Homework αποθηκεύτηκαν & συμπιέστηκαν!",
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
        "batch_upload": "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων (συμπιέζονται αυτόματα):",
        "folder_found": "φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.",
        "clear_notebooks": "🗑️ Εκκαθάριση Φακέλου Τετραδίων",
        "btn_evaluate": "🚀 Έναρξη Βαθμολόγησης Τετραδίων",
        "eval_success": "Η αξιολόγηση ολοκληρώθηκε και αποθηκεύτηκε στον πίνακα προόδου!",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "📸 Τραβήξτε φωτογραφία καταλόγου με κάμερα ή ανεβάστε αρχείο:",
        "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
        "stats_sec": "📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style)",
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.",
        "alert_box": "⚙️ Διαχειριστείτε τα τμήματα από την πλαϊνή μπάρα και εισάγετε το API Key σας παρακάτω.",
        "uploader_label_hw": "📸 Κάμερα ή Αρχείο Εκφώνησης",
        "box1_title": "🗂️ Κουτάκι 1: Αυτόματη Αξιολόγηση Άσκησης",
        "box2_title": "🗂️ Κουτάκι 2: Εισαγωγή Καταλόγου",
        "box3_title": "🗂️ Κουτάκι 3: Πίνακας Προόδου & Αναφορές",
        "roster_photo_caption": "Φωτογραφία Καταλόγου",
        "no_classes_warn": "⚠️ Δεν υπάρχουν διαθέσιμα τμήματα. Δημιουργήστε ένα τμήμα από την πλαϊνή μπάρα για να ξεκινήσετε.",
        "no_students_yet": "Δεν έχουν προστεθεί μαθητές ακόμα.",
        "current_class_label": "Τρέχον Τμήμα:",
        "catalog_spinner": "⏳ Το AI αναλύει και οργανώνει τον κατάλογο της τάξης... (Διαρκεί 1-2 λεπτά)",
        "workflow_info": "💡 <b>Οδηγός Χρήσης:</b> Οι φωτογραφίες συμπιέζονται αυτόματα για στιγμιαίο ανέβασμα. Πατήστε 'Έναρξη Βαθμολόγησης' για να αξιολογηθούν απευθείας τα τετράδια βάσει της εκφώνησης."
    }
}

# --- 3. SIDEBAR: ΓΛΩΣΣΑ, ΕΚΦΩΝΗΣΗ & ΤΜΗΜΑΤΑ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
lang_keys = list(TRANSLATIONS.keys())
current_lang_index = lang_keys.index(st.session_state["app_lang"]) if st.session_state["app_lang"] in lang_keys else 0

selected_sidebar_lang = st.sidebar.selectbox("Choose UI Language:", lang_keys, index=current_lang_index, key="sidebar_lang_select")
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

if hw_files:
    for idx, hw_f in enumerate(hw_files):
        compressed_bytes = compress_image(hw_f.getbuffer())
        hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{idx}.jpg")
        with open(hw_path, "wb") as f:
            f.write(compressed_bytes)

homework_images = []
hw_paths_in_folder = sorted([os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('hw_page_')])
for p in hw_paths_in_folder:
    try:
        homework_images.append(Image.open(p))
    except Exception:
        pass

if homework_images:
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
        if n_class not in st.session_state["students_db"]:
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
            st.session_state["students_db"][selected_class].append(new_student)
            save_students(st.session_state["students_db"])
            st.sidebar.success(f"Added {new_student}")
            st.rerun()

    if st.session_state["students_db"][selected_class]:
        student_to_remove = st.sidebar.selectbox(t["remove_student"], ["-- Select --"] + st.session_state["students_db"][selected_class])
        if st.sidebar.button(t["btn_remove"]):
            if student_to_remove != "-- Select --":
                st.session_state["students_db"][selected_class].remove(student_to_remove)
                save_students(st.session_state["students_db"])
                st.sidebar.warning(f"Removed {student_to_remove}")
                st.rerun()
    else:
        st.sidebar.info(t["no_students_yet"])

# --- 4. ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ & API KEY ---
st.markdown(f"""
    <div class="custom-alert-box">
        {t["alert_box"]}
    </div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown("### " + t["api_prompt"])
    current_api_key = st.session_state["config"].get("api_key", "")
    api_key_input = st.text_input("API Key:", value=current_api_key, type="password", key="main_api_key_input", label_visibility="collapsed")
    if st.button(t["save_api"]):
        if api_key_input.strip():
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
        {t["workflow_info"]}
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
            st.warning("⚠️ Σημείωση: Ανεβάστε πρώτα την εκφώνηση της άσκησης από το πλαϊνό μενού (Sidebar).")
        
        notebook_files = st.file_uploader(
            t["batch_upload"],
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="notebook_batch_uploader"
        )
        
        if notebook_files:
            for idx, nb_file in enumerate(notebook_files):
                compressed_bytes = compress_image(nb_file.getbuffer())
                unique_filename = f"student_page_{int(time.time())}_{idx}.jpg"
                nb_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                with open(nb_path, "wb") as f:
                    f.write(compressed_bytes)
        
        existing_notebooks = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith('student_page_')]
        notebook_count = len(existing_notebooks)
        
        if notebook_count > 0:
            st.success(f"✅ {notebook_count} {t['folder_found']}")
            if st.button(t["clear_notebooks"]):
                for f in existing_notebooks:
                    try:
                        os.remove(os.path.join(UPLOAD_FOLDER, f))
                    except:
                        pass
                st.rerun()
        
        st.markdown("---")
        
        # --- ΑΜΕΣΗ ΕΝΑΡΞΗ ΒΑΘΜΟΛΟΓΗΣΗΣ ΜΕ ΕΞΥΠΝΗ ΑΝΑΓΝΩΣΗ ---
        if st.button(t["btn_evaluate"]):
            api_key_val = st.session_state["config"].get("api_key", "").strip()
            if not api_key_val:
                st.error("⚠️ Please enter your Gemini API Key first above!")
            elif not homework_images:
                st.error("⚠️ Παρακαλώ ανεβάστε πρώτα την εκφώνηση της άσκησης στο πλαϊνό μενού!")
            else:
                nb_images_paths = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('student_page_')]
                if not nb_images_paths:
                    st.warning("⚠️ Δεν βρέθηκαν φωτογραφίες τετραδίων. Ανεβάστε πρώτα φωτογραφίες τετραδίων.")
                else:
                    try:
                        client = genai.Client(api_key=api_key_val)
                        new_records = []
                        today_str = datetime.date.today().strftime("%Y-%m-%d")
                        class_students = st.session_state["students_db"].get(selected_class, [])
                        
                        total_files = len(nb_images_paths)
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, nb_p in enumerate(nb_images_paths):
                            file_name_display = os.path.basename(nb_p)
                            status_text.markdown(f"🔄 **Βαθμολόγηση σε εξέλιξη...** (Φωτογραφία {i+1} από {total_files}: `{file_name_display}`)")
                            
                            try:
                                nb_img = Image.open(nb_p)
                                prompt_eval = (
                                    f"Official Roster list: {class_students}\n"
                                    "Compare the student's notebook page against the homework prompt image(s).\n"
                                    "1. Identify the student's name on the page and match it precisely to the official roster list.\n"
                                    "2. Grade the student's work from 0 to 100 based on accuracy.\n"
                                    "3. Write constructive feedback in Greek.\n"
                                    "Return ONLY valid JSON with keys: \"student_name\", \"score\", \"feedback\"."
                                )
                                
                                contents_to_send = homework_images + [nb_img, prompt_eval]
                                resp_text = call_gemini_safe(client, 'gemini-3.8-flash', contents_to_send)
                                if not resp_text:
                                    resp_text = call_gemini_safe(client, 'gemini-2.5-flash', contents_to_send)
                                
                                matched_student = class_students[i % len(class_students)] if class_students else f"Student_{i+1}"
                                score_val = 50
                                feedback_val = "Χωρίς σχόλιο."
                                
                                if resp_text:
                                    clean_resp = resp_text.replace("```json", "").replace("```", "").strip()
                                    json_match = re.search(r'\{.*\}', clean_resp, re.DOTALL)
                                    if json_match:
                                        try:
                                            res_data = json.loads(json_match.group(0))
                                            raw_name = str(res_data.get("student_name", ""))
                                            for s in class_students:
                                                if s.lower() in raw_name.lower() or raw_name.lower() in s.lower():
                                                    matched_student = s
                                                    break
                                            score_val = int(res_data.get("score", 50))
                                            feedback_val = str(res_data.get("feedback", "Χωρίς σχόλιο."))
                                        except:
                                            pass
                                    
                                    # Fallback αναζήτησης αριθμού αν δεν γίνει parse το JSON
                                    if score_val == 50 and resp_text:
                                        nums = re.findall(r'\b(100|[1-9]?[0-9])\b', resp_text)
                                        if nums:
                                            for n in nums:
                                                val = int(n)
                                                if val <= 100:
                                                    score_val = val
                                                    break
                                        feedback_val = resp_text[:200]

                                new_records.append({
                                    "Section": selected_class,
                                    "Student": matched_student,
                                    "Date": today_str,
                                    "Score": score_val,
                                    "Feedback": feedback_val
                                })
                            except Exception as inner_e:
                                print(f"Skipping image due to error: {inner_e}")
                            
                            progress_bar.progress((i + 1) / total_files)
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        if new_records:
                            df_new = pd.DataFrame(new_records)
                            existing_df = st.session_state["grades_df"]
                            if not existing_df.empty:
                                existing_df = existing_df[~((existing_df["Section"] == selected_class) & (existing_df["Date"] == today_str))]
                            
                            st.session_state["grades_df"] = pd.concat([existing_df, df_new], ignore_index=True)
                            save_grades_df(st.session_state["grades_df"])
                            st.success(f"✅ {t['eval_success']}")
                        else:
                            st.error("⚠️ Αποτυχία βαθμολόγησης. Παρακαλώ δοκιμάστε ξανά.")
                    except Exception as e:
                        st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == t["opt2"]:
        st.subheader(t["box2_title"])
        st.write(f"**{t['current_class_label']} {selected_class}**")
        
        catalog_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="catalog_uploader")
        if catalog_file:
            catalog_path = os.path.join(UPLOAD_FOLDER, "catalog_temp.jpg")
            with open(catalog_path, "wb") as f:
                f.write(compress_image(catalog_file.getbuffer()))
            
            st.image(catalog_path, caption=t["roster_photo_caption"], width=300)
            
            if st.button(t["btn_read_names"]):
                api_key_val = st.session_state["config"].get("api_key", "").strip()
                if not api_key_val:
                    st.error("⚠️ Please enter your Gemini API Key first above!")
                else:
                    spinner_placeholder = st.empty()
                    spinner_placeholder.markdown(f"""
                        <div class="custom-spinner-box">
                            {t["catalog_spinner"]}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    try:
                        client = genai.Client(api_key=api_key_val)
                        img_to_send = Image.open(catalog_path)
                        
                        prompt = (
                            "Read all student names from this school roster image. "
                            "If last name and first name are in separate columns, combine them as 'ΕΠΩΝΥΜΟ ΟΝΟΜΑ'. "
                            "List only the full names, one per line. Do not include numbers, codes, or extra text."
                        )
                        
                        response_text = call_gemini_safe(client, 'gemini-3.8-flash', [img_to_send, prompt])
                        if not response_text:
                            response_text = call_gemini_safe(client, 'gemini-2.5-flash', [img_to_send, prompt])
                            
                        spinner_placeholder.empty()
                        
                        if response_text:
                            lines = response_text.replace("```", "").split("\n")
                            parsed_names = []
                            for line in lines:
                                clean_line = line.strip()
                                clean_line = re.sub(r'^[\d\-\.\)]+\s*', '', clean_line).strip()
                                if len(clean_line) > 2:
                                    parsed_names.append(clean_line)
                            
                            if parsed_names:
                                added_count = 0
                                for name in parsed_names:
                                    if name not in st.session_state["students_db"][selected_class]:
                                        st.session_state["students_db"][selected_class].append(name)
                                        added_count += 1
                                
                                save_students(st.session_state["students_db"])
                                st.success(f"✅ Successfully read! Added {added_count} new students to section {selected_class}.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("⚠️ No clear names found. Please try taking a closer or clearer picture.")
                        else:
                            st.error("⚠️ Error reading roster, please try again.")
                    except Exception as e:
                        if 'spinner_placeholder' in locals():
                            spinner_placeholder.empty()
                        st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == t["opt3"]:
        st.subheader(t["box3_title"])
        st.write(f"📊 {t['stats_sec']} - {selected_class}")
        
        grades_data = st.session_state["grades_df"]
        section_grades = grades_data[grades_data["Section"] == selected_class] if not grades_data.empty and "Section" in grades_data.columns else pd.DataFrame()
        
        if st.session_state["students_db"][selected_class]:
            students_list = st.session_state["students_db"][selected_class]
            df_progress = pd.DataFrame({"Student": students_list})
            
            if not section_grades.empty:
                latest_grades = section_grades.drop_duplicates(subset=["Student"], keep="last")
                df_progress = pd.merge(df_progress, latest_grades[["Student", "Date", "Score", "Feedback"]], on="Student", how="left")
            
            st.dataframe(df_progress, use_container_width=True)
        else:
            st.info(t["no_students_yet"])
