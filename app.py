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

# ΕΞΥΠΝΗ ΣΥΝΑΡΤΗΣΗ ΜΕ AUTO-RETRY ΚΑΙ ΕΝΗΜΕΡΩΣΗ ΧΡΗΣΤΗ
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
        except Exception as e:
            print(f"Gemini API Error (προσπάθεια {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                st.toast(f"⚠️ Στιγμιαίο κόλλημα δικτύου. Γίνεται αυτόματη επανάληψη ({attempt+2}/3)...", icon="🔄")
                time.sleep(2)
            else:
                st.error(f"❌ Αποτυχία σύνδεσης με το Gemini API μετά από {max_retries} προσπάθειες. Λεπτομέρειες: {str(e)}")
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
    },
    "Français": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Correcteur intelligent de devoirs – Assistant enseignant*",
        "hw_section": "📖 Sujet & Correction",
        "hw_desc": "📸 Téléchargez le sujet et la solution officielle :",
        "hw_saved": "Page(s) de devoirs enregistrées !",
        "sol_saved": "Page(s) de correction enregistrées !",
        "class_mgmt": "⚙️ Gestion des classes",
        "select_class": "Sélectionner la classe :",
        "add_new_class": "➕ Ajouter une section :",
        "btn_add_class": "Ajouter",
        "remove_class": "❌ Supprimer la section :",
        "btn_remove_class": "Supprimer",
        "students_in": "Élèves de la section",
        "add_student": "Ajouter un élève :",
        "btn_add": "➕ Ajouter",
        "remove_student": "Supprimer l'élève :",
        "btn_remove": "❌ Supprimer",
        "api_prompt": "🔑 Clé API Google Gemini",
        "save_api": "💾 Enregistrer la clé",
        "audio_toggle": "🔊 Activer l'alerte sonore",
        "api_saved_success": "Clé API enregistrée avec succès !",
        "menu_title": "📌 Mode :",
        "opt1": "📷 1. Correction assistée",
        "opt2": "📋 2. Importer la liste",
        "opt3": "📊 3. Tableau de progression",
        "batch_upload": "📸 Prendre en photo ou sélectionner les cahiers :",
        "folder_found": "cahiers prêts.",
        "clear_notebooks": "🗑️ Vider le dossier",
        "btn_evaluate": "🔍 Générer les évaluations",
        "eval_success": "Évaluation enregistrée !",
        "catalog_sec": "📷 Importer la liste de classe",
        "upload_catalog": "📸 Photo de la liste :",
        "btn_read_names": "🤖 Lire et enregistrer",
        "stats_sec": "📊 Matrice de progression",
        "sidebar_stop_text": "🔴 IMPORTANT :<br>Faites défiler 👇<br>pour choisir la classe.",
        "alert_box": "⚙️ Gérez vos classes dans la barre latérale et entrez votre clé API.",
        "uploader_label_hw": "📸 Sujet du devoir",
        "uploader_label_sol": "💡 Solution officielle",
        "box1_title": "🗂️ Correction des devoirs par IA",
        "box2_title": "🗂️ Importer la liste",
        "box3_title": "🗂️ Tableau de progression",
        "roster_photo_caption": "Photo de la liste",
        "no_classes_warn": "⚠️ Aucune section disponible.",
        "no_students_yet": "Aucun élève ajouté.",
        "current_class_label": "Section actuelle :",
        "catalog_spinner": "⏳ Analyse de la liste...",
        "workflow_info": "💡 <b>Mode hybride :</b> L'IA compare le sujet et la solution avec le cahier de l'élève.",
        "hw_warn_box1": "⚠️ Veuillez d'abord charger le sujet dans la barre latérale.",
        "hw_err_eval": "⚠️ Veuillez charger le sujet !",
        "no_notebooks_warn": "⚠️ Aucun cahier trouvé.",
        "eval_complete_msg": "🎉 Analyse terminée !",
        "bulk_success_msg": "🎉 Toutes les notes ont été enregistrées !"
    },
    "Deutsch": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Intelligenter Hausaufgaben-Korrektor*",
        "hw_section": "📖 Aufgabe & Lösung",
        "hw_desc": "📸 Aufgabe und offizielle Lösung hochladen:",
        "hw_saved": "Aufgabe gespeichert!",
        "sol_saved": "Lösung gespeichert!",
        "class_mgmt": "⚙️ Klassenverwaltung",
        "select_class": "Klasse auswählen:",
        "add_new_class": "➕ Neue Klasse:",
        "btn_add_class": "Hinzufügen",
        "remove_class": "❌ Klasse löschen:",
        "btn_remove_class": "Löschen",
        "students_in": "Schüler in der Klasse",
        "add_student": "Schüler hinzufügen:",
        "btn_add": "➕ Hinzufügen",
        "remove_student": "Schüler entfernen:",
        "btn_remove": "❌ Entfernen",
        "api_prompt": "🔑 Google Gemini API-Schlüssel",
        "save_api": "💾 Schlüssel speichern",
        "audio_toggle": "🔊 Tonbenachrichtigung aktivieren",
        "api_saved_success": "API-Schlüssel gespeichert!",
        "menu_title": "📌 Modus wählen:",
        "opt1": "📷 1. Assistierte Korrektur",
        "opt2": "📋 2. Klassenliste importieren",
        "opt3": "📊 3. Fortschrittstabelle",
        "batch_upload": "📸 Fotos der Hefte auswählen:",
        "folder_found": "Hefte bereit.",
        "clear_notebooks": "🗑️ Ordner leeren",
        "btn_evaluate": "🔍 Bewertungen generieren",
        "eval_success": "Erfolgreich bewertet!",
        "catalog_sec": "📷 Klassenliste importieren",
        "upload_catalog": "📸 Foto der Liste:",
        "btn_read_names": "🤖 Namen automatisch lesen",
        "stats_sec": "📊 Fortschrittsmatrix",
        "sidebar_stop_text": "🔴 WICHTIG:<br>Nach unten scrollen 👇",
        "alert_box": "⚙️ Klassen verwalten und API-Schlüssel eingeben.",
        "uploader_label_hw": "📸 Aufgabenfoto",
        "uploader_label_sol": "💡 Musterlösung",
        "box1_title": "🗂️ KI-Hausaufgabenkorrektur",
        "box2_title": "🗂️ Liste importieren",
        "box3_title": "🗂️ Fortschrittstabelle",
        "roster_photo_caption": "Listenfoto",
        "no_classes_warn": "⚠️ Keine Klassen vorhanden.",
        "no_students_yet": "Keine Schüler hinzugefügt.",
        "current_class_label": "Aktuelle Klasse:",
        "catalog_spinner": "⏳ KI analysiert die Liste...",
        "workflow_info": "💡 <b>Workflow:</b> KI vergleicht Aufgabe & Lösung mit dem Schülerheft.",
        "hw_warn_box1": "⚠️ Bitte laden Sie zuerst die Aufgabe in der Seitenleiste hoch.",
        "hw_err_eval": "⚠️ Bitte Aufgabe hochladen!",
        "no_notebooks_warn": "⚠️ Keine Hefte gefunden.",
        "eval_complete_msg": "🎉 Analyse abgeschlossen!",
        "bulk_success_msg": "🎉 Alle Noten gespeichert!"
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
            st.write(f"Συμπίεση αρχείου {idx+1} από {total_hw}...")
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
        {t["alert_box"]}
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
            st.success(f"✅ {notebook_count} {t['folder_found']}")
            if st.button(t["clear_notebooks"]):
                with st.spinner("🗑️ Εκκαθάριση φακέλου τετραδίων..."):
                    for f in existing_notebooks:
                        try:
                            os.remove(os.path.join(UPLOAD_FOLDER, f))
                        except:
                            pass
                    st.session_state["pending_evaluations"] = []
                st.rerun()
        
        st.markdown("---")
        
        if st.button(t["btn_evaluate"]):
            api_key_val = st.session_state["config"].get("api_key", "").strip()
            if not api_key_val:
                st.error("⚠️ Please enter your Gemini API Key first above!")
            elif not homework_images:
                st.error(t["hw_err_eval"])
            else:
                nb_images_paths = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('student_page_')]
                if not nb_images_paths:
                    st.warning(t["no_notebooks_warn"])
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
                                    f"4. FEEDBACK: Write 1 concise sentence explaining the score in the following language: {app_lang}.\n"
                                    "Format strictly as:\n"
                                    "NAME: [Student Name]\n"
                                    "SCORE: [Score]\n"
                                    "FEEDBACK: [Feedback]"
                                )
                                
                                contents_to_send = homework_images + solution_images + [nb_img, prompt_eval]
                                resp_text = call_gemini_safe(client, 'gemini-3.8-flash', contents_to_send)
                                
                                matched_student = class_students[i % len(class_students)] if class_students else f"Student_{i+1}"
                                score_val = 50
                                feedback_val = "Review needed."
                                
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
                        
                        st.success(t["eval_complete_msg"])
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
                st.success(t["bulk_success_msg"])
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
                    cat_progress = st.progress(0, text="🔄 Ανάγνωση καταλόγου μαθητών...")
                    cat_status = st.empty()
                    cat_status.markdown(f"⏳ {t['catalog_spinner']}")
                    
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

    elif mode == t["opt3"]:
        st.subheader(t["box3_title"])
        st.write(f"📊 {t['stats_sec']} - {selected_class}")
