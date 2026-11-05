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
                    osc.frequency.value = freq;
                    gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + time);
                    osc.connect(gain);
                    gain.connect(audioCtx.destination);
                    osc.start();
                    osc.stop(audioCtx.currentTime + time);
                }, delay);
            }
            playTone(523.25, 0.3, 0);
            playTone(659.25, 0.3, 150);
            playTone(783.99, 0.5, 300);
        </script>
    """
    components.html(sound_html, height=0, width=0)

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

# --- 3. SIDEBAR: ΕΚΦΩΝΗΣΗ, ΣΩΣΤΗ ΛΥΣΗ & ΤΜΗΜΑΤΑ ---
st.markdown("🎓 GradeMind AI")
st.markdown("### *Smart Homework & Test Grader – Ο Έξυπνος Ψηφιακός Βοηθός Δασκάλου*")

st.sidebar.header("📖 Εκφώνηση & Σωστή Λύση")
st.sidebar.write("📸 Ανεβάστε την Εκφώνηση ΚΑΙ τη Σωστή Λύση:")

hw_files = st.sidebar.file_uploader(
    "📸 Φωτογραφία Εκφώνησης (Homework)",
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
            st.write(f"Συμπίεση αρχείου {idx+1} από {total_hw}...")
            compressed_bytes = compress_image(hw_f.getbuffer())
            hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{idx}.jpg")
            with open(hw_path, "wb") as f:
                f.write(compressed_bytes)
        status.update(label="✅ Η εκφώνηση αποθηκεύτηκε με επιτυχία!", state="complete", expanded=False)

sol_files = st.sidebar.file_uploader(
    "💡 Φωτογραφία Σωστής Λύσης / Απάντησης",
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
            st.write(f"Συμπίεση λύσης {idx+1} από {total_sol}...")
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
        st.sidebar.success(f"✅ {len(homework_images)} σελίδα/σελίδες Εκφώνησης αποθηκεύτηκαν!")
    if solution_images:
        st.sidebar.success(f"✅ {len(solution_images)} σελίδα/σελίδες Σωστής Λύσης αποθηκεύτηκαν!")
        
    if st.sidebar.button("🗑️ Εκκαθάριση Εκφώνησης & Λύσης", key="clear_hw_btn"):
        with st.spinner("🗑️ Διαγραφή αρχείων..."):
            for p in hw_paths_in_folder + sol_paths_in_folder:
                try:
                    os.remove(p)
                except:
                    pass
        st.rerun()

st.sidebar.markdown("""
    <div class="sidebar-stop-box">
        🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Διαχείριση Τάξης & Τμημάτων")

new_class_input = st.sidebar.text_input("➕ Δημιουργία Νέου Τμήματος (π.χ. Β3):")
if st.sidebar.button("Προσθήκη Τμήματος"):
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
    class_to_remove = st.sidebar.selectbox("❌ Διαγραφή Τμήματος:", ["-- Select --"] + list(st.session_state["students_db"].keys()))
    if st.sidebar.button("Διαγραφή Τμήματος"):
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
    st.warning("⚠️ Δεν υπάρχουν διαθέσιμα τμήματα. Δημιουργήστε ένα τμήμα από την πλαϊνή μπάρα για να ξεκινήσετε.")
