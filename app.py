import streamlit as st
from google import genai
from PIL import Image
import pandas as pd
import datetime
import os
import json
import re

# --- 1. ΔΙΑΜΟΡΦΩΣΗ ΣΕΛΙΔΑΣ & GRADEMIND AI ---
st.set_page_config(
    page_title="GradeMind AI – Smart Homework & Test Grader", 
    page_icon="🎓",
    layout="wide"
)

# Φάκελοι & Αρχεία
UPLOAD_FOLDER = "uploads_folder"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

STUDENTS_FILE = "students_db.json"
GRADES_FILE = "grades_db.csv"

def load_students():
    if os.path.exists(STUDENTS_FILE):
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"Α1": [], "Α2": [], "Β1": [], "Β2": [], "Γ1": [], "Γ2": []}

def save_students(students_dict):
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(students_dict, f, ensure_ascii=False, indent=4)

def clean_old_records():
    if os.path.exists(GRADES_FILE):
        try:
            df = pd.read_csv(GRADES_FILE)
            if not df.empty and "Ημερομηνία" in df.columns:
                df["Ημερομηνία_dt"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
                cutoff_date = pd.Timestamp(datetime.date.today() - datetime.timedelta(days=7))
                df_filtered = df[df["Ημερομηνία_dt"] >= cutoff_date].drop(columns=["Ημερομηνία_dt"])
                df_filtered.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
        except Exception:
            pass

def clear_upload_folder():
    """Διαγράφει όλες τις φωτογραφίες τετραδίων από τον φάκελο ώστε να είναι καθαρός για την επόμενη μέρα."""
    for f in os.listdir(UPLOAD_FOLDER):
        if not f.startswith('hw_page_'):
            file_path = os.path.join(UPLOAD_FOLDER, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception:
                pass

clean_old_records()
students_db = load_students()

# --- 2. ΛΕΞΙΚΟ ΠΟΛΛΑΠΛΩΝ ΓΛΩΣΣΩΝ ΓΙΑ ΤΟ ΠΕΡΙΒΑΛΛΟΝ (TRANSLATIONS) ---
TRANSLATIONS = {
    "Ελληνικά": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*",
        "hw_section": "📖 Φωτογραφίες Εκφώνησης (Homework)",
        "hw_desc": "Τραβήξτε τις σελίδες της εκφώνησης:",
        "hw_pages": "Σελίδες Homework:",
        "hw_cam": "📸 Homework - Σελίδα",
        "hw_saved": "σελίδα/σελίδες Homework αποθηκεύτηκαν",
        "class_mgmt": "⚙️ Διαχείριση Τάξης",
        "select_class": "Επιλογή Τμήματος:",
        "students_in": "Μαθητές Τμήματος",
        "add_student": "Προσθήκη νέου μαθητή:",
        "btn_add": "➕ Προσθήκη Μαθητή",
        "remove_student": "Αφαίρεση μαθητή:",
        "btn_remove": "❌ Διαγραφή Μαθητή",
        "api_prompt": "Εισάγετε Google Gemini API Key",
        "tab1": "📷 Αυτόματη Αξιολόγηση Άσκησης",
        "tab2": "📋 Εισαγωγή Καταλόγου",
        "tab3": "📊 Αναφορές & Απουσίες",
        "notebook_sec": "✨ Φωτογράφηση Τετραδίων Μαθητών",
        "no_hw_warn": "⚠️ Σημείωση: Δεν έχετε τραβήξει φωτογραφία Homework από την αριστερή στήλη.",
        "input_mode": "Τρόπος Εισαγωγής Τετραδίου Μαθητή:",
        "mode_cam": "📷 Live Κάμερα Browser",
        "mode_file": "📱 Πίσω Κάμερα Κινητού / Επιλογή Αρχείων (Συνιστάται για Κινητά)",
        "how_many_pages": "Πόσες σελίδες θέλετε να φωτογραφίσετε για το τετράδιο;",
        "page_label": "Σελίδα",
        "snap_page": "📷 Φωτογραφίστε τη Σελίδα",
        "page_saved": "αποθηκεύτηκε!",
        "batch_upload": "📱 Τραβήξτε φωτογραφίες με την Πίσω Κάμερα ή επιλέξτε από τη Συλλογή:",
        "batch_saved": "φωτογραφίες αποθηκεύτηκαν επιτυχώς!",
        "folder_found": "φωτογραφίες σελίδων μαθητών στον φάκελο.",
        "btn_evaluate": "🚀 Έναρξη Αξιολόγησης Ασκήσεων Φακέλου",
        "eval_spinner": "🤖 Η AI αναλύει τις σελίδες και προσαρμόζει τις οδηγίες...",
        "eval_success": "Αποθηκεύτηκαν επιτυχώς στις Αναφορές & ο φάκελος καθαρίστηκε!",
        "view_eval": "🔍 Προβολή Αναλυτικής Αξιολόγησης (Πρόοδος)",
        "catalog_sec": "📷 Εισαγωγή Καταλόγου για το Τμήμα",
        "upload_catalog": "Ανεβάστε φωτογραφία καταλόγου",
        "btn_read_names": "🤖 Ανάγνωση Ονομάτων από AI",
        "btn_save_names": "📥 Αποθήκευση Ονομάτων στο Τμήμα",
        "stats_sec": "📊 Στατιστικά Τμήματος (Πίνακας Excel ανά Ημερομηνία)",
        "stats_info": "ℹ️ *Οι εγγραφές διαγράφονται αυτόματα μετά από 7 ημέρες.*",
        "btn_close_day": "🚨 Κλείσιμο Ημέρας & Σημείωση Όσων ΔΕΝ Έκαναν Ασκήσεις",
        "manual_delete": "🗑️ Χειροκίνητη Διαγραφή Εγγραφής"
    },
    "English": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – Smart Teacher Assistant*",
        "hw_section": "📖 Homework Prompt Photos",
        "hw_desc": "Take photos of the assignment pages:",
        "hw_pages": "Homework Pages:",
        "hw_cam": "📸 Homework - Page",
        "hw_saved": "Homework page(s) saved",
        "class_mgmt": "⚙️ Class Management",
        "select_class": "Select Class/Section:",
        "students_in": "Students in Section",
        "add_student": "Add new student:",
        "btn_add": "➕ Add Student",
        "remove_student": "Remove student:",
        "btn_remove": "❌ Delete Student",
        "api_prompt": "Enter Google Gemini API Key",
        "tab1": "📷 Automatic Grading",
        "tab2": "📋 Import Roster",
        "tab3": "📊 Reports & Attendance",
        "notebook_sec": "✨ Capture Student Notebooks",
        "no_hw_warn": "⚠️ Note: You have not taken a Homework prompt photo from the left sidebar.",
        "input_mode": "Student Notebook Input Method:",
        "mode_cam": "📷 Live Browser Camera",
        "mode_file": "📱 Mobile Back Camera / Gallery (Recommended for Phones)",
        "how_many_pages": "How many pages do you want to snap for this notebook?",
        "page_label": "Page",
        "snap_page": "📷 Snap Page",
        "page_saved": "saved!",
        "batch_upload": "📱 Snap photos using Back Camera or select from Gallery:",
        "batch_saved": "photos uploaded successfully!",
        "folder_found": "student notebook photos in folder.",
        "btn_evaluate": "🚀 Start Folder Grading Evaluation",
        "eval_spinner": "🤖 AI is analyzing pages and adapting feedback...",
        "eval_success": "Successfully saved to Reports & folder cleared!",
        "view_eval": "🔍 View Detailed Evaluation (Progress)",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "Upload roster photo",
        "btn_read_names": "🤖 Read Names with AI",
        "btn_save_names": "📥 Save Names to Section",
        "stats_sec": "📊 Class Statistics (Excel-style Table by Date)",
        "stats_info": "ℹ️ *Records are automatically deleted after 7 days.*",
        "btn_close_day": "🚨 Close Day & Mark Students Missing Homework",
        "manual_delete": "🗑️ Manual Record Deletion"
    }
}

