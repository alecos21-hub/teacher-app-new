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
        "mode_cam": "📷 Λήψη με Κάμερα (Πολλαπλές Σελίδες)",
        "mode_file": "📁 Επιλογή Αρχείων από Συλλογή",
        "how_many_pages": "Πόσες σελίδες θέλετε να φωτογραφίσετε για το τετράδιο;",
        "page_label": "Σελίδα",
        "snap_page": "📷 Φωτογραφίστε τη Σελίδα",
        "page_saved": "αποθηκεύτηκε!",
        "batch_upload": "📁 Μαζική επιλογή φωτογραφιών τετραδίων (πολλαπλή επιλογή)",
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
        "mode_cam": "📷 Camera Capture (Multiple Pages)",
        "mode_file": "📁 Upload Files from Gallery",
        "how_many_pages": "How many pages do you want to snap for this notebook?",
        "page_label": "Page",
        "snap_page": "📷 Snap Page",
        "page_saved": "saved!",
        "batch_upload": "📁 Batch select notebook photos (multiple selection)",
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
    },
    "Français": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Correcteur Intelligent de Devoirs – Assistant Enseignant*",
        "hw_section": "📖 Photos du Sujet du Devoir",
        "hw_desc": "Prenez en photo les pages du devoir :",
        "hw_pages": "Pages de Devoir :",
        "hw_cam": "📸 Devoir - Page",
        "hw_saved": "page(s) de devoir enregistrée(s)",
        "class_mgmt": "⚙️ Gestion de la Classe",
        "select_class": "Sélectionner la Classe :",
        "students_in": "Élèves de la Classe",
        "add_student": "Ajouter un nouvel élève :",
        "btn_add": "➕ Ajouter Élève",
        "remove_student": "Supprimer un élève :",
        "btn_remove": "❌ Supprimer Élève",
        "api_prompt": "Entrez la clé API Google Gemini",
        "tab1": "📷 Évaluation Automatique",
        "tab2": "📋 Importer la Liste",
        "tab3": "📊 Rapports et Absences",
        "notebook_sec": "✨ Prendre en Photo les Cahiers",
        "no_hw_warn": "⚠️ Remarque : Aucune photo de devoir n'a été prise dans le panneau latéral.",
        "input_mode": "Méthode d'introduction des cahiers :",
        "mode_cam": "📷 Capture Appareil Photo (Pages Multiples)",
        "mode_file": "📁 Sélectionner depuis la Galerie",
        "how_many_pages": "Combien de pages souhaitez-vous prendre en photo ?",
        "page_label": "Page",
        "snap_page": "📷 Prendre en Photo la Page",
        "page_saved": "enregistrée !",
        "batch_upload": "📁 Sélectionner plusieurs photos de cahiers",
        "batch_saved": "photos téléchargées avec succès !",
        "folder_found": "photos de cahiers d'élèves prêtes.",
        "btn_evaluate": "🚀 Lancer l'Évaluation des Cahiers",
        "eval_spinner": "🤖 L'IA analyse les pages et adapte le contenu...",
        "eval_success": "Enregistré dans les Rapports & dossier vidé !",
        "view_eval": "🔍 Voir l'Évaluation Détaillée",
        "catalog_sec": "📷 Importer la Liste d'Élèves",
        "upload_catalog": "Télécharger la photo de la liste",
        "btn_read_names": "🤖 Lire les Noms avec l'IA",
        "btn_save_names": "📥 Enregistrer les Noms dans la Classe",
        "stats_sec": "📊 Statistiques (Tableau Excel par Date)",
        "stats_info": "ℹ️ *Les enregistrements sont automatiquement supprimés après 7 jours.*",
        "btn_close_day": "🚨 Clôturer la Journée & Marquer les Devoirs Non Rendus",
        "manual_delete": "🗑️ Suppression Manuelle"
    },
    "Deutsch": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Intelligenter Hausaufgaben-Korrektor – Digitaler Lehrassistent*",
        "hw_section": "📖 Fotos der Aufgabenstellung",
        "hw_desc": "Fotografieren Sie die Aufgabenseiten:",
        "hw_pages": "Aufgabenseiten:",
        "hw_cam": "📸 Aufgabe - Seite",
        "hw_saved": "Aufgabenseite(n) gespeichert",
        "class_mgmt": "⚙️ Klassenverwaltung",
        "select_class": "Klasse auswählen:",
        "students_in": "Schüler in Klasse",
        "add_student": "Neuen Schüler hinzufügen:",
        "btn_add": "➕ Schüler Hinzufügen",
        "remove_student": "Schüler entfernen:",
        "btn_remove": "❌ Schüler Löschen",
        "api_prompt": "Google Gemini API-Schlüssel eingeben",
        "tab1": "📷 Automatische Korrektur",
        "tab2": "📋 Namensliste Importieren",
        "tab3": "📊 Berichte & Anwesenheit",
        "notebook_sec": "✨ Schülerhefte Fotografieren",
        "no_hw_warn": "⚠️ Hinweis: Sie haben keine Aufgabenstellung in der linken Leiste fotografiert.",
        "input_mode": "Eingabemethode für Schülerhefte:",
        "mode_cam": "📷 Kameraaufnahme (Mehrere Seiten)",
        "mode_file": "📁 Aus Galerie hochladen",
        "how_many_pages": "Wie viele Seiten möchten Sie für dieses Heft fotografieren?",
        "page_label": "Seite",
        "snap_page": "📷 Seite Fotografieren",
        "page_saved": "gespeichert!",
        "batch_upload": "📁 Mehrere Heftfotos auswählen",
        "batch_saved": "Fotos erfolgreich hochgeladen!",
        "folder_found": "Heftfotos bereit zur Auswertung.",
        "btn_evaluate": "🚀 Auswertung Starten",
        "eval_spinner": "🤖 KI analysiert die Seiten und passt Rückmeldungen an...",
        "eval_success": "Erfolgreich gespeichert & Ordner geleert!",
        "view_eval": "🔍 Detaillierte Auswertung Anzeigen",
        "catalog_sec": "📷 Klassenliste Importieren",
        "upload_catalog": "Foto der Klassenliste hochladen",
        "btn_read_names": "🤖 Namen mit KI Lesen",
        "btn_save_names": "📥 Namen Speichern",
        "stats_sec": "📊 Klassenstatistik (Excel-Tabelle nach Datum)",
        "stats_info": "ℹ️ *Einträge werden nach 7 Tagen automatisch gelöscht.*",
        "btn_close_day": "🚨 Tag Abschließen & Fehlende Aufgaben Markieren",
        "manual_delete": "🗑️ Manuelles Löschen"
    },
    "Español": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Corrector Inteligente de Tareas – Asistente Docente*",
        "hw_section": "📖 Fotos del Enunciado de la Tarea",
        "hw_desc": "Tome fotos de las páginas de la tarea:",
        "hw_pages": "Páginas de la tarea:",
        "hw_cam": "📸 Tarea - Página",
        "hw_saved": "página(s) de tarea guardada(s)",
        "class_mgmt": "⚙️ Gestión de la Clase",
        "select_class": "Seleccionar Clase:",
        "students_in": "Estudiantes en la Clase",
        "add_student": "Añadir nuevo estudiante:",
        "btn_add": "➕ Añadir Estudiante",
        "remove_student": "Eliminar estudiante:",
        "btn_remove": "❌ Eliminar Estudiante",
        "api_prompt": "Ingrese la clave API de Google Gemini",
        "tab1": "📷 Evaluación Automática",
        "tab2": "📋 Importar Lista",
        "tab3": "📊 Informes y Asistencia",
        "notebook_sec": "✨ Capturar Cuadernos de Estudiantes",
        "no_hw_warn": "⚠️ Nota: No ha tomado fotos del enunciado en el panel lateral.",
        "input_mode": "Método de entrada de cuadernos:",
        "mode_cam": "📷 Capturar con Cámara (Varias Páginas)",
        "mode_file": "📁 Seleccionar de la Galería",
        "how_many_pages": "¿Cuántas páginas desea fotografiar para este cuaderno?",
        "page_label": "Página",
        "snap_page": "📷 Fotografiar Página",
        "page_saved": "¡guardada!",
        "batch_upload": "📁 Selección múltiple de fotos de cuadernos",
        "batch_saved": "¡fotos subidas con éxito!",
        "folder_found": "fotos de cuadernos listas para evaluar.",
        "btn_evaluate": "🚀 Iniciar Evaluación",
        "eval_spinner": "🤖 La IA está analizando las páginas y adaptando los comentarios...",
        "eval_success": "¡Guardado en Informes y carpeta vaciada!",
        "view_eval": "🔍 Ver Evaluación Detallada",
        "catalog_sec": "📷 Importar Lista de Clase",
        "upload_catalog": "Subir foto de la lista",
        "btn_read_names": "🤖 Leer Nombres con IA",
        "btn_save_names": "📥 Guardar Nombres en la Clase",
        "stats_sec": "📊 Estadísticas (Tabla Excel por Fecha)",
        "stats_info": "ℹ️ *Los registros se eliminan automáticamente después de 7 días.*",
        "btn_close_day": "🚨 Cerrar Día y Marcar Tareas No Entregadas",
        "manual_delete": "🗑️ Eliminación Manual"
    },
    "Italiano": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Correttore Intelligente dei Compiti – Assistente Docente*",
        "hw_section": "📖 Foto della Traccia del Compito",
        "hw_desc": "Scatta foto alle pagine del compito:",
        "hw_pages": "Pagine del Compito:",
        "hw_cam": "📸 Compito - Pagina",
        "hw_saved": "pagina/e del compito salvata/e",
        "class_mgmt": "⚙️ Gestione Classe",
        "select_class": "Seleziona Classe:",
        "students_in": "Studenti della Classe",
        "add_student": "Aggiungi nuovo studente:",
        "btn_add": "➕ Aggiungi Studente",
        "remove_student": "Rimuovi studente:",
        "btn_remove": "❌ Elimina Studente",
        "api_prompt": "Inserisci la chiave API di Google Gemini",
        "tab1": "📷 Valutazione Automatica",
        "tab2": "📋 Importa Registro",
        "tab3": "📊 Report e Presenze",
        "notebook_sec": "✨ Scatta Foto ai Quaderni",
        "no_hw_warn": "⚠️ Nota: Non hai scattato foto della traccia del compito nella barra laterale.",
        "input_mode": "Metodo di inserimento quaderni:",
        "mode_cam": "📷 Scatta con Fotocamera (Pagine Multiple)",
        "mode_file": "📁 Seleziona dalla Galleria",
        "how_many_pages": "Quante pagine vuoi fotografare per questo quaderno?",
        "page_label": "Pagina",
        "snap_page": "📷 Scatta Foto alla Pagina",
        "page_saved": "salvata!",
        "batch_upload": "📁 Selezione multipla foto quaderni",
        "batch_saved": "foto caricate con successo!",
        "folder_found": "foto quaderni pronte per la valutazione.",
        "btn_evaluate": "🚀 Avvia Valutazione",
        "eval_spinner": "🤖 L'IA sta analizzando le pagine e adattando il feedback...",
        "eval_success": "Salvato nei Report e cartella svuotata!",
        "view_eval": "🔍 Visualizza Valutazione Dettagliata",
        "catalog_sec": "📷 Importa Registro Classe",
        "upload_catalog": "Carica foto del registro",
        "btn_read_names": "🤖 Leggi Nomi con IA",
        "btn_save_names": "📥 Salva Nomi nella Classe",
        "stats_sec": "📊 Statistiche (Tabella Excel per Data)",
        "stats_info": "ℹ️ *I dati vengono eliminati automaticamente dopo 7 giorni.*",
        "btn_close_day": "🚨 Chiudi Giornata e Segna Compiti Mancanti",
        "manual_delete": "🗑️ Eliminazione Manuale"
    },
    "Русский": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Интеллектуальная проверка домашних заданий – Цифровой помощник учителя*",
        "hw_section": "📖 Фотографии задания",
        "hw_desc": "Сделайте снимки страниц с заданием:",
        "hw_pages": "Страниц задания:",
        "hw_cam": "📸 Задание - Страница",
        "hw_saved": "страница(ы) задания сохранены",
        "class_mgmt": "⚙️ Управление классом",
        "select_class": "Выберите класс:",
        "students_in": "Ученики класса",
        "add_student": "Добавить нового ученика:",
        "btn_add": "➕ Добавить ученика",
        "remove_student": "Удалить ученика:",
        "btn_remove": "❌ Удалить ученика",
        "api_prompt": "Введите API-ключ Google Gemini",
        "tab1": "📷 Автоматическая проверка",
        "tab2": "📋 Импорт списка класса",
        "tab3": "📊 Отчеты и посещаемость",
        "notebook_sec": "✨ Съемка тетрадей учеников",
        "no_hw_warn": "⚠️ Примечание: Вы не сделали фото задания на боковой панели.",
        "input_mode": "Способ загрузки тетрадей:",
        "mode_cam": "📷 Съемка на камеру (несколько страниц)",
        "mode_file": "📁 Выбрать из галереи",
        "how_many_pages": "Сколько страниц нужно сфотографировать для этой тетради?",
        "page_label": "Страница",
        "snap_page": "📷 Сфотографировать страницу",
        "page_saved": "сохранена!",
        "batch_upload": "📁 Пакетный выбор фото тетрадей (множественный выбор)",
        "batch_saved": "фотографий успешно загружено!",
        "folder_found": "фото тетрадей готовы к проверке.",
        "btn_evaluate": "🚀 Начать проверку",
        "eval_spinner": "🤖 ИИ анализирует страницы и формирует отзыв...",
        "eval_success": "Успешно сохранено и папка очищена!",
        "view_eval": "🔍 Посмотреть подробный отчет",
        "catalog_sec": "📷 Импорт списка класса",
        "upload_catalog": "Загрузить фото списка",
        "btn_read_names": "🤖 Распознать имена с помощью ИИ",
        "btn_save_names": "📥 Сохранить имена в класс",
        "stats_sec": "📊 Статистика (Таблица Excel по датам)",
        "stats_info": "ℹ️ *Записи автоматически удаляются через 7 дней.*",
        "btn_close_day": "🚨 Завершить день и отметить не сдавших",
        "manual_delete": "🗑️ Ручное удаление записи"
    },
    "中文 (Chinese)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *Smart Homework & Test Grader – 智能教师助手*",
        "hw_section": "📖 题目与作业照片",
        "hw_desc": "拍摄作业题目页面：",
        "hw_pages": "作业页数：",
        "hw_cam": "📸 作业题目 - 第",
        "hw_saved": "页作业题目已保存",
        "class_mgmt": "⚙️ 班级管理",
        "select_class": "选择班级：",
        "students_in": "班级学生",
        "add_student": "添加新学生：",
        "btn_add": "➕ 添加学生",
        "remove_student": "删除学生：",
        "btn_remove": "❌ 删除学生",
        "api_prompt": "请输入 Google Gemini API Key",
        "tab1": "📷 自动批改",
        "tab2": "📋 导入花名册",
        "tab3": "📊 报告与考勤",
        "notebook_sec": "✨ 拍摄学生作业本",
        "no_hw_warn": "⚠️ 注意：您尚未从左侧栏拍摄作业题目照片。",
        "input_mode": "学生作业本输入方式：",
        "mode_cam": "📷 拍照（多页）",
        "mode_file": "📁 从相册批量上传",
        "how_many_pages": "该作业本要拍摄多少页？",
        "page_label": "页",
        "snap_page": "📷 拍摄第",
        "page_saved": "页已保存！",
        "batch_upload": "📁 批量选择作业本照片（可多选）",
        "batch_saved": "张照片已成功上传！",
        "folder_found": "张学生作业照片准备就绪。",
        "btn_evaluate": "🚀 开始批量批改",
        "eval_spinner": "🤖 AI 正在分析页面并生成反馈...",
        "eval_success": "成功保存到报告并已清空文件夹！",
        "view_eval": "🔍 查看详细评估（进度）",
        "catalog_sec": "📷 导入班级花名册：",
        "upload_catalog": "上传花名册照片",
        "btn_read_names": "🤖 AI 识别姓名",
        "btn_save_names": "📥 保存姓名到班级",
        "stats_sec": "📊 班级统计（按日期 Excel 表格）：",
        "stats_info": "ℹ️ *记录将在 7 天后自动删除。*",
        "btn_close_day": "🚨 结业登记 & 标记未交作业学生",
        "manual_delete": "🗑️ 手动删除记录"
    },
    "日本語 (Japanese)": {
        "title": "🎓 GradeMind AI",
        "subtitle": "### *スマート宿題＆テスト採点 – AI教員アシスタント*",
        "hw_section": "📖 宿題・問題の写真",
        "hw_desc": "宿題の問題ページを撮影してください：",
        "hw_pages": "問題のページ数：",
        "hw_cam": "📸 宿題 - ページ",
        "hw_saved": "ページの問題画像を保存しました",
        "class_mgmt": "⚙️ クラス管理",
        "select_class": "クラスを選択：",
        "students_in": "クラスの生徒一覧",
        "add_student": "新しい生徒を追加：",
        "btn_add": "➕ 生徒を追加",
        "remove_student": "生徒を削除：",
        "btn_remove": "❌ 生徒を削除",
        "api_prompt": "Google Gemini APIキーを入力してください",
        "tab1": "📷 自動採点",
        "tab2": "📋 名簿インポート",
        "tab3": "📊 レポート＆出席",
        "notebook_sec": "✨ 生徒のノートを撮影",
        "no_hw_warn": "⚠️ 注意：サイドバーから宿題の問題写真を撮影していません。",
        "input_mode": "ノートの入力方法：",
        "mode_cam": "📷 カメラで撮影（複数ページ）",
        "mode_file": "📁 ギャラリーから一括選択",
        "how_many_pages": "このノートは何ページ撮影しますか？",
        "page_label": "ページ",
        "snap_page": "📷 ページを撮影",
        "page_saved": "を保存しました！",
        "batch_upload": "📁 ノート写真を一括選択（複数選択可）",
        "batch_saved": "枚の写真をアップロードしました！",
        "folder_found": "枚のノート写真の準備が完了しました。",
        "btn_evaluate": "🚀 一括採点を開始",
        "eval_spinner": "🤖 AIがページを解析してフィードバックを作成中...",
        "eval_success": "レポートに保存し、フォルダを消去しました！",
        "view_eval": "🔍 詳細な評価を表示",
        "catalog_sec": "📷 クラス名簿をインポート",
        "upload_catalog": "名簿写真をアップロード",
        "btn_read_names": "🤖 AIで名前を読み取る",
        "btn_save_names": "📥 名前をクラスに保存",
        "stats_sec": "📊 クラス統計（日付別Excelテーブル）",
        "stats_info": "ℹ️ *記録は7日後に自動的に削除されます。*",
        "btn_close_day": "🚨 本日の締め切り＆未提出者を記録",
        "manual_delete": "🗑️ 手動で記録を削除"
    }
}