else:
    if "selected_class" not in st.session_state or st.session_state["selected_class"] not in st.session_state["students_db"]:
        st.session_state["selected_class"] = list(st.session_state["students_db"].keys())[0]

    selected_class_sidebar = st.sidebar.selectbox(
        "Επιλογή Τμήματος:", 
        list(st.session_state["students_db"].keys()), 
        index=list(st.session_state["students_db"].keys()).index(st.session_state["selected_class"])
    )
    if selected_class_sidebar != st.session_state["selected_class"]:
        st.session_state["selected_class"] = selected_class_sidebar
        st.rerun()

    selected_class = st.session_state["selected_class"]

    st.sidebar.subheader(f"Μαθητές Τμήματος {selected_class}")
    new_student = st.sidebar.text_input("Προσθήκη νέου μαθητή:")
    if st.sidebar.button("➕ Προσθήκη Μαθητή"):
        if new_student and new_student not in st.session_state["students_db"][selected_class]:
            with st.spinner("➕ Προσθήκη μαθητή..."):
                st.session_state["students_db"][selected_class].append(new_student)
                save_students(st.session_state["students_db"])
            st.sidebar.success(f"Added {new_student}")
            st.rerun()

    if st.session_state["students_db"][selected_class]:
        student_to_remove = st.sidebar.selectbox("Αφαίρεση μαθητή:", ["-- Select --"] + st.session_state["students_db"][selected_class])
        if st.sidebar.button("❌ Διαγραφή Μαθητή"):
            if student_to_remove != "-- Select --":
                with st.spinner("❌ Αφαίρεση μαθητή..."):
                    st.session_state["students_db"][selected_class].remove(student_to_remove)
                    save_students(st.session_state["students_db"])
                st.sidebar.warning(f"Removed {student_to_remove}")
                st.rerun()
    else:
        st.sidebar.info("Δεν έχουν προστεθεί μαθητές ακόμα.")

