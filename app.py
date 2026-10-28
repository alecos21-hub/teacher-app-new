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

# Τα English είναι πρώτα ώστε να γίνουν default
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
        "api_prompt": "Enter Google Gemini API Key",
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
        "eval_success": "Successfully saved to Progress Table!",
        "view_eval": "🔍 View Latest Evaluation",
        "catalog_sec": "📷 Import Class Roster for Section",
        "upload_catalog": "📸 Take roster photo with camera or upload file:",
        "btn_read_names": "🤖 Read & Auto-Save Roster",
        "stats_sec": "📊 Class Progress Matrix (Excel Style)",
        "btn_close_day": "🚨 Mark Missing Homework for Today",
        "manual_delete": "🗑️ Delete Records",
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.<br><span style='font-size: 11px; font-weight: normal;'>(Scroll down to select Department)</span>",
        "alert_box": "⚙️ Press the arrows <span class=\"red-badge\">&gt;&gt;</span> top left for Sections &amp; Language",
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
        "no_classes_warn": "⚠️ No sections available. Create a section from the left sidebar to get started.",
        "catalog_spinner": "⏳ AI is analyzing and organizing the class list... (Takes 1-2 minutes)",
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
    "Русский (Russian)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Умный помощник учителя для проверки домашних заданий*",
        "hw_section": "📖 Фотографии заданий",
        "hw_desc": "📸 Сделайте фото или загрузите страницы задания:",
        "hw_saved": "Страницы задания сохранены!",
        "class_mgmt": "⚙️ Управление классами",
        "select_class": "Выберите класс:",
        "add_new_class": "➕ Добавить новый класс:",
        "btn_add_class": "Добавить класс",
        "remove_class": "❌ Удалить класс:",
        "btn_remove_class": "Удалить класс",
        "students_in": "Ученики класса",
        "add_student": "Добавить нового ученика:",
        "btn_add": "➕ Добавить ученика",
        "remove_student": "Удалить ученика:",
        "btn_remove": "❌ Удалить ученика",
        "api_prompt": "Введите Google Gemini API Key",
        "save_api": "💾 Сохранить API Key",
        "api_saved_success": "API Key успешно сохранен!",
        "menu_title": "📌 Выберите режим:",
        "opt1": "📷 1. Автоматическая оценка",
        "opt2": "📋 2. Импорт списка",
        "opt3": "📊 3. Таблица успеваемости",
        "notebook_sec": "✨ Загрузка тетрадей учеников",
        "no_hw_warn": "⚠️ Внимание: Фотография задания не выбрана.",
        "batch_upload": "📸 Сделайте фото или выберите файлы тетрадей:",
        "folder_found": "фотографий тетрадей готовы в папке.",
        "btn_evaluate": "🚀 Начать оценку",
        "eval_success": "Успешно сохранено в таблицу!",
        "view_eval": "🔍 Просмотр последней оценки",
        "catalog_sec": "📷 Импорт списка класса",
        "upload_catalog": "📸 Сделайте фото списка или загрузите файл:",
        "btn_read_names": "🤖 Прочитать и сохранить список",
        "stats_sec": "📊 Матрица успеваемости класса",
        "btn_close_day": "🚨 Отметить отсутствующих на сегодня",
        "manual_delete": "🗑️ Удалить записи",
        "sidebar_stop_text": "🔴 ВАЖНО:<br>Прокрутите вниз 👇<br>для выбора класса.",
        "alert_box": "⚙️ Нажмите стрелки <span class=\"red-badge\">&gt;&gt;</span> вверху слева для классов и языка",
        "uploader_label_hw": "📸 Камера или файл задания",
        "uploader_label_notebook": "📸 Сделайте фото или выберите файлы тетрадей:",
        "expander_class": "🏫 Выбор класса и управление (Нажмите здесь)",
        "expander_lang": "🌐 Смена языка интерфейса (Нажмите здесь)",
        "current_class_label": "Текущий класс:",
        "change_class_label": "Изменить класс:",
        "no_students_yet": "Ученики еще не добавлены.",
        "section_students_text": "Ученики класса",
        "lang_select_label": "Язык интерфейса / Language:",
        "box1_title": "🗂️ Блок 1: Автоматическая оценка заданий",
        "box2_title": "🗂️ Блок 2: Импорт списка",
        "box3_title": "🗂️ Блок 3: Таблица успеваемости и отчеты",
        "view_photos_folder": "👁️ Просмотр фотографий в папке",
        "clear_folder": "🗑️ Очистить папку",
        "roster_photo_caption": "Фото списка",
        "no_classes_warn": "⚠️ Нет доступных классов. Создайте класс на левой панели.",
        "catalog_spinner": "⏳ ИИ анализирует и организует список класса... (Занимает 1-2 минуты)",
        "catalog_success": "✅ Список класса успешно зарегистрирован!"
    },
    "Français (French)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Assistant intelligent pour l'évaluation des devoirs*",
        "hw_section": "📖 Photos des consignes",
        "hw_desc": "📸 Prenez une photo ou téléchargez les consignes:",
        "hw_saved": "Page(s) de devoirs enregistrée(s) !",
        "class_mgmt": "⚙️ Gestion des classes",
        "select_class": "Sélectionner la classe :",
        "add_new_class": "➕ Ajouter une nouvelle classe :",
        "btn_add_class": "Ajouter la classe",
        "remove_class": "❌ Supprimer la classe :",
        "btn_remove_class": "Supprimer la classe",
        "students_in": "Élèves de la classe",
        "add_student": "Ajouter un nouvel élève :",
        "btn_add": "➕ Ajouter l'élève",
        "remove_student": "Supprimer un élève :",
        "btn_remove": "❌ Supprimer l'élève",
        "api_prompt": "Entrez la clé API Google Gemini",
        "save_api": "💾 Enregistrer la clé API",
        "api_saved_success": "Clé API enregistrée avec succès !",
        "menu_title": "📌 Sélectionner le mode :",
        "opt1": "📷 1. Correction automatique",
        "opt2": "📋 2. Importer la liste",
        "opt3": "📊 3. Tableau de progression",
        "notebook_sec": "✨ Capturer et télécharger les cahiers",
        "no_hw_warn": "⚠️ Remarque : Vous n'avez pas pris de photo de consigne.",
        "batch_upload": "📸 Prenez une photo ou sélectionnez des fichiers :",
        "folder_found": "photos de cahiers prêtes dans le dossier.",
        "btn_evaluate": "🚀 Lancer la correction",
        "eval_success": "Enregistré avec succès dans le tableau !",
        "view_eval": "🔍 Voir la dernière évaluation",
        "catalog_sec": "📷 Importer la liste de la classe",
        "upload_catalog": "📸 Prenez en photo la liste ou téléchargez un fichier :",
        "btn_read_names": "🤖 Lire et enregistrer la liste",
        "stats_sec": "📊 Matrice de progression de la classe",
        "btn_close_day": "🚨 Marquer les absents pour aujourd'hui",
        "manual_delete": "🗑️ Supprimer des enregistrements",
        "sidebar_stop_text": "🔴 IMPORTANT :<br>Faites défiler vers le bas 👇<br>pour choisir la classe.",
        "alert_box": "⚙️ Appuyez sur les flèches <span class=\"red-badge\">&gt;&gt;</span> en haut à gauche pour les classes et la langue",
        "uploader_label_hw": "📸 Appareil photo ou fichier de consigne",
        "uploader_label_notebook": "📸 Prenez une photo ou sélectionnez des fichiers :",
        "expander_class": "🏫 Sélection et gestion de classe (Cliquez ici)",
        "expander_lang": "🌐 Changement de langue (Cliquez ici)",
        "current_class_label": "Classe actuelle :",
        "change_class_label": "Changer de classe :",
        "no_students_yet": "Aucun élève ajouté pour l'instant.",
        "section_students_text": "Élèves de la classe",
        "lang_select_label": "Langue de l'interface / Language:",
        "box1_title": "🗂️ Bloc 1 : Correction automatique des devoirs",
        "box2_title": "🗂️ Bloc 2 : Importer la liste",
        "box3_title": "🗂️ Bloc 3 : Tableau de progression et rapports",
        "view_photos_folder": "👁️ Afficher les photos du dossier",
        "clear_folder": "🗑️ Vider le dossier",
        "roster_photo_caption": "Photo de la liste",
        "no_classes_warn": "⚠️ Aucune classe disponible. Créez une classe dans la barre latérale.",
        "catalog_spinner": "⏳ L'IA analyse et organise la liste de la classe... (Prend 1-2 minutes)",
        "catalog_success": "✅ Liste de classe enregistrée avec succès !"
    },
    "Italiano (Italian)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Assistente intelligente per la valutazione dei compiti*",
        "hw_section": "📖 Foto del compito",
        "hw_desc": "📸 Scatta una foto o carica la traccia:",
        "hw_saved": "Pagina/e del compito salvata/e!",
        "class_mgmt": "⚙️ Gestione classi",
        "select_class": "Seleziona classe:",
        "add_new_class": "➕ Aggiungi nuova classe:",
        "btn_add_class": "Aggiungi classe",
        "remove_class": "❌ Elimina classe:",
        "btn_remove_class": "Elimina classe",
        "students_in": "Studenti nella classe",
        "add_student": "Aggiungi nuovo studente:",
        "btn_add": "➕ Aggiungi studente",
        "remove_student": "Rimuovi studente:",
        "btn_remove": "❌ Elimina studente",
        "api_prompt": "Inserisci Google Gemini API Key",
        "save_api": "💾 Salva API Key",
        "api_saved_success": "API Key salvata con successo!",
        "menu_title": "📌 Seleziona modalità:",
        "opt1": "📷 1. Correzione automatica",
        "opt2": "📋 2. Importa registro",
        "opt3": "📊 3. Tabella dei progressi",
        "notebook_sec": "✨ Cattura e carica i quaderni",
        "no_hw_warn": "⚠️ Nota: Non hai scattato una foto della traccia.",
        "batch_upload": "📸 Scatta foto o seleziona file dei quaderni:",
        "folder_found": "foto di quaderni pronte nella cartella.",
        "btn_evaluate": "🚀 Avvia correzione",
        "eval_success": "Salvato con successo nella tabella!",
        "view_eval": "🔍 Visualizza ultima valutazione",
        "catalog_sec": "📷 Importa registro classe",
        "upload_catalog": "📸 Scatta foto del registro o carica file:",
        "btn_read_names": "🤖 Leggi e salva registro",
        "stats_sec": "📊 Matrice progressi della classe",
        "btn_close_day": "🚨 Segna assenti per oggi",
        "manual_delete": "🗑️ Elimina record",
        "sidebar_stop_text": "🔴 IMPORTANTE:<br>Scorri verso il basso 👇<br>per selezionare la classe.",
        "alert_box": "⚙️ Premi le frecce <span class=\"red-badge\">&gt;&gt;</span> in alto a sinistra per classi e lingua",
        "uploader_label_hw": "📸 Fotocamera o file del compito",
        "uploader_label_notebook": "📸 Scatta foto o seleziona file dei quaderni:",
        "expander_class": "🏫 Selezione e gestione classe (Clicca qui)",
        "expander_lang": "🌐 Cambio lingua UI (Clicca qui)",
        "current_class_label": "Classe corrente:",
        "change_class_label": "Cambia classe:",
        "no_students_yet": "Nessuno studente aggiunto.",
        "section_students_text": "Studenti della classe",
        "lang_select_label": "Lingua interfaccia / Language:",
        "box1_title": "🗂️ Blocco 1: Correzione automatica dei compiti",
        "box2_title": "🗂️ Blocco 2: Importa registro",
        "box3_title": "🗂️ Blocco 3: Tabella dei progressi e report",
        "view_photos_folder": "👁️ Visualizza foto nella cartella",
        "clear_folder": "🗑️ Pulisci cartella",
        "roster_photo_caption": "Foto del registro",
        "no_classes_warn": "⚠️ Nessuna classe disponibile. Crea una classe dalla barra laterale.",
        "catalog_spinner": "⏳ L'IA sta analizzando e organizzando la lista della classe... (Tarda 1-2 minuti)",
        "catalog_success": "✅ Lista di classe registrata con successo!"
    },
    "Deutsch (German)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Intelligenter Assistent für Hausaufgaben und Tests*",
        "hw_section": "📖 Aufgabenfotos",
        "hw_desc": "📸 Machen Sie ein Foto oder laden Sie die Aufgabe hoch:",
        "hw_saved": "Aufgabenseite(n) gespeichert!",
        "class_mgmt": "⚙️ Klassenverwaltung",
        "select_class": "Klasse auswählen:",
        "add_new_class": "➕ Neue Klasse hinzufügen:",
        "btn_add_class": "Klasse hinzufügen",
        "remove_class": "❌ Klasse löschen:",
        "btn_remove_class": "Klasse löschen",
        "students_in": "Schüler in der Klasse",
        "add_student": "Schüler hinzufügen:",
        "btn_add": "➕ Schüler hinzufügen",
        "remove_student": "Schüler entfernen:",
        "btn_remove": "❌ Schüler löschen",
        "api_prompt": "Google Gemini API-Schlüssel eingeben",
        "save_api": "💾 API-Schlüssel speichern",
        "api_saved_success": "API-Schlüssel erfolgreich gespeichert!",
        "menu_title": "📌 Modus auswählen:",
        "opt1": "📷 1. Automatische Bewertung",
        "opt2": "📋 2. Klassenliste importieren",
        "opt3": "📊 3. Fortschrittstabelle",
        "notebook_sec": "✨ Schülerhefte erfassen und hochladen",
        "no_hw_warn": "⚠️ Hinweis: Sie haben kein Aufgabenfoto aufgenommen.",
        "batch_upload": "📸 Foto aufnehmen oder Heftdateien auswählen:",
        "folder_found": "Heftfotos im Ordner bereit.",
        "btn_evaluate": "🚀 Bewertung starten",
        "eval_success": "Erfolgreich in der Tabelle gespeichert!",
        "view_eval": "🔍 Letzte Bewertung anzeigen",
        "catalog_sec": "📷 Klassenliste importieren",
        "upload_catalog": "📸 Listenfoto aufnehmen oder Datei hochladen:",
        "btn_read_names": "🤖 Liste lesen und speichern",
        "stats_sec": "📊 Klassen-Fortschrittsmatrix",
        "btn_close_day": "🚨 Fehlende Hausaufgaben für heute markieren",
        "manual_delete": "🗑️ Datensätze löschen",
        "sidebar_stop_text": "🔴 WICHTIG:<br>Nach unten scrollen 👇<br>um die Klasse auszuwählen.",
        "alert_box": "⚙️ Drücken Sie die Pfeile <span class=\"red-badge\">&gt;&gt;</span> oben links für Klassen und Sprache",
        "uploader_label_hw": "📸 Kamera oder Aufgabendatei",
        "uploader_label_notebook": "📸 Foto aufnehmen oder Heftdateien auswählen:",
        "expander_class": "🏫 Klassenauswahl & Verwaltung (Hier klicken)",
        "expander_lang": "🌐 UI-Sprache ändern (Hier klicken)",
        "current_class_label": "Aktuelle Klasse:",
        "change_class_label": "Klasse wechseln:",
        "no_students_yet": "Noch keine Schüler hinzugefügt.",
        "section_students_text": "Schüler der Klasse",
        "lang_select_label": "UI-Sprache / Language:",
        "box1_title": "🗂️ Feld 1: Automatische Hausaufgabenkorrektur",
        "box2_title": "🗂️ Feld 2: Klassenliste importieren",
        "box3_title": "🗂️ Feld 3: Fortschrittstabelle und Berichte",
        "view_photos_folder": "👁️ Ordnerfotos anzeigen",
        "clear_folder": "🗑️ Ordner leeren",
        "roster_photo_caption": "Listenfoto",
        "no_classes_warn": "⚠️ Keine Klassen verfügbar. Erstellen Sie eine Klasse in der Seitenleiste.",
        "catalog_spinner": "⏳ Die KI analysiert und ordnet die Klassenliste... (Dauert 1-2 Minuten)",
        "catalog_success": "✅ Klassenliste erfolgreich registriert!"
    },
    "中文 (Chinese)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *智能作业与测试批改助手*",
        "hw_section": "📖 作业题目照片",
        "hw_desc": "📸 拍摄或上传作业题目：",
        "hw_saved": "作业页面已保存！",
        "class_mgmt": "⚙️ 班级与分组管理",
        "select_class": "选择班级：",
        "add_new_class": "➕ 添加新班级：",
        "btn_add_class": "添加班级",
        "remove_class": "❌ 删除班级：",
        "btn_remove_class": "删除班级",
        "students_in": "班级学生",
        "add_student": "添加新学生：",
        "btn_add": "➕ 添加学生",
        "remove_student": "删除学生：",
        "btn_remove": "❌ 删除学生",
        "api_prompt": "输入 Google Gemini API 密钥",
        "save_api": "💾 保存 API 密钥",
        "api_saved_success": "API 密钥保存成功！",
        "menu_title": "📌 选择模式：",
        "opt1": "📷 1. 自动批改",
        "opt2": "📋 2. 导入花名册",
        "opt3": "📊 3. 进度表与报告",
        "notebook_sec": "✨ 拍摄并上传学生作业本",
        "no_hw_warn": "⚠️ 提示：您尚未拍摄作业题目照片。",
        "batch_upload": "📸 拍摄作业照片或选择文件：",
        "folder_found": "个学生作业本照片已准备就绪。",
        "btn_evaluate": "🚀 开始批改",
        "eval_success": "成功保存到进度表！",
        "view_eval": "🔍 查看最新评估",
        "catalog_sec": "📷 导入班级花名册",
        "upload_catalog": "📸 拍摄花名册照片或上传文件：",
        "btn_read_names": "🤖 读取并自动保存花名册",
        "stats_sec": "📊 班级进度矩阵 (Excel格式)",
        "btn_close_day": "🚨 标记今日未交作业学生",
        "manual_delete": "🗑️ 删除记录",
        "sidebar_stop_text": "🔴 重要提示：<br>向下滚动 👇<br>以选择班级。",
        "alert_box": "⚙️ 点击左上角的箭头 <span class=\"red-badge\">&gt;&gt;</span> 以管理班级和语言",
        "uploader_label_hw": "📸 相机或作业文件",
        "uploader_label_notebook": "📸 拍摄作业照片或选择文件：",
        "expander_class": "🏫 快速选择与班级管理（点击这里）",
        "expander_lang": "🌐 快速切换界面语言（点击这里）",
        "current_class_label": "当前班级：",
        "change_class_label": "更改班级：",
        "no_students_yet": "尚未添加学生。",
        "section_students_text": "班级学生",
        "lang_select_label": "界面语言 / Language:",
        "box1_title": "🗂️ 模块 1：自动作业批改",
        "box2_title": "🗂️ 模块 2：导入花名册",
        "box3_title": "🗂️ 模块 3：进度表与报告",
        "view_photos_folder": "👁️ 查看文件夹照片",
        "clear_folder": "🗑️ 清空文件夹",
        "roster_photo_caption": "花名册照片",
        "no_classes_warn": "⚠️ 暂无班级。请在侧边栏创建一个班级。",
        "catalog_spinner": "⏳ 智能AI正在分析和组织班级花名册... (大约需要 1-2 分钟)",
        "catalog_success": "✅ 班级花名册成功录入！"
    },
    "日本語 (Japanese)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *スマート宿題・テスト採点アシスタント*",
        "hw_section": "📖 宿題の問題写真",
        "hw_desc": "📸 カメラで撮影するか、問題のページをアップロード：",
        "hw_saved": "宿題のページが保存されました！",
        "class_mgmt": "⚙️ クラス・セクション管理",
        "select_class": "クラスを選択：",
        "add_new_class": "➕ 新しいクラスを追加：",
        "btn_add_class": "クラスを追加",
        "remove_class": "❌ クラスを削除：",
        "btn_remove_class": "クラスを削除",
        "students_in": "クラスの生徒",
        "add_student": "新しい生徒を追加：",
        "btn_add": "➕ 生徒を追加",
        "remove_student": "生徒を削除：",
        "btn_remove": "❌ 生徒を削除",
        "api_prompt": "Google Gemini APIキーを入力",
        "save_api": "💾 APIキーを保存",
        "api_saved_success": "APIキーが正常に保存されました！",
        "menu_title": "📌 モードを選択：",
        "opt1": "📷 1. 自動採点",
        "opt2": "📋 2. 名簿のインポート",
        "opt3": "📊 3. 進捗テーブルとレポート",
        "notebook_sec": "✨ 生徒のノートを撮影・アップロード",
        "no_hw_warn": "⚠️ 注意：宿題の問題写真が撮影されていません。",
        "batch_upload": "📸 ノートの写真を撮影またはファイルを選択：",
        "folder_found": "件のノート写真の準備ができました。",
        "btn_evaluate": "🚀 採点を開始",
        "eval_success": "進捗テーブルに正常に保存されました！",
        "view_eval": "🔍 最新の評価を表示",
        "catalog_sec": "📷 クラス名簿のインポート",
        "upload_catalog": "📸 名簿の写真を撮影またはファイルをアップロード：",
        "btn_read_names": "🤖 名簿を読み取って自動保存",
        "stats_sec": "📊 クラス進捗マトリックス",
        "btn_close_day": "🚨 本日の未提出者を記録",
        "manual_delete": "🗑️ データの削除",
        "sidebar_stop_text": "🔴 重要：<br>下にスクロール 👇<br>してクラスを選択してください。",
        "alert_box": "⚙️ 左上の矢印 <span class=\"red-badge\">&gt;&gt;</span> を押してクラスと言語を変更してください",
        "uploader_label_hw": "📸 カメラまたは宿題ファイル",
        "uploader_label_notebook": "📸 ノートの写真を撮影またはファイルを選択：",
        "expander_class": "🏫 クラスの選択と管理（ここをクリック）",
        "expander_lang": "🌐 UI言語の変更（ここをクリック）",
        "current_class_label": "現在のクラス：",
        "change_class_label": "クラスを変更：",
        "no_students_yet": "生徒はまだ追加されていません。",
        "section_students_text": "クラスの生徒",
        "lang_select_label": "UI言語 / Language:",
        "box1_title": "🗂️ ブロック 1：自動宿題採点",
        "box2_title": "🗂️ ブロック 2：名簿のインポート",
        "box3_title": "🗂️ ブロック 3：進捗テーブルとレポート",
        "view_photos_folder": "👁️ フォルダの写真を表示",
        "clear_folder": "🗑️ フォルダをクリア",
        "roster_photo_caption": "名簿の写真",
        "no_classes_warn": "⚠️ クラスがありません。サイドバーからクラスを作成してください。",
        "catalog_spinner": "⏳ AIがクラス名簿を分析・整理しています... (1〜2分かかります)",
        "catalog_success": "✅ クラス名簿が正常に登録されました！"
    }
}

