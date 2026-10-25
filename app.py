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

# Custom CSS για τα κόκκινα κουτάκια
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
            margin-bottom: 20px;
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
    </style>
""", unsafe_allow_html=True)

# Φάκελοι & Αρχεία
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
    return {"Α1": [], "Α2": [], "Β1": [], "Β2": [], "Γ1": [], "Γ2": []}

def save_students(students_dict):
    try:
        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(students_dict, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def clear_upload_folder():
    """Διαγράφει τις προσωρινές φωτογραφίες τετραδίων κρατώντας τα homework prompts."""
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

# --- 2. ΛΕΞΙΚΟ ΠΟΛΛΑΠΛΩΝ ΓΛΩΣΣΩΝ ---
TRANSLATIONS = {
    "Ελληνικά": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*",
        "hw_section": "📖 Φωτογραφίες Εκφώνησης (Homework)",
        "hw_desc": "📸 Τραβήξτε/Ανεβάστε τις σελίδες της εκφώνησης (Υψηλή Ανάλυση):",
        "hw_saved": "σελίδα/σελίδες Homework αποθηκεύτηκαν!",
        "class_mgmt": "⚙️ Διαχείριση Τάξης & Τμημάτων",
        "select_class": "Επιλογή Τμήματος:",
        "add_new_class": "➕ Δημιουργία Νέου Τμήματος (π.χ. Β3):",
        "btn_add_class": "Προσθήκη Τμήματος",
        "students_in": "Μαθητές Τμήματος",
        "add_student": "Προσθήκη νέου μαθητή:",
        "btn_add": "➕ Προσθήκη Μαθητή",
        "remove_student": "Αφαίρεση μαθητή:",
        "btn_remove": "❌ Διαγραφή Μαθητή",
        "api_prompt": "Εισάγετε Google Gemini API Key",
        "save_api": "💾 Αποθήκευση API Key",
        "api_saved_success": "Το API Key αποθηκεύτηκε επιτυχώς!",
        "tab1": "📷 Αυτόματη Αξιολόγηση Άσκησης",
        "tab2": "📋 Εισαγωγή Καταλόγου",
        "tab3": "📊 Πίνακας Προόδου & Αναφορές",
        "notebook_sec": "✨ Φωτογράφηση & Μεταφόρτωση Τετραδίων Μαθητών",
        "no_hw_warn": "⚠️ Σημείωση: Δεν έχετε τραβήξει φωτογραφία Homework από την αριστερή στήλη.",
        "batch_upload": "📸 Επιλέξτε ή Τραβήξτε φωτογραφίες τετραδίων (πολλαπλές επιλογές):",
        "folder_found": "φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.",
        "btn_evaluate": "🚀 Έναρξη Αξιολόγησης (Γρήγορη Λειτουργία)",
        "eval_success": "Αποθηκεύτηκαν επιτυχώς στον πίνακα προόδου!",
        "view_eval": "🔍 Προβολή Τελευταίας Αξιολόγησης",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "Ανεβάστε φωτογραφία καταλόγου (λίστα ονομάτων)",
        "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
        "stats_sec": "📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style)",
        "btn_close_day": "🚨 Καταγραφή Απουσιών/Ελλείψεων για Σήμερα",
        "manual_delete": "🗑️ Διαγραφή Δεδομένων"
    },
    "English": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Smart Teacher Assistant*",
        "hw_section": "📖 Homework Prompt Photos",
        "hw_desc": "📸 Take/Upload assignment prompt pages (High-Res):",
        "hw_saved": "Homework page(s) saved!",
        "class_mgmt": "⚙️ Class Management & Sections",
        "select_class": "Select Class/Section:",
        "add_new_class": "➕ Add New Section (e.g. B3):",
        "btn_add_class": "Add Section",
        "students_in": "Students in Section",
        "add_student": "Add new student:",
        "btn_add": "➕ Add Student",
        "remove_student": "Remove student:",
        "btn_remove": "❌ Delete Student",
        "api_prompt": "Enter Google Gemini API Key",
        "save_api": "💾 Save API Key",
        "api_saved_success": "API Key saved successfully!",
        "tab1": "📷 Automatic Grading",
        "tab2": "📋 Import Roster",
        "tab3": "📊 Progress Table & Reports",
        "notebook_sec": "✨ Capture & Upload Student Notebooks",
        "no_hw_warn": "⚠️ Note: You have not taken a Homework prompt photo from the left sidebar.",
        "batch_upload": "📸 Select or Take notebook photos (multiple allowed):",
        "folder_found": "student notebook photos ready in folder.",
        "btn_evaluate": "🚀 Start Grading (Fast Mode)",
        "eval_success": "Successfully saved to Progress Table!",
        "view_eval": "🔍 View Latest Evaluation",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "Upload roster photo (list of names)",
        "btn_read_names": "🤖 Read & Auto-Save Roster",
        "stats_sec": "📊 Class Progress Matrix (Excel Style)",
        "btn_close_day": "🚨 Mark Missing Homework for Today",
        "manual_delete": "🗑️ Delete Records"
    }
}

# --- 3. SIDEBAR: ΔΙΑΧΕΙΡΙΣΗ ΤΜΗΜΑΤΩΝ & ΜΑΘΗΤΩΝ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
app_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=0)
t = TRANSLATIONS.get(app_lang, TRANSLATIONS["Ελληνικά"])

st.markdown(t["title"])
st.markdown(t["subtitle"])

st.sidebar.markdown("---")
st.sidebar.header(t["hw_section"])
st.sidebar.write(t["hw_desc"])

hw_files = st.sidebar.file_uploader(
    "📸 Φωτογραφίστε ή επιλέξτε σελίδες εκφώνησης:",
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
        homework_images.append(Image.open(hw_path))
    st.sidebar.success(f"✅ {len(homework_images)} {t['hw_saved']}")

st.sidebar.markdown("---")
st.sidebar.header(t["class_mgmt"])

new_class_input = st.sidebar.text_input(t["add_new_class"])
if st.sidebar.button(t["btn_add_class"]):
    n_class = new_class_input.strip().upper()
    if n_class and n_class not in students_db:
        students_db[n_class] = []
        save_students(students_db)
        st.sidebar.success(f"Δημιουργήθηκε το τμήμα: {n_class}")
        st.rerun()

selected_class = st.sidebar.selectbox(t["select_class"], list(students_db.keys()))

st.sidebar.subheader(f"{t['students_in']} {selected_class}")
new_student = st.sidebar.text_input(t["add_student"])
if st.sidebar.button(t["btn_add"]):
    if new_student and new_student not in students_db[selected_class]:
        students_db[selected_class].append(new_student)
        students_db[selected_class].sort()
        save_students(students_db)
        st.sidebar.success(f"Added: {new_student}")
        st.rerun()

student_to_remove = st.sidebar.selectbox(t["remove_student"], ["-- Select --"] + students_db[selected_class])
if st.sidebar.button(t["btn_remove"]):
    if student_to_remove != "-- Select --":
        students_db[selected_class].remove(student_to_remove)
        save_students(students_db)
        st.sidebar.warning(f"Removed: {student_to_remove}")
        st.rerun()

# --- 4. API KEY & MAIN APP ---
saved_api_key = config_data.get("api_key", "")
col_api1, col_api2 = st.columns([3, 1])

with col_api1:
    api_key_input = st.text_input(t["api_prompt"], value=saved_api_key, type="password")

with col_api2:
    st.write("")
    st.write("")
    if st.button(t["save_api"]):
        if api_key_input.strip():
            config_data["api_key"] = api_key_input.strip()
            save_config(config_data)
            st.success(t["api_saved_success"])
            st.rerun()

active_api_key = config_data.get("api_key", "") or api_key_input

if active_api_key:
    try:
        client = genai.Client(api_key=active_api_key)
        
        # Κόκκινο κουτί με ξεχωριστό κόκκινο κουτάκι για τα βελάκια
        st.markdown('''
            <div class="custom-alert-box">
                ⚙️ Πατήστε τα βελάκια <span class="red-badge">&gt;&gt;</span> πάνω αριστερά για Τμήματα &amp; Γλώσσα
            </div>
        ''', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs([t["tab1"], t["tab2"], t["tab3"]])

        # TAB 1: ΑΥΤΟΜΑΤΗ ΑΞΙΟΛΟΓΗΣΗ ΜΕ WAKE LOCK
        with tab1:
            st.subheader(t["notebook_sec"])
            
            if not homework_images:
                st.warning(t["no_hw_warn"])

            up_files = st.file_uploader(
                t["batch_upload"], 
                type=["png", "jpg", "jpeg"], 
                accept_multiple_files=True, 
                key="notebook_batch_up"
            )
            
            if up_files:
                current_signature = tuple((f.name, f.size) for f in up_files)
                if st.session_state.get("last_uploaded_sig") != current_signature:
                    clear_upload_folder()
                    for idx, uf in enumerate(up_files):
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        file_path = os.path.join(UPLOAD_FOLDER, f"student_notebook_{timestamp}_{idx}.jpg")
                        with open(file_path, "wb") as f:
                            f.write(uf.getbuffer())
                    st.session_state["last_uploaded_sig"] = current_signature
                    st.rerun()

            folder_files = [
                os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) 
                if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('hw_page_')
            ]

            if folder_files:
                st.markdown("---")
                st.write(f"📊 **{len(folder_files)} {t['folder_found']}**")
                
                with st.expander("👁️ Προβολή φωτογραφιών στον φάκελο"):
                    cols = st.columns(3)
                    for idx, f_path in enumerate(folder_files):
                        with cols[idx % 3]:
                            st.image(f_path, caption=f"Φωτογραφία {idx+1}", use_column_width=True)
                
                col_btn1, col_btn2 = st.columns([2, 1])
                with col_btn1:
                    run_eval = st.button(t["btn_evaluate"], type="primary")
                with col_btn2:
                    if st.button("🗑️ Εκκαθάριση Φακέλου"):
                        clear_upload_folder()
                        if "last_uploaded_sig" in st.session_state:
                            del st.session_state["last_uploaded_sig"]
                        st.rerun()

                if run_eval:
                    wake_lock_code = """
                    <script>
                    let wakeLock = null;
                    async function requestWakeLock() {
                        try {
                            if ('wakeLock' in navigator) {
                                wakeLock = await navigator.wakeLock.request('screen');
                                console.log('Screen Wake Lock active!');
                            }
                        } catch (err) {
                            console.error(`${err.name}, ${err.message}`);
                        }
                    }
                    requestWakeLock();
                    </script>
                    """
                    components.html(wake_lock_code, height=0)
                    
                    st.info("💡 **Σημείωση:** Η οθόνη του κινητού σου κρατιέται ενεργή αυτόματα. Παρακαλώ περίμενε μερικά δευτερόλεπτα...")
                    
                    BATCH_SIZE = 15
                    folder_files_batches = [
                        folder_files[i:i + BATCH_SIZE] 
                        for i in range(0, len(folder_files), BATCH_SIZE)
                    ]
                    
                    all_eval_responses = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_batches = len(folder_files_batches)
                    
                    for b_idx, batch_paths in enumerate(folder_files_batches):
                        status_text.text(f"⏳ Γρήγορη επεξεργασία ομάδας {b_idx + 1} από {total_batches}...")
                        batch_images = [Image.open(f_path) for f_path in batch_paths]
                        
                        known_students_str = ", ".join(students_db[selected_class])
                        prompt = f"""
                        You are an expert teacher grading student exercises.
                        I attached high-resolution images of student notebook pages.
                        Evaluate EACH student found in these images individually.

                        1. **MULTI-PAGE HANDLING**: If a student's work spans across multiple pages/images, combine all their pages together and output a SINGLE unified score and evaluation for that student. Do not create separate entries for the same student.
                        2. **DETECT STUDENT WORK LANGUAGE**: Automatically detect the language used by the student.
                        3. **MATCH FEEDBACK LANGUAGE**: Write all analysis/notes EXCLUSIVELY in that same language.
                        4. **SCORE FORMAT**: Provide the score strictly as a percentage (e.g., 85% or 0% if completely wrong).

                        For EACH student, structure your response strictly as:

                        ### Μαθητής:
                        Όνομα: [Student Name]
                        Ποσοστό: [X%]
                        Ανάλυση: [Detailed evaluation text]

                        Enrolled students in section {selected_class}: [{known_students_str}].
                        Match the detected names with this roster.
                        """

                        contents_list = [prompt] + batch_images
                        if homework_images:
                            contents_list += homework_images

                        try:
                            eval_res = call_gemini_with_retry(client, 'gemini-3.8-flash', contents_list)
                            if eval_res:
                                all_eval_responses.append(eval_res)
                        except Exception:
                            pass
                        
                        progress_bar.progress((b_idx + 1) / total_batches)

                    status_text.empty()
                    progress_bar.empty()

                    if not all_eval_responses:
                        st.error("⚠️ Προέκυψε προσωρινό πρόβλημα σύνδεσης. Παρακαλώ δοκιμάστε ξανά.")
                        st.stop()

                    full_eval_res = "\n\n".join(all_eval_responses)
                    
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    student_blocks = re.split(r'###\s*Μαθητής\s*:?|Μαθητής\s+\d+:', full_eval_res)
                    
                    new_rows = []
                    for block in student_blocks:
                        if not block.strip():
                            continue
                        
                        d_name = "Άγνωστος"
                        d_score = "0%"
                        
                        for line in block.split('\n'):
                            line_str = line.strip()
                            if line_str.startswith("Όνομα:"):
                                d_name = line_str.replace("Όνομα:", "").strip()
                            elif line_str.startswith("Ποσοστό:"):
                                d_score = line_str.replace("Ποσοστό:", "").strip()
                        
                        d_name = d_name.replace("**", "").replace("*", "").strip().replace("/", "-")
                        d_score = d_score.replace("**", "").replace("*", "").strip()

                        if d_name != "Άγνωστος":
                            new_rows.append({
                                "Ημερομηνία": today,
                                "Τμήμα": selected_class,
                                "Μαθητής": d_name,
                                "Ποσοστό": d_score,
                                "Κατάσταση": "Ελέγχθηκε",
                                "Αξιολόγηση": block.strip()
                            })

                    if new_rows:
                        df_new = pd.DataFrame(new_rows)
                        if os.path.exists(GRADES_FILE):
                            df_ex = pd.read_csv(GRADES_FILE)
                            df_ex = df_ex[~((df_ex["Ημερομηνία"] == today) & (df_ex["Τμήμα"] == selected_class) & (df_ex["Μαθητής"].isin([r["Μαθητής"] for r in new_rows])))]
                            df_updated = pd.concat([df_ex, df_new], ignore_index=True)
                        else:
                            df_updated = df_new
                        
                        df_updated.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                        clear_upload_folder()
                        if "last_uploaded_sig" in st.session_state:
                            del st.session_state["last_uploaded_sig"]
                        st.success(f"🎉 {len(new_rows)} {t['eval_success']}")

                    st.session_state["current_eval"] = full_eval_res
                    st.rerun()

            if "current_eval" in st.session_state:
                with st.expander(t["view_eval"], expanded=True):
                    st.markdown(st.session_state["current_eval"])

        # TAB 2: ΕΙΣΑΓΩΓΗ ΚΑΤΑΛΟΓΟΥ
        with tab2:
            st.subheader(f"{t['catalog_sec']} – {selected_class}")
            
            list_img_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="list_up")
            if list_img_file:
                list_path = os.path.join(UPLOAD_FOLDER, list_img_file.name)
                with open(list_path, "wb") as f:
                    f.write(list_img_file.getbuffer())
                list_img = Image.open(list_path)
                
                st.image(list_img, caption="Φωτογραφία Καταλόγου", use_column_width=True)
                
                if st.button(t["btn_read_names"], type="primary"):
                    with st.spinner("🤖 Η AI διαβάζει τα ονόματα και τα αποθηκεύει μόνιμα στο τμήμα..."):
                        p_list = "Read all student names from this roster photo carefully. Return ONLY a comma-separated list of the full names (e.g. Γιώργος Παπαδόπουλος, Μαρία Ιωάννου). Do not add any extra text or numbers."
                        
                        try:
                            raw_text_res = call_gemini_with_retry(client, 'gemini-3.8-flash', [p_list, list_img])
                            raw_text = raw_text_res.strip() if raw_text_res else ""
                        except Exception:
                            raw_text = ""
                        
                        if not raw_text:
                            st.error("⚠️ Προέκυψε στιγμιαίο πρόβλημα. Παρακαλώ δοκιμάστε ξανά.")
                            st.stop()
                        
                        names_found = [n.strip().replace("\n", "").replace("-", "") for n in raw_text.split(",") if n.strip()]
                        
                        added_count = 0
                        for n in names_found:
                            if n and n not in students_db[selected_class]:
                                students_db[selected_class].append(n)
                                added_count += 1
                        
                        students_db[selected_class].sort()
                        save_students(students_db)
                        
                        st.success(f"🎉 Διαβάστηκαν και αποθηκεύτηκαν επιτυχώς {added_count} νέα ονόματα στο τμήμα {selected_class}!")
                        st.write("📋 **Ονόματα που προστέθηκαν:**", names_found)
                        st.rerun()

        # TAB 3: ΠΙΝΑΚΑΣ ΠΡΟΟΔΟΥ & ΔΙΑΧΕΙΡΙΣΗ ΑΠΟΥΣΙΩΝ/ΕΛΛΕΙΨΕΩΝ
        with tab3:
            st.subheader(f"{t['stats_sec']} – {selected_class}")
            
            if st.button(t["btn_close_day"]):
                today = datetime.date.today().strftime("%Y-%m-%d")
                
                if os.path.exists(GRADES_FILE):
                    df_g = pd.read_csv(GRADES_FILE)
                else:
                    df_g = pd.DataFrame(columns=["Ημερομηνία", "Τμήμα", "Μαθητής", "Ποσοστό", "Κατάσταση", "Αξιολόγηση"])

                today_checked = df_g[(df_g["Ημερομηνία"] == today) & (df_g["Τμήμα"] == selected_class)]["Μαθητής"].tolist()
                
                missing_records = []
                for st_name in students_db[selected_class]:
                    if st_name not in today_checked:
                        missing_records.append({
                            "Ημερομηνία": today,
                            "Τμήμα": selected_class,
                            "Μαθητής": st_name,
                            "Ποσοστό": "Δεν έκανε ασκήσεις",
                            "Κατάσταση": "Ελλιπής",
                            "Αξιολόγηση": "No notebook submitted."
                        })
                
                if missing_records:
                    df_missing = pd.DataFrame(missing_records)
                    df_final = pd.concat([df_g, df_missing], ignore_index=True)
                    df_final.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                    st.success(f"Καταγράφηκαν οι απουσίες/ελλείψεις για όσους δεν είχαν τετράδιο σήμερα!")
                    st.rerun()
                else:
                    st.info("Όλοι οι μαθητές έχουν αξιολογηθεί για σήμερα!")

            if os.path.exists(GRADES_FILE):
                df_all = pd.read_csv(GRADES_FILE)
                df_class = df_all[df_all["Τμήμα"] == selected_class]
                
                if not df_class.empty:
                    pivot_df = df_class.pivot_table(
                        index="Μαθητής", 
                        columns="Ημερομηνία", 
                        values="Ποσοστό", 
                        aggfunc="first"
                    ).fillna("Δεν έκανε ασκήσεις")
                    
                    for st_name in students_db[selected_class]:
                        if st_name not in pivot_df.index:
                            pivot_df.loc[st_name] = "Δεν έκανε ασκήσεις"

                    st.markdown("### 📋 Πίνακας Βαθμολογίας & Πρόκρισης (Excel Format)")
                    st.dataframe(pivot_df, use_container_width=True)

                    st.markdown("---")
                    st.subheader("🗑️ Επιλογές Διαχείρισης & Διαγραφής")
                    
                    col_d1, col_d2 = st.columns(2)
                    
                    with col_d1:
                        available_dates = df_class["Ημερομηνία"].unique().tolist()
                        selected_date_to_delete = st.selectbox("Ημερομηνία για μαζική διαγραφή:", ["-- Επιλέξτε --"] + available_dates)
                        if st.button("🚨 Διαγραφή Ημέρας"):
                            if selected_date_to_delete != "-- Επιλέξτε --":
                                df_all = df_all[~((df_all["Ημερομηνία"] == selected_date_to_delete) & (df_all["Τμήμα"] == selected_class))]
                                df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                                st.success(f"Η ημερομηνία {selected_date_to_delete} διαγράφηκε επιτυχώς!")
                                st.rerun()

                    with col_d2:
                        options_to_delete = ["-- Επιλέξτε εγγραφή --"]
                        indices_map = {}
                        for idx, row in df_class.iterrows():
                            label = f"{row['Ημερομηνία']} | {row['Μαθητής']} | {row['Ποσοστό']}"
                            options_to_delete.append(label)
                            indices_map[label] = idx

                        selected_del = st.selectbox("Μεμονωμένη εγγραφή:", options_to_delete)
                        if st.button("🗑️ Διαγραφή Επιλεγμένου"):
                            if selected_del != "-- Επιλέξτε εγγραφή --":
                                target_idx = indices_map[selected_del]
                                df_all = df_all.drop(target_idx)
                                df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                                st.success("Η εγγραφή διαγράφηκε!")
                                st.rerun()
                else:
                    st.info(f"Δεν υπάρχουν καταγεγραμμένες βαθμολογίες για το τμήμα {selected_class} ακόμα. Ανεβάστε τετράδια στην 1η καρτέλα για να ξεκινήσετε!")
            else:
                st.info("Δεν βρέθηκε αρχείο βαθμολογιών.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.warning("Please enter and save your API Key to continue.")