# --- 4. ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ, API KEY & AUDIO TOGGLE ---
st.markdown("""
    <div class="custom-alert-box">
        ⚙️ Διαχειριστείτε τα τμήματα από την πλαϊνή μπάρα και εισάγετε το API Key σας παρακάτω.
    </div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown("### 🔑 Google Gemini API Key")
    current_api_key = st.session_state["config"].get("api_key", "")
    api_key_input = st.text_input("API Key:", value=current_api_key, type="password", key="main_api_key_input", label_visibility="collapsed")
    
    audio_enabled_val = st.session_state["config"].get("audio_target", True)
    audio_toggle = st.checkbox("🔊 Ηχητική ειδοποίηση κατά την ολοκλήρωση", value=audio_enabled_val, key="audio_toggle_box")
    if audio_toggle != audio_enabled_val:
        st.session_state["config"]["audio_target"] = audio_toggle
        save_config(st.session_state["config"])

    if st.button("💾 Αποθήκευση API Key"):
        if api_key_input.strip():
            with st.spinner("💾 Αποθήκευση ρυθμίσεων & API Key..."):
                st.session_state["config"]["api_key"] = api_key_input.strip()
                save_config(st.session_state["config"])
            st.success("Το API Key αποθηκεύτηκε επιτυχώς!")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Please enter a valid API Key.")

st.markdown("---")

st.markdown("""
    <div class="custom-info-card">
        💡 <b>Υβριδική Λειτουργία:</b> Το AI συγκρίνει Εκφώνηση + Σωστή Λύση με το τετράδιο του μαθητή, προτείνει βαθμό και σχόλια. Ελέγξτε ή εγκρίνετε μαζικά!
    </div>
""", unsafe_allow_html=True)

if not st.session_state["students_db"]:
    st.info("👈 Please create at least one section from the sidebar to get started.")
else:
    mode = st.radio(
        "📌 Επιλέξτε Λειτουργία (Κάθετο Μενού):",
        ("📷 1. Υποβοηθούμενη Αξιολόγηση", "📋 2. Εισαγωγή Καταλόγου", "📊 3. Πίνακας Προόδου & Αναφορές"),
        horizontal=True
    )

    if mode == "📷 1. Υποβοηθούμενη Αξιολόγηση":
        st.subheader("🗂️ Κουτάκι 1: Υποβοηθούμενη Αξιολόγηση Άσκησης")
        if not homework_images:
            st.warning("⚠️ Σημείωση: Ανεβάστε πρώτα την εκφώνηση της άσκησης από το πλαϊνό μενού (Sidebar).")
        
        notebook_files = st.file_uploader(
            "📸 Τραβήξτε φωτογραφία με την κάμερα ή επιλέξτε αρχεία τετραδίων (συμπιέζονται αυτόματα):",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="notebook_batch_uploader"
        )
        
        if notebook_files:
            with st.status("🔄 Συμπίεση & αποθήκευση φωτογραφιών τετραδίων...", expanded=True) as nb_status:
                for idx, nb_file in enumerate(notebook_files):
                    st.write(f"Επεξεργασία τετραδίου {idx+1} από {len(notebook_files)}...")
                    compressed_bytes = compress_image(nb_file.getbuffer())
                    unique_filename = f"student_page_{int(time.time())}_{idx}.jpg"
                    nb_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    with open(nb_path, "wb") as f:
                        f.write(compressed_bytes)
                nb_status.update(label="✅ Τα τετράδια ετοιμάστηκαν για ανάλυση!", state="complete", expanded=False)
        
        existing_notebooks = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith('student_page_')]
        notebook_count = len(existing_notebooks)
        
        if notebook_count > 0:
            st.success(f"✅ {notebook_count} φωτογραφίες σελίδων μαθητών είναι έτοιμες στον φάκελο.")
            if st.button("🗑️ Εκκαθάριση Φακέλου Τετραδίων"):
                with st.spinner("🗑️ Εκκαθάριση φακέλου τετραδίων..."):
                    for f in existing_notebooks:
                        try:
                            os.remove(os.path.join(UPLOAD_FOLDER, f))
                        except:
                            pass
                    st.session_state["pending_evaluations"] = []
                st.rerun()
        
        st.markdown("---")
        
        if st.button("🔍 Δημιουργία Προτεινόμενων Αξιολογήσεων"):
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
                        st.session_state["pending_evaluations"] = []
                        class_students = st.session_state["students_db"].get(selected_class, [])
                        
                        total_files = len(nb_images_paths)
                        
                        progress_bar = st.progress(0, text="🔄 Προετοιμασία AI...")
                        status_box = st.empty()
                        
                        start_time = time.time()
                        
                        for i, nb_p in enumerate(nb_images_paths):
                            elapsed = time.time() - start_time
                            avg_time_per_item = elapsed / i if i > 0 else 3.5
                            remaining_items = total_files - i
                            est_sec = int(avg_time_per_item * remaining_items)
                            
                            pct = int(((i) / total_files) * 100)
                            progress_bar.progress(
                                (i) / total_files, 
                                text=f"🔄 Προόδος AI: {pct}% (Τετράδιο {i+1} από {total_files})"
                            )
                            status_box.markdown(f"⏱️ *Εκτιμώμενος υπολειπόμενος χρόνος: ~{est_sec} δευτερόλεπτα*")
                            
                            try:
                                nb_img = Image.open(nb_p)
                                prompt_eval = (
                                    f"Official Roster: {class_students}\n"
                                    "You are an expert teacher. Examine the provided Homework Prompt, Official Solution (if provided), and Student Notebook Page.\n"
                                    "1. READ STUDENT NAME: Scan the top of the notebook page for the student's name and match it to the Official Roster.\n"
                                    "2. EVALUATE WORK: Compare student's steps and final answer against the prompt and solution.\n"
                                    "3. SCORE: Assign 100 (Fully correct), 50 (Partial/minor error), or 0 (Incorrect/missing).\n"
                                    "4. FEEDBACK: Write 1 concise sentence explaining the score in Greek.\n"
                                    "Format strictly as:\n"
                                    "NAME: [Student Name]\n"
                                    "SCORE: [Score]\n"
                                    "FEEDBACK: [Feedback in Greek]"
                                )
                                
                                contents_to_send = homework_images + solution_images + [nb_img, prompt_eval]
                                resp_text = call_gemini_safe(client, 'gemini-3.8-flash', contents_to_send)
                                if not resp_text:
                                    resp_text = call_gemini_safe(client, 'gemini-2.5-flash', contents_to_send)
                                
                                matched_student = class_students[i % len(class_students)] if class_students else f"Student_{i+1}"
                                score_val = 50
                                feedback_val = "Χρειάζεται επανέλεγχο."
                                
                                if resp_text:
                                    name_match = re.search(r'NAME:\s*(.+)', resp_text, re.IGNORECASE)
                                    if name_match:
                                        raw_name = name_match.group(1).strip()
                                        for s in class_students:
                                            if s.lower() in raw_name.lower() or raw_name.lower() in s.lower():
                                                matched_student = s
                                                break
                                    
                                    score_match = re.search(r'SCORE:\s*(100|50|0)', resp_text, re.IGNORECASE)
                                    if score_match:
                                        score_val = int(score_match.group(1))
                                    
                                    fb_match = re.search(r'FEEDBACK:\s*(.+)', resp_text, re.IGNORECASE | re.DOTALL)
                                    if fb_match:
                                        feedback_val = fb_match.group(1).strip()[:200]

                                st.session_state["pending_evaluations"].append({
                                    "img_path": nb_p,
                                    "student": matched_student,
                                    "score": score_val,
                                    "feedback": feedback_val
                                })
                            except Exception as inner_e:
                                print(f"Skipping image due to error: {inner_e}")
                        
                        progress_bar.progress(1.0, text="✅ Ολοκληρώθηκε!")
                        time.sleep(0.3)
                        progress_bar.empty()
                        status_box.empty()
                        
                        if st.session_state["config"].get("audio_target", True):
                            play_success_sound()
                        
                        st.success("🎉 Η ανάλυση AI ολοκληρώθηκε επιτυχώς! Επιθεωρήστε, διορθώστε ή εγκρίνετε μαζικά παρακάτω.")
                    except Exception as e:
                        st.error(f"⚠️ Processing error: {str(e)}")

        if st.session_state["pending_evaluations"]:
            st.markdown("### 📋 Επισκόπηση & Τελική Έγκριση Καθηγητή")
            st.write("Μπορείτε είτε να ελέγξετε κάθε μαθητή ξεχωριστά είτε να πατήσετε **Μαζική Έγκριση** για άμεση καταχώρηση:")
            
            if st.button("🚀⚡ Μαζική Έγκριση & Αποθήκευση Όλων (Fast-Track)", type="primary"):
                with st.spinner("💾 Μαζική αποθήκευση βαθμολογιών στον Πίνακα Προόδου..."):
                    bulk_records = []
                    today_str = datetime.date.today().strftime("%Y-%m-%d")
                    for item in st.session_state["pending_evaluations"]:
                        bulk_records.append({
                            "Section": selected_class,
                            "Student": item["student"],
                            "Date": today_str,
                            "Score": item["score"],
                            "Feedback": item["feedback"]
                        })
                    
                    df_new = pd.DataFrame(bulk_records)
                    existing_df = st.session_state["grades_df"]
                    if not existing_df.empty:
                        existing_df = existing_df[~((existing_df["Section"] == selected_class) & (existing_df["Date"] == today_str))]
                    
                    st.session_state["grades_df"] = pd.concat([existing_df, df_new], ignore_index=True)
                    save_grades_df(st.session_state["grades_df"])
                    st.session_state["pending_evaluations"] = []
                    
                st.balloons()
                st.success("🎉 Όλες οι βαθμολογίες εγκρίθηκαν και αποθηκεύτηκαν μαζικά στον Πίνακα Προόδου!")
                time.sleep(1)
                st.rerun()

            st.markdown("---")
            st.write("Ή αναλυτικός έλεγχος ανά μαθητή:")
            
            updated_results = []
            class_students = st.session_state["students_db"].get(selected_class, [])
            
            for idx, item in enumerate(st.session_state["pending_evaluations"]):
                st.markdown(f"#### 📄 Μαθητής #{idx+1}")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    try:
                        st.image(item["img_path"], use_column_width=True, caption=f"Φωτογραφία #{idx+1}")
                        with st.expander(f"🔍 Μεγέθυνση Φωτογραφίας #{idx+1}"):
                            st.image(item["img_path"], use_column_width=True)
                    except:
                        st.write("Εικόνα τετραδίου")
                        
                with col2:
                    student_idx = class_students.index(item["student"]) if item["student"] in class_students else 0
                    sel_student = st.selectbox(f"Μαθητής #{idx+1}:", class_students, index=student_idx, key=f"sel_st_{idx}")
                    
                    sel_score = st.radio(
                        f"Βαθμός #{idx+1}:", 
                        [100, 50, 0], 
                        index=[100, 50, 0].index(item["score"]) if item["score"] in [100, 50, 0] else 1, 
                        horizontal=True,
                        key=f"sel_sc_{idx}"
                    )
                    
                    sel_fb = st.text_area(f"Σχόλιο #{idx+1}:", value=item["feedback"], height=70, key=f"sel_fb_{idx}")
                    
                    updated_results.append({
                        "Section": selected_class,
                        "Student": sel_student,
                        "Date": datetime.date.today().strftime("%Y-%m-%d"),
                        "Score": sel_score,
                        "Feedback": sel_fb
                    })
                st.markdown("---")
            
            if st.button("💾 Οριστική Αποθήκευση Επιλεγμένων", type="primary"):
                with st.spinner("💾 Αποθήκευση αλλαγών..."):
                    df_new = pd.DataFrame(updated_results)
                    existing_df = st.session_state["grades_df"]
                    today_str = datetime.date.today().strftime("%Y-%m-%d")
                    
                    if not existing_df.empty:
                        existing_df = existing_df[~((existing_df["Section"] == selected_class) & (existing_df["Date"] == today_str))]
                    
                    st.session_state["grades_df"] = pd.concat([existing_df, df_new], ignore_index=True)
                    save_grades_df(st.session_state["grades_df"])
                    st.session_state["pending_evaluations"] = []
                    
                st.balloons()
                st.success("🎉 Οι βαθμολογίες εγκρίθηκαν και αποθηκεύτηκαν επιτυχώς στον Πίνακα Προόδου!")
                time.sleep(1)
                st.rerun()

    elif mode == "📋 2. Εισαγωγή Καταλόγου":
        st.subheader("🗂️ Κουτάκι 2: Εισαγωγή Καταλόγου")
        st.write(f"**Τρέχον Τμήμα:** {selected_class}")
        
        catalog_file = st.file_uploader("📸 Τραβήξτε φωτογραφία καταλόγου με κάμερα ή ανεβάστε αρχείο:", type=["png", "jpg", "jpeg"], key="catalog_uploader")
        if catalog_file:
            catalog_path = os.path.join(UPLOAD_FOLDER, "catalog_temp.jpg")
            with open(catalog_path, "wb") as f:
                f.write(compress_image(catalog_file.getbuffer()))
            
            st.image(catalog_path, caption="Φωτογραφία Καταλόγου", width=300)
            
            if st.button("🤖 Ανάγνωση & Αυτόματη Αποθήκευση Καταλόγου"):
                api_key_val = st.session_state["config"].get("api_key", "").strip()
                if not api_key_val:
                    st.error("⚠️ Please enter your Gemini API Key first above!")
                else:
                    cat_progress = st.progress(0, text="🔄 Ανάγνωση καταλόγου μαθητών...")
                    cat_status = st.empty()
                    cat_status.markdown("⏳ Το AI αναλύει και οργανώνει τον κατάλογο της τάξης...")
                    
                    cat_progress.progress(35, text="🔄 Αποστολή εικόνας στο AI...")
                    time.sleep(0.5)
                    
                    try:
                        client = genai.Client(api_key=api_key_val)
                        img_to_send = Image.open(catalog_path)
                        
                        prompt = (
                            "Read all student names from this school roster image. "
                            "If last name and first name are in separate columns, combine them. "
                            "List only the full names, one per line. Do not include numbers, codes, or extra text."
                        )
                        
                        cat_progress.progress(70, text="🔄 Επεξεργασία ονομάτων...")
                        response_text = call_gemini_safe(client, 'gemini-3.8-flash', [img_to_send, prompt])
                        if not response_text:
                            response_text = call_gemini_safe(client, 'gemini-2.5-flash', [img_to_send, prompt])
                            
                        cat_progress.progress(100, text="✅ Ολοκληρώθηκε!")
                        time.sleep(0.3)
                        cat_status.empty()
                        cat_progress.empty()
                        
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
                        if 'cat_status' in locals():
                            cat_status.empty()
                        if 'cat_progress' in locals():
                            cat_progress.empty()
                        st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == "📊 3. Πίνακας Προόδου & Αναφορές":
        st.subheader("🗂️ Κουτάκι 3: Πίνακας Προόδου & Αναφορές")
        st.write(f"📊 Συνολικός Πίνακας Προόδου Τμήματος (Excel Style) - {selected_class}")
        
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
            st.info("Δεν έχουν προστεθεί μαθητές ακόμα.")