# --- 3. SIDEBAR: ΕΠΙΛΟΓΗ ΓΛΩΣΣΑΣ & ΔΙΑΧΕΙΡΙΣΗ ---
st.sidebar.header("🌐 App Language / Γλώσσα")
app_lang = st.sidebar.selectbox("Choose UI Language:", list(TRANSLATIONS.keys()), index=0)
t = TRANSLATIONS[app_lang]

st.markdown(t["title"])
st.markdown(t["subtitle"])

st.sidebar.markdown("---")
st.sidebar.header(t["hw_section"])
st.sidebar.write(t["hw_desc"])

hw_pages_num = st.sidebar.number_input(t["hw_pages"], min_value=1, max_value=5, value=1, step=1)

homework_images = []
for h_idx in range(int(hw_pages_num)):
    hw_cam = st.sidebar.camera_input(f"{t['hw_cam']} {h_idx+1}", key=f"hw_cam_{h_idx}")
    if hw_cam:
        hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{h_idx}.jpg")
        with open(hw_path, "wb") as f:
            f.write(hw_cam.getbuffer())
        homework_images.append(Image.open(hw_path))

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
                [t["mode_cam"], t["mode_file"]],
                key="input_mode_radio"
            )

            if input_mode == t["mode_cam"]:
                num_pages = st.number_input(t["how_many_pages"], min_value=1, max_value=5, value=2, step=1)
                
                for p_idx in range(int(num_pages)):
                    st.write(f"**{t['page_label']} {p_idx+1}:**")
                    cam_file = st.camera_input(f"{t['snap_page']} {p_idx+1}", key=f"student_cam_{p_idx}")
                    if cam_file:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_path = os.path.join(UPLOAD_FOLDER, f"student_cam_p{p_idx+1}_{timestamp}.jpg")
                        with open(file_path, "wb") as f:
                            f.write(cam_file.getbuffer())
                        st.success(f"✅ {t['page_label']} {p_idx+1} {t['page_saved']}")

            else:
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
                    
                    # Δημιουργία πίνακα τύπου Excel (Pivot Table)
                    # Γραμμές: Μαθητής, Στήλες: Ημερομηνία, Τιμές: Ποσοστό
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