# --- 3. SIDEBAR: ΔΙΑΧΕΙΡΙΣΗ ΤΜΗΜΑΤΩΝ & ΜΑΘΗΤΩΝ ---
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

# --- 4. ΚΥΡΙΩΣ ΠΕΡΙΕΧΟΜΕΝΟ & ΜΕΝΟΥ ---
st.markdown(f"""
    <div class="custom-alert-box">
        {t["alert_box"]}
    </div>
""", unsafe_allow_html=True)

if not students_db:
    st.info("👈 Please create at least one section from the left sidebar to get started.")
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
                    st.error("⚠️ Please enter your Gemini API Key first in settings or config!")
                else:
                    try:
                        with st.spinner(t["catalog_spinner"]):
                            client = genai.Client(api_key=api_key_val)
                            img_to_send = Image.open(catalog_path)
                            
                            prompt = (
                                "Look at this image containing a class roster or list of student names. "
                                "Extract all student names. Return ONLY a valid JSON list of strings, "
                                "where each string is a student's full name (e.g., [\"John Doe\", \"Maria Smith\"]). "
                                "Do not include any extra text, markdown formatting blocks like ```json, or explanations."
                            )
                            
                            response_text = call_gemini_with_retry(client, 'gemini-2.5-flash', [img_to_send, prompt])
                            
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
                        st.error(f"⚠️ Processing error: {str(e)}")

    elif mode == t["opt3"]:
        st.subheader(t["box3_title"])
        st.write(f"📊 {t['stats_sec']} - {selected_class}")
        if students_db[selected_class]:
            df_progress = pd.DataFrame({"Student": students_db[selected_class]})
            st.dataframe(df_progress, use_container_width=True)
        else:
            st.info(t["no_students_yet"])
