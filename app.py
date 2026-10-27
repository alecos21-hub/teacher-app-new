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
    return {"Α1": [], "Α2": [], "Β1": [], "Β2": [], "Γ1": [], "Γ2": []}

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
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.<br><span style='font-size: 11px; font-weight: normal;'>(Scroll down to select Department)</span>"
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
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.<br><span style='font-size: 11px; font-weight: normal;'>(Κάντε scroll κάτω για Τμήμα)</span>"
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
        "sidebar_stop_text": "🔴 ВАЖНО:<br>Прокрутите вниз 👇<br>для выбора класса."
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
        "sidebar_stop_text": "🔴 IMPORTANT :<br>Faites défiler vers le bas 👇<br>pour choisir la classe."
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
        "sidebar_stop_text": "🔴 IMPORTANTE:<br>Scorri verso il basso 👇<br>per selezionare la classe."
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
        "sidebar_stop_text": "🔴 WICHTIG:<br>Nach unten scrollen 👇<br>um die Klasse auszuwählen."
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
        "sidebar_stop_text": "🔴 重要提示：<br>向下滚动 👇<br>以选择班级。"
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
        "sidebar_stop_text": "🔴 重要：<br>下にスクロール 👇<br>してクラスを選択してください。"
    }
}

# --- 3. SIDEBAR: ΔΙΑΧΕΙΡΙΣΗ ΤΜΗΜΑΤΩΝ & ΜΑΘΗΤΩΝ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
app_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=0, key="sidebar_lang_select")
t = TRANSLATIONS.get(app_lang, TRANSLATIONS["Ελληνικά"])

st.markdown(t["title"])
st.markdown(t["subtitle"])

st.sidebar.markdown("---")
st.sidebar.header(t["hw_section"])
st.sidebar.write(t["hw_desc"])

hw_files = st.sidebar.file_uploader(
    "📸 Κάμερα ή Αρχείο Εκφώνησης",
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

# Κόκκινο πλαίσιο-στοπ ακριβώς κάτω από το upload στο sidebar για τα κινητά
st.sidebar.markdown(f"""
    <div class="sidebar-stop-box">
        {t["sidebar_stop_text"]}
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar
