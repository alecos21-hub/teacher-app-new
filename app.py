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
        "sidebar_stop_text": "🔴 ΣΗΜΑΝΤΙΚΟ:<br>Κάντε scroll προς τα κάτω 👇<br>για να επιλέξετε Τμήμα.<br><span style='font-size: 11px; font-weight: normal;'>(Scroll down to select Department)</span>",
        "alert_box": "⚙️ Πατήστε τα βελάκια <span class=\"red-badge\">&gt;&gt;</span> πάνω αριστερά για Τμήματα &amp; Γλώσσα"
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
        "sidebar_stop_text": "🔴 IMPORTANT:<br>Scroll down 👇<br>to select Department.<br><span style='font-size: 11px; font-weight: normal;'>(Κάντε scroll κάτω για Τμήμα)</span>",
        "alert_box": "⚙️ Press the arrows <span class=\"red-badge\">&gt;&gt;</span> top left for Sections &amp; Language"
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
        "sidebar_stop_text": "🔴 ВАЖНО:<br>Прокрутите вниз 👇<br>для выбора класса.",
        "alert_box": "⚙️ Нажмите стрелки <span class=\"red-badge\">&gt;&gt;</span> вверху слева для классов и языка"
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
        "sidebar_stop_text": "🔴 IMPORTANT :<br>Faites défiler vers le bas 👇<br>pour choisir la classe.",
        "alert_box": "⚙️ Appuyez sur les flèches <span class=\"red-badge\">&gt;&gt;</span> en haut à gauche pour les classes et la langue"
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
        "sidebar_stop_text": "🔴 IMPORTANTE:<br>Scorri verso il basso 👇<br>per selezionare la classe.",
        "alert_box": "⚙️ Premi le frecce <span class=\"red-badge\">&gt;&gt;</span> in alto a sinistra per classi e lingua"
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
        "sidebar_stop_text": "🔴 WICHTIG:<br>Nach unten scrollen 👇<br>um die Klasse auszuwählen.",
        "alert_box": "⚙️ Drücken Sie die Pfeile <span class=\"red-badge\">&gt;&gt;</span> oben links für Klassen und Sprache"
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
        "sidebar_stop_text": "🔴 重要提示：<br>向下滚动 👇<br>以选择班级。",
        "alert_box": "⚙️ 点击左上角的箭头 <span class=\"red-badge\">&gt;&gt;</span> 以管理班级和语言"
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
        "sidebar_stop_text": "🔴 重要：<br>下にスクロール 👇<br>してクラスを選択してください。",
        "alert_box": "⚙️ 左上の矢印 <span class=\"red-badge\">&gt;&gt;</span> を押してクラスと言語を変更してください"
    }
}

# --- 3. SIDEBAR: ΔΙΑΧΕΙΡΙΣΗ ΤΜΗΜΑΤΩΝ & ΜΑΘΗΤΩΝ ---
if "app_lang" not in st.session_state:
    st.session_state["app_lang"] = "Ελληνικά"

