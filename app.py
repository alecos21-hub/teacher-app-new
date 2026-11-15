import streamlit as st
import os
import json
import re
import time
from PIL import Image
import io
import pandas as pd

# --- ΑΥΤΟΜΑΤΟΣ ΕΛΕΓΧΟΣ ΚΑΙ ΕΓΚΑΤΑΣΤΑΣΗ ΒΙΒΛΙΟΘΗΚΩΝ ---
def check_and_install():
    required_packages = {
        "streamlit": "streamlit",
        "google.genai": "google-genai",
        "pandas": "pandas",
        "PIL": "Pillow"
    }
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            st.warning(f"⚠️ Η βιβλιοθήκη '{package_name}' δεν βρέθηκε. Αυτόματη εγκατάσταση σε εξέλιξη...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            st.success(f"Επιτυχής εγκατάσταση του {package_name}!")

# Εκτέλεση ελέγχου κατά την εκκίνηση
import sys
check_and_install()

from google import genai

# --- ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ ---
st.set_page_config(
    page_title="GradeMind AI - Ψηφιακός Βοηθός Εκπαιδευτικού",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Δημιουργία φακέλου αποθήκευσης προσωρινών αρχείων
UPLOAD_FOLDER = "temp_uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATA_FILE = "students_database.json"

def load_students():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_students(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Αρχικοποίηση Session State
if "students_db" not in st.session_state:
    st.session_state["students_db"] = load_students()

if "config" not in st.session_state:
    st.session_state["config"] = {"api_key": ""}

# Συναρτήσεις επεξεργασίας εικόνας
def compress_image(image_bytes, max_size=(1024, 1024), quality=85):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception as e:
        return image_bytes

# --- ΕΛΛΗΝΙΚΑ ΚΕΙΜΕΝΑ / UI ---
t = {
    "title": "🎓 GradeMind AI - Έξυπνη Αξιολόγηση Τετραδίων",
    "sidebar_title": "⚙️ Διαχείριση & Ρυθμίσεις",
    "api_label": "Gemini API Key:",
    "class_section": "🏫 Επιλογή / Δημιουργία Τμήματος",
    "new_class_label": "Όνομα νέου τμήματος (π.χ. Α1):",
    "add_class_btn": "➕ Προσθήκη Τμήματος",
    "select_class": "Επιλέξτε Τμήμα:",
    "opt1": "📝 1. Υποβοηθούμενη Αξιολόγηση",
    "opt2": "👥 2. Εισαγωγή Καταλόγου",
    "opt3": "📊 3. Προβολή / Εξαγωγή Βαθμών",
    "box2_title": "📂 Ανέβασμα Καταλόγου Μαθητών",
    "upload_catalog": "Ανεβάστε φωτογραφία του καταλόγου μαθητών του τμήματος:",
    "roster_photo_caption": "Κατάλογος Μαθητών",
    "btn_read_names": "🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου",
    "catalog_spinner": "Το Gemini αναλύει τον κατάλογο και εξαγάγει τα ονόματα...",
}

st.title(t["title"])

# --- SIDEBAR ---
with st.sidebar:
    st.header(t["sidebar_title"])
    
    # API Key Input
    api_key_input = st.text_input(t["api_label"], value=st.session_state["config"]["api_key"], type="password")
    if api_key_input:
        st.session_state["config"]["api_key"] = api_key_input
        
    st.divider()
    st.subheader(t["class_section"])
    
    # Δημιουργία νέου τμήματος
    new_class_name = st.text_input(t["new_class_label"], key="new_class_input")
    if st.button(t["add_class_btn"]):
        if new_class_name.strip():
            c_name = new_class_name.strip()
            if c_name not in st.session_state["students_db"]:
                st.session_state["students_db"][c_name] = []
                save_students(st.session_state["students_db"])
                st.success(f"Το τμήμα '{c_name}' προστέθηκε!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Το τμήμα υπάρχει ήδη.")
        else:
            st.error("Εισάγετε έγκυρο όνομα τμήματος.")

    # Λίστα διαθέσιμων τμημάτων
    existing_classes = list(st.session_state["students_db"].keys())
    if existing_classes:
        selected_class = st.selectbox(t["select_class"], existing_classes)
    else:
        selected_class = None
        st.info("Δεν υπάρχουν τμήματα. Δημιουργήστε ένα από πάνω.")

    st.divider()
    mode = st.radio("Πλοήγηση:", [t["opt1"], t["opt2"], t["opt3"]])

# --- ΚΥΡΙΩΣ ΛΕΙΤΟΥΡΓΙΑ ---
if not selected_class:
    st.warning("⚠️ Παρακαλώ δημιουργήστε και επιλέξτε ένα τμήμα από την πλαϊνή μπάρα για να συνεχίσετε.")
else:
    # ----------------------------------------------------
    # ΕΠΙΛΟΓΗ 2: ΕΙΣΑΓΩΓΗ ΚΑΤΑΛΟΓΟΥ (ΔΙΟΡΘΩΜΕΝΟ & ΣΤΑΘΕΡΟ)
    # ----------------------------------------------------
    if mode == t["opt2"]:
        st.subheader(t["box2_title"])
        st.write(f"Τρέχον Τμήμα: **{selected_class}**")
        
        roster_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="roster_uploader_main")
        roster_path = os.path.join(UPLOAD_FOLDER, f"roster_{selected_class}.jpg")
        
        # Ανέβασμα και προσωρινή αποθήκευση
        if roster_file is not None:
            try:
                roster_bytes = roster_file.getbuffer()
                compressed_roster = compress_image(roster_bytes)
                with open(roster_path, "wb") as f:
                    f.write(compressed_roster)
            except Exception as e:
                st.error(f"⚠️ Σφάλμα αποθήκευσης εικόνας: {e}")

        # Εμφάνιση εικόνας και κουμπιού ΑΝ υπάρχει το αρχείο τοπικά
        if os.path.exists(roster_path):
            st.image(roster_path, caption=t["roster_photo_caption"], width=400)
            st.markdown("---")
            
            # ΣΤΑΘΕΡΟ ΚΟΥΜΠΙ ΑΝΑΓΝΩΣΗΣ
            if st.button(t["btn_read_names"], type="primary", key="btn_read_roster_action"):
                api_key_val = st.session_state["config"].get("api_key", "").strip()
                if not api_key_val:
                    st.error("⚠️ Παρακαλώ εισάγετε πρώτα το Gemini API Key σας στην πλαϊνή μπάρα!")
                else:
                    with st.spinner(t["catalog_spinner"]):
                        try:
                            client = genai.Client(api_key=api_key_val)
                            roster_img = Image.open(roster_path)
                            prompt_roster = (
                                f"Extract all student names for class section {selected_class} from this roster image.\n"
                                "Return ONLY a valid JSON array of strings containing the student names as they appear.\n"
                                "Do not include markdown formatting or extra text.\n"
                                "Example: [\"Αλέξανδρος Παπαδόπουλος\", \"Μαρία Ιωάννου\"]"
                            )
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[prompt_roster, roster_img]
                            )
                            resp_text = response.text if response and response.text else ""
                            clean_text = resp_text.replace("```json", "").replace("```", "").strip()
                            
                            extracted_names = []
                            json_match = re.search(r'\[.*\]', clean_text, re.DOTALL)
                            if json_match:
                                extracted_names = json.loads(json_match.group(0))
                            
                            if extracted_names and isinstance(extracted_names, list):
                                st.session_state["students_db"][selected_class] = [str(n).strip() for n in extracted_names if str(n).strip()]
                                save_students(st.session_state["students_db"])
                                st.success(f"🎉 Επιτυχής εισαγωγή {len(extracted_names)} μαθητών στο τμήμα {selected_class}!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Δεν εντοπίστηκαν ονόματα αυτόματα. Απάντηση AI:")
                                st.code(resp_text)
                        except Exception as e:
                            st.error(f"⚠️ Σφάλμα κατά την ανάγνωση: {type(e).__name__} - {str(e)}")
        else:
            st.info("💡 Παρακαλώ ανεβάστε μια φωτογραφία του καταλόγου μαθητών για να εμφανιστεί η επιλογή ανάγνωσης.")
            
        # Εμφάνιση υπαρχόντων μαθητών τμήματος
        current_students = st.session_state["students_db"].get(selected_class, [])
        if current_students:
            st.markdown("---")
            st.subheader(f"📋 Εγγεγραμμένοι Μαθητές Τμήματος {selected_class} ({len(current_students)})")
            for idx, student in enumerate(current_students, 1):
                st.write(f"{idx}. {student}")

    # ----------------------------------------------------
    # ΕΠΙΛΟΓΗ 1: ΑΞΙΟΛΟΓΗΣΗ ΤΕΤΡΑΔΙΩΝ
    # ----------------------------------------------------
    elif mode == t["opt1"]:
        st.subheader("📝 Υποβοηθούμενη Αξιολόγηση Τετραδίου")
        st.write(f"Τμήμα: **{selected_class}**")
        
        current_students = st.session_state["students_db"].get(selected_class, [])
        if not current_students:
            st.warning("⚠️ Δεν έχετε περάσει μαθητές για αυτό το τμήμα. Πηγαίνετε πρώτα στην 'Εισαγωγή Καταλόγου'.")
        else:
            student_choice = st.selectbox("Επιλογή Μαθητή:", current_students)
            homework_file = st.file_uploader("Ανεβάστε φωτογραφία τετραδίου μαθητή:", type=["png", "jpg", "jpeg"], key="hw_uploader")
            
            if homework_file and st.button("🚀 Αξιολόγηση με Gemini", type="primary"):
                api_key_val = st.session_state["config"].get("api_key", "").strip()
                if not api_key_val:
                    st.error("⚠️ Παρακαλώ εισάγετε το Gemini API Key σας!")
                else:
                    with st.spinner("Αξιολόγηση εργασίας σε εξέλιξη..."):
                        hw_bytes = homework_file.getbuffer()
                        compressed_hw = compress_image(hw_bytes)
                        hw_img = Image.open(io.BytesIO(compressed_hw))
                        
                        client = genai.Client(api_key=api_key_val)
                        prompt_hw = f"Evaluate this homework for student {student_choice}. Give a score out of 10 and constructive feedback in Greek."
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[prompt_hw, hw_img]
                        )
                        st.success("✅ Η αξιολόγηση ολοκληρώθηκε!")
                        st.write(response.text)

    # ----------------------------------------------------
    # ΕΠΙΛΟΓΗ 3: ΑΝΑΦΟΡΕΣ / ΕΞΑΓΩΓΗ
    # ----------------------------------------------------
    elif mode == t["opt3"]:
        st.subheader("📊 Προβολή & Εξαγωγή Βαθμών")
        st.write(f"Τμήμα: **{selected_class}**")
        current_students = st.session_state["students_db"].get(selected_class, [])
        if current_students:
            df = pd.DataFrame({"Μαθητής": current_students, "Βαθμός": ["-"] * len(current_students)})
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Δεν υπάρχουν μαθητές καταχωρημένοι στο τμήμα αυτό.")