# --- 3. SIDEBAR: ΕΠΙΛΟΓΗ ΓΛΩΣΣΑΣ & ΔΙΑΧΕΙΡΙΣΗ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
app_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=0)
t = TRANSLATIONS.get(app_lang, TRANSLATIONS["Ελληνικά"])

st.markdown(t["title"])
st.markdown(t["subtitle"])

st.sidebar.markdown("---")
st.sidebar.header(t["hw_section"])
st.sidebar.write(t["hw_desc"])

hw_pages_num = st.sidebar.number_input(t["hw_pages"], min_value=1, max_value=5, value=1, step=1)

homework_images = []
for h_idx in range(int(hw_pages_num)):
    try:
        hw_cam = st.sidebar.camera_input(f"{t['hw_cam']} {h_idx+1}", key=f"hw_cam_{h_idx}")
        if hw_cam:
            hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{h_idx}.jpg")
            with open(hw_path, "wb") as f:
                f.write(hw_cam.getbuffer())
            homework_images.append(Image.open(hw_path))
    except Exception:
        st.sidebar.warning("⚠️ Η live κάμερα δεν υποστηρίζεται. Ανεβάστε τη φωτογραφία εκφώνησης ως αρχείο.")

if homework_images:
    st.sidebar.success(f"✅ {len(homework_images)} {t['hw_saved']}")

st.sidebar.markdown("---")
st.sidebar.header(t["class_mgmt"])
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

# --- 4. ΚΥΡΙΩΣ ΜΕΡΟΣ ---
api_key = st.text_input(t["api_prompt"], type="password")

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        
        tab1, tab2, tab3 = st.tabs([t["tab1"], t["tab2"], t["tab3"]])

        # TAB 1: ΑΥΤΟΜΑΤΗ ΑΞΙΟΛΟΓΗΣΗ
        with tab1:
            st.subheader(t["notebook_sec"])
            
            if not homework_images:
                st.warning(t["no_hw_warn"])

            input_mode = st.radio(
                t["input_mode"], 
                [t["mode_file"], t["mode_cam"]], # Η επιλογή κινητού είναι πρώτη
                key="input_mode_radio"
            )

            if input_mode == t["mode_cam"]:
                num_pages = st.number_input(t["how_many_pages"], min_value=1, max_value=5, value=2, step=1)
                
                for p_idx in range(int(num_pages)):
                    st.write(f"**{t['page_label']} {p_idx+1}:**")
                    try:
                        cam_file = st.camera_input(f"{t['snap_page']} {p_idx+1}", key=f"student_cam_{p_idx}")
                        if cam_file:
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_path = os.path.join(UPLOAD_FOLDER, f"student_cam_p{p_idx+1}_{timestamp}.jpg")
                            with open(file_path, "wb") as f:
                                f.write(cam_file.getbuffer())
                            st.success(f"✅ {t['page_label']} {p_idx+1} {t['page_saved']}")
                    except Exception:
                        st.error("⚠️ Η live κάμερα του browser κόλλησε. Παρακαλώ επιλέξτε την επιλογή '📱 Πίσω Κάμερα Κινητού / Επιλογή Αρχείων' παραπάνω.")

            else:
                st.info("💡 **Συμβουλή για Κινητά:** Πατώντας το κουμπί παρακάτω, επιλέξτε **«Κάμερα»** στο κινητό σας. Έτσι θα ανοίξει η **πίσω κάμερα** της συσκευής σας χωρίς κανένα σφάλμα!")
                up_files = st.file_uploader(
                    t["batch_upload"], 
                    type=["png", "jpg", "jpeg"], 
                    accept_multiple_files=True, 
                    key="up_ex_multi"
                )
                if up_files:
                    for idx, uf in enumerate(up_files):
                        file_path = os.path.join(UPLOAD_FOLDER, f"student_batch_{idx}_{uf.name}")
                        with open(file_path, "wb") as f:
                            f.write(uf.getbuffer())
                    st.success(f"📂 {len(up_files)} {t['batch_saved']}")

            folder_files = [
                os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) 
                if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('hw_page_')
            ]

            if folder_files:
                st.markdown("---")
                st.write(f"📊 **{len(folder_files)} {t['folder_found']}**")
                
                if st.button(t["btn_evaluate"]):
                    student_images = [Image.open(f_path) for f_path in folder_files]
                    
                    with st.spinner(t["eval_spinner"]):
                        known_students_str = ", ".join(students_db[selected_class])
                        
                        prompt = f"""
                        You are an expert teacher grading student exercises.
                        I attached the images of the homework prompt and student notebook pages.
                        Evaluate EACH student individually.

                        1. **DETECT STUDENT WORK LANGUAGE**: Automatically detect the language used by the student in their exercise.
                        2. **MATCH FEEDBACK LANGUAGE**: Write all analysis, corrections, feedback, and notes EXCLUSIVELY in the EXACT SAME language used by the student.

                        For EACH student found in the images, structure your response as follows:

                        ### Μαθητής:
                        Όνομα: [Student Name]
                        Ποσοστό: [X%]
                        Ανάλυση: [Detailed evaluation text in the student's language]

                        Enrolled students in section {selected_class}: [{known_students_str}].
                        Match the detected names with this roster.
                        """

                        contents_list = [prompt] + student_images
                        if homework_images:
                            contents_list += homework_images

                        response = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=contents_list
                        )
                        
                        eval_res = response.text
                        today = datetime.date.today().strftime("%Y-%m-%d")

                        student_blocks = re.split(r'###\s*Μαθητής\s*:?|Μαθητής\s+\d+:', eval_res)
                        
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
                            
                            d_name = d_name.replace("**", "").replace("*", "").strip()
                            d_score = d_score.replace("**", "").replace("*", "").strip()

                            if d_name != "Άγνωστος" or d_score != "0%":
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
                                df_updated = pd.concat([df_ex, df_new], ignore_index=True)
                            else:
                                df_updated = df_new
                            
                            df_updated.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                            
                            # ΑΥΤΟΜΑΤΟΣ ΚΑΘΑΡΙΣΜΟΣ ΦΑΚΕΛΟΥ ΜΕΤΑ ΤΗ ΒΑΘΜΟΛΟΓΗΣΗ
                            clear_upload_folder()
                            st.success(f"🎉 {len(new_rows)} {t['eval_success']}")

                        st.session_state["current_eval"] = eval_res

            if "current_eval" in st.session_state:
                with st.expander(t["view_eval"], expanded=True):
                    st.markdown(st.session_state["current_eval"])

        # TAB 2: ΕΙΣΑΓΩΓΗ ΚΑΤΑΛΟΓΟΥ
        with tab2:
            st.subheader(f"{t['catalog_sec']} {selected_class}")
            
            list_img_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="list_up")
            if list_img_file:
                list_path = os.path.join(UPLOAD_FOLDER, list_img_file.name)
                with open(list_path, "wb") as f:
                    f.write(list_img_file.getbuffer())
                list_img = Image.open(list_path)
                
                st.image(list_img, caption="Roster Photo", use_column_width=True)
                
                if st.button(t["btn_read_names"]):
                    with st.spinner("AI Reading Roster..."):
                        p_list = "Read the student names carefully from the photo. Return them as a simple comma-separated list (e.g. Name1, Name2, Name3)."
                        res_list = client.models.generate_content(model='gemini-3.8-flash', contents=[p_list, list_img])
                        
                        names_found = [n.strip() for n in res_list.text.split(",") if n.strip()]
                        st.write("**Names Found:**", names_found)
                        
                        st.session_state["found_names_cache"] = names_found

            if "found_names_cache" in st.session_state and st.session_state["found_names_cache"]:
                if st.button(t["btn_save_names"]):
                    added_count = 0
                    for n in st.session_state["found_names_cache"]:
                        if n not in students_db[selected_class]:
                            students_db[selected_class].append(n)
                            added_count += 1
                    students_db[selected_class].sort()
                    save_students(students_db)
                    st.success(f"Added {added_count} new students to section {selected_class}!")
                    del st.session_state["found_names_cache"]
                    st.rerun()

        # TAB 3: ΑΝΑΦΟΡΕΣ, ΑΠΟΥΣΙΕΣ & ΔΙΑΓΡΑΦΗ (EXCEL FORMAT)
        with tab3:
            st.subheader(f"{t['stats_sec']} {selected_class}")
            st.caption(t["stats_info"])
            
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
                            "Ποσοστό": "-",
                            "Κατάσταση": "Δεν έκανε ασκήσεις",
                            "Αξιολόγηση": "No notebook submitted."
                        })
                
                if missing_records:
                    df_missing = pd.DataFrame(missing_records)
                    df_final = pd.concat([df_g, df_missing], ignore_index=True)
                    df_final.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                    st.warning(f"{len(missing_records)} students marked as missing homework for today.")
                    st.rerun()
                else:
                    st.success("All students graded!")

            if os.path.exists(GRADES_FILE):
                df_all = pd.read_csv(GRADES_FILE)
                df_class = df_all[df_all["Τμήμα"] == selected_class]
                
                if not df_class.empty:
                    st.markdown("### 📊 Πίνακας Excel - Πρόοδος Μαθητών ανά Ημερομηνία")
                    
                    pivot_df = df_class.pivot_table(
                        index="Μαθητής", 
                        columns="Ημερομηνία", 
                        values="Ποσοστό", 
                        aggfunc="first"
                    ).fillna("-")
                    
                    st.dataframe(pivot_df, use_container_width=True)

                    st.markdown("---")
                    st.markdown("📋 **Αναλυτικός Κατάλογος Εγγραφών**")
                    df_display = df_class[["Ημερομηνία", "Τμήμα", "Μαθητής", "Ποσοστό", "Κατάσταση"]]
                    st.dataframe(df_display, use_container_width=True)

                    st.markdown("---")
                    st.subheader(t["manual_delete"])
                    
                    options_to_delete = ["-- Select record to delete --"]
                    indices_map = {}
                    for idx, row in df_class.iterrows():
                        label = f"{row['Ημερομηνία']} | {row['Μαθητής']} | {row['Ποσοστό']} ({row['Κατάσταση']})"
                        options_to_delete.append(label)
                        indices_map[label] = idx

                    selected_del = st.selectbox("Select Record:", options_to_delete)
                    if st.button("🗑️ Delete"):
                        if selected_del != "-- Select record to delete --":
                            target_idx = indices_map[selected_del]
                            df_all = df_all.drop(target_idx)
                            df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                            st.success("Record deleted successfully!")
                            st.rerun()
                else:
                    st.info("No saved records for this section in the last 7 days.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.warning("Please enter your API Key.")