st.sidebar.header("🌐 App Language / Γλώσσα")
selected_sidebar_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=list(TRANSLATIONS.keys()).index(st.session_state["app_lang"]), key="sidebar_lang_select")
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
    if n_class and n_class not in students_db:
        students_db[n_class] = []
        save_students(students_db)
        st.sidebar.success(f"Δημιουργήθηκε το τμήμα: {n_class}")
        st.session_state["selected_class"] = n_class
        st.rerun()

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
        
        st.markdown(f'''
            <div class="custom-alert-box">
                {t["alert_box"]}
            </div>
        ''', unsafe_allow_html=True)
        
        with st.expander("🏫 Γρήγορη Επιλογή & Διαχείριση Τμήματος (Πατήστε εδώ)", expanded=False):
            st.write(f"**Τρέχον Τμήμα:** `{selected_class}`")
            quick_class = st.selectbox("Αλλαγή Τμήματος:", list(students_db.keys()), index=list(students_db.keys()).index(selected_class) if selected_class in students_db else 0, key="quick_class_sel")
            if quick_class != selected_class:
                st.session_state["selected_class"] = quick_class
                st.rerun()
            
            st.write(f"👥 **Μαθητές τμήματος {selected_class}:** {', '.join(students_db[selected_class]) if students_db[selected_class] else 'Δεν έχουν προστεθεί μαθητές ακόμα.'}")

        with st.expander("🌐 Γρήγορη Αλλαγή Γλώσσας UI (Πατήστε εδώ)", expanded=False):
            quick_lang = st.selectbox("Επιλογή Γλώσσας / Language:", list(TRANSLATIONS.keys()), index=list(TRANSLATIONS.keys()).index(app_lang), key="quick_lang_sel")
            if quick_lang != app_lang:
                st.session_state["app_lang"] = quick_lang
                st.rerun()

        st.markdown("---")
        
        selected_mode = st.radio(
            t["menu_title"], 
            [t["opt1"], t["opt2"], t["opt3"]],
            horizontal=False
        )
        st.markdown("---")

        if selected_mode == t["opt1"]:
            st.markdown("### 🗂️ Κουτάκι 1: Αυτόματη Αξιολόγηση Άσκησης")
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

            folder_files = []
            for f in os.listdir(UPLOAD_FOLDER):
                if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('hw_page_'):
                    f_path = os.path.join(UPLOAD_FOLDER, f)
                    try:
                        img_check = Image.open(f_path)
                        img_check.verify()
                        folder_files.append(f_path)
                    except Exception:
                        pass

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
                            }
                        } catch (err) {}
                    }
                    requestWakeLock();
                    </script>
                    """
                    components.html(wake_lock_code, height=0)
                    
                    st.info("💡 Σημείωση / Note...")
                    
                    batch_images = []
                    for f_path in folder_files:
                        try:
                            batch_images.append(Image.open(f_path))
                        except Exception:
                            pass
                    
                    known_students_str = ", ".join(students_db[selected_class])
                    prompt = f"""
                    You are an expert teacher grading student exercises.
                    I attached high-resolution images of student notebook pages.
                    Evaluate EACH student found in these images individually.

                    1. **MULTI-PAGE HANDLING**: If a student's work spans across multiple pages/images, combine all their pages together and output a SINGLE unified score and evaluation for that student.
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
                    except Exception as api_err:
                        eval_res = None
                        st.error(f"⚠️ API Error: {api_err}")

                    if not eval_res:
                        st.error("⚠️ Connection error. Please try again.")
                        st.stop()

                    full_eval_res = eval_res
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
                            if line_str.startswith("Όνομα:") or line_str.startswith("Name:"):
                                d_name = line_str.split(":", 1)[1].strip()
                            elif line_str.startswith("Ποσοστό:") or line_str.startswith("Score:"):
                                d_score = line_str.split(":", 1)[1].strip()
                        
                        d_name = d_name.replace("*", "").strip().replace("/", "-")
                        d_score = d_score.replace("*", "").strip()

                        if d_name != "Άγνωστος" and d_name != "Unknown":
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

        elif selected_mode == t["opt2"]:
            st.markdown("### 🗂️ Κουτάκι 2: Εισαγωγή Καταλόγου")
            st.subheader(f"{t['catalog_sec']} – {selected_class}")
            
            list_img_file = st.file_uploader(t["upload_catalog"], type=["png", "jpg", "jpeg"], key="list_up")
            if list_img_file:
                list_path = os.path.join(UPLOAD_FOLDER, list_img_file.name)
                with open(list_path, "wb") as f:
                    f.write(list_img_file.getbuffer())
                list_img = Image.open(list_path)
                
                st.image(list_img, caption="Φωτογραφία Καταλόγου", use_column_width=True)
                
                if st.button(t["btn_read_names"], type="primary"):
                    with st.spinner("🤖 AI..."):
                        p_list = "Read all student names from this roster photo carefully. Return ONLY a comma-separated list of the full names. Do not add any extra text or numbers."
                        
                        try:
                            raw_text_res = call_gemini_with_retry(client, 'gemini-3.8-flash', [p_list, list_img])
                            raw_text = raw_text_res.strip() if raw_text_res else ""
                        except Exception:
                            raw_text = ""
                        
                        if not raw_text:
                            st.error("⚠️ Error reading roster. Please try again.")
                            st.stop()
                        
                        names_found = [n.strip().replace("\n", "").replace("-", "") for n in raw_text.split(",") if n.strip()]
                        
                        added_count = 0
                        for n in names_found:
                            if n and n not in students_db[selected_class]:
                                students_db[selected_class].append(n)
                                added_count += 1
                        
                        students_db[selected_class].sort()
                        save_students(students_db)
                        
                        st.success(f"🎉 {added_count} names added successfully!")
                        st.write("📋 **Names:**", names_found)
                        st.rerun()

        elif selected_mode == t["opt3"]:
            st.markdown("### 🗂️ Κουτάκι 3: Πίνακας Προόδου & Αναφορές")
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
                    st.success("Missing records saved!")
                    st.rerun()
                else:
                    st.info("All students evaluated!")

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

                    st.markdown("### 📋 Progress Matrix")
                    st.dataframe(pivot_df, use_container_width=True)

                    st.markdown("---")
                    st.subheader("🗑️ Management")
                    
                    col_d1, col_d2 = st.columns(2)
                    
                    with col_d1:
                        available_dates = df_class["Ημερομηνία"].unique().tolist()
                        selected_date_to_delete = st.selectbox("Date to delete:", ["-- Select --"] + available_dates)
                        if st.button("🚨 Delete Date"):
                            if selected_date_to_delete != "-- Select --":
                                df_all = df_all[~((df_all["Ημερομηνία"] == selected_date_to_delete) & (df_all["Τμήμα"] == selected_class))]
                                df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                                st.success("Deleted!")
                                st.rerun()

                    with col_d2:
                        options_to_delete = ["-- Select entry --"]
                        indices_map = {}
                        for idx, row in df_class.iterrows():
                            label = f"{row['Ημερομηνία']} | {row['Μαθητής']} | {row['Ποσοστό']}"
                            options_to_delete.append(label)
                            indices_map[label] = idx

                        selected_del = st.selectbox("Single entry:", options_to_delete)
                        if st.button("🗑️ Delete Selected"):
                            if selected_del != "-- Select entry --":
                                target_idx = indices_map[selected_del]
                                df_all = df_all.drop(target_idx)
                                df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                                st.success("Deleted!")
                                st.rerun()
                else:
                    st.info(f"No records for section {selected_class}.")
            else:
                st.info("No grades file found.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.warning("Please enter and save your API Key to continue.")
