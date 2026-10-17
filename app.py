import streamlit as st
from google import genai
from PIL import Image
import pandas as pd
import datetime
import os
import json

st.set_page_config(page_title="Πλήρες Σύστημα Διαχείρισης Τάξης & Ασκήσεων", layout="wide")

st.markdown("# 📚 Ψηφιακός Βοηθός Τάξης & Αυτόματη Αξιολόγηση")

# Αρχεία αποθήκευσης
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
    """Διαγράφει αυτόματα εγγραφές παλαιότερες των 7 ημερών"""
    if os.path.exists(GRADES_FILE):
        try:
            df = pd.read_csv(GRADES_FILE)
            if not df.empty and "Ημερομηνία" in df.columns:
                df["Ημερομηνία_dt"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
                cutoff_date = pd.Timestamp(datetime.date.today() - datetime.timedelta(days=7))
                df_filtered = df[df["Ημερομηνία_dt"] >= cutoff_date].drop(columns=["Ημερομηνία_dt"])
                df_filtered.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
        except Exception as e:
            pass

clean_old_records()
students_db = load_students()

# --- SIDEBAR: ΦΩΤΟΓΡΑΦΙΕΣ HOMEWORK & ΔΙΑΧΕΙΡΙΣΗ ΤΑΞΗΣ ---
st.sidebar.markdown("---")
st.sidebar.header("📖 Φωτογραφίες Homework")
st.sidebar.write("Τραβήξτε τις σελίδες της εκφώνησης (Homework):")

hw_pages_num = st.sidebar.number_input("Σελίδες Homework:", min_value=1, max_value=5, value=1, step=1)

homework_images = []
for h_idx in range(int(hw_pages_num)):
    hw_cam = st.sidebar.camera_input(f"📸 Homework - Σελίδα {h_idx+1}", key=f"hw_cam_{h_idx}")
    if hw_cam:
        homework_images.append(Image.open(hw_cam))

if homework_images:
    st.sidebar.success(f"✅ {len(homework_images)} σελίδα/σελίδες Homework Καταγράφηκαν")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Διαχείριση Τάξης")
selected_class = st.sidebar.selectbox("Επιλογή Τμήματος:", list(students_db.keys()))

st.sidebar.subheader(f"Μαθητές Τμήματος {selected_class}")
new_student = st.sidebar.text_input("Προσθήκη νέου μαθητή:")
if st.sidebar.button("➕ Προσθήκη Μαθητή"):
    if new_student and new_student not in students_db[selected_class]:
        students_db[selected_class].append(new_student)
        students_db[selected_class].sort()
        save_students(students_db)
        st.sidebar.success(f"Προστέθηκε ο/η {new_student}")
        st.rerun()

student_to_remove = st.sidebar.selectbox("Αφαίρεση μαθητή:", ["-- Επιλέξτε --"] + students_db[selected_class])
if st.sidebar.button("❌ Διαγραφή Μαθητή"):
    if student_to_remove != "-- Επιλέξτε --":
        students_db[selected_class].remove(student_to_remove)
        save_students(students_db)
        st.sidebar.warning(f"Αφαιρέθηκε ο/η {student_to_remove}")
        st.rerun()

# --- ΚΥΡΙΩΣ ΜΕΡΟΣ ---
api_key = st.text_input("Εισάγετε Google Gemini API Key", type="password")

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        
        tab1, tab2, tab3 = st.tabs(["📷 Αυτόματη Αξιολόγηση Άσκησης", "📋 Εισαγωγή Καταλόγου", "📊 Αναφορές & Απουσίες"])

        # TAB 1: ΑΥΤΟΜΑΤΗ ΑΞΙΟΛΟΓΗΣΗ ΑΣΚΗΣΗΣ
        with tab1:
            st.subheader("✨ Πλήρως Αυτόματη Αξιολόγηση Ασκήσεων (Live)")
            
            if not homework_images:
                st.warning("⚠️ Σημείωση: Δεν έχετε τραβήξει φωτογραφία Homework από την αριστερή στήλη.")

            option = st.radio("Τρόπος Εισαγωγής Τετραδίου:", ["📷 Κάμερα (Βήμα-Βήμα Σελίδες)", "📁 Πολλαπλά Αρχεία από Συλλογή"], key="exercise_opt")
            
            student_images = []

            if option == "📷 Κάμερα (Βήμα-Βήμα Σελίδες)":
                num_pages = st.number_input("Πόσες σελίδες είναι το τετράδιο του μαθητή;", min_value=1, max_value=5, value=1, step=1)
                
                for i in range(int(num_pages)):
                    cam_file = st.camera_input(f"📷 Κάμερα - Σελίδα {i+1} (το όνομα να φαίνεται κάπου)", key=f"cam_page_{i}")
                    if cam_file:
                        student_images.append(Image.open(cam_file))
            else:
                up_files = st.file_uploader("Ανεβάστε όλες τις φωτογραφίες των σελίδων μαζί", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="up_ex_multi")
                if up_files:
                    for uf in up_files:
                        student_images.append(Image.open(uf))

            if student_images:
                img_key = f"{len(student_images)}_{selected_class}"
                
                if "last_processed_key" not in st.session_state or st.session_state["last_processed_key"] != img_key:
                    with st.spinner("🤖 Η AI αναλύει αυτόματα τις σελίδες, το όνομα και το ποσοστό..."):
                        known_students_str = ", ".join(students_db[selected_class])
                        
                        prompt = f"""
                        Είσαι έμπειρος εκπαιδευτικός. 
                        Έχω επισυνάψει τις εικόνες από την εκφώνηση της άσκησης (Homework) καθώς και τις σελίδες του τετραδίου του μαθητή.
                        Σε μία από τις σελίδες του τετραδίου, ο μαθητής έχει γράψει το όνομά του.
                        Οι εγγεγραμμένοι μαθητές του τμήματος {selected_class} είναι: [{known_students_str}].

                        Παρακαλώ εκτέλεσε τα εξής:
                        1. **ΟΝΟΜΑ ΜΑΘΗΤΗ**: Βρες ποιο όνομα αναγράφεται στις φωτογραφίες και ταύτισέ το με τη λίστα.
                        2. **ΠΟΣΟΣΤΟ ΕΠΙΤΥΧΙΑΣ**: Δώσε ένα συνολικό ποσοστό % (π.χ. 85%). Αν η άσκηση είναι εντελώς λάθος, δώσε 0%.
                        3. **ΑΝΑΛΥΣΗ ΔΙΑΔΙΚΑΣΙΑΣ**: Σύγκρινε ολόκληρη τη λύση με το Homework, εντόπισε τα ενδιάμεσα βήματα και τη λογική.
                        4. **ΣΧΟΛΙΑ**: Δώσε αναλυτικές οδηγίες διόρθωσης.

                        Δώσε την απάντηση αυστηρά με αυτή τη δομή:
                        Όνομα: [Όνομα Μαθητή]
                        Ποσοστό: [X%]
                        Ανάλυση: [Κείμενο]
                        """

                        contents_list = [prompt] + student_images
                        if homework_images:
                            contents_list += homework_images

                        response = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=contents_list
                        )
                        
                        eval_res = response.text

                        detected_name = "Άγνωστος"
                        detected_score = "0%"
                        for line in eval_res.split('\n'):
                            if line.startswith("Όνομα:"):
                                detected_name = line.replace("Όνομα:", "").strip()
                            elif line.startswith("Ποσοστό:"):
                                detected_score = line.replace("Ποσοστό:", "").strip()

                        today = datetime.date.today().strftime("%Y-%m-%d")
                        new_row = {
                            "Ημερομηνία": today,
                            "Τμήμα": selected_class,
                            "Μαθητής": detected_name,
                            "Ποσοστό": detected_score,
                            "Κατάσταση": "Ελέγχθηκε",
                            "Αξιολόγηση": eval_res
                        }

                        df_new = pd.DataFrame([new_row])
                        if os.path.exists(GRADES_FILE):
                            df_ex = pd.read_csv(GRADES_FILE)
                            df_updated = pd.concat([df_ex, df_new], ignore_index=True)
                        else:
                            df_updated = df_new
                        
                        df_updated.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')

                        st.session_state["last_processed_key"] = img_key
                        st.session_state["current_name"] = detected_name
                        st.session_state["current_score"] = detected_score
                        st.session_state["current_eval"] = eval_res
                        st.session_state["current_date"] = today

            if "current_score" in st.session_state:
                curr_name = st.session_state["current_name"]
                curr_score = st.session_state["current_score"]
                curr_eval = st.session_state["current_eval"]
                curr_date = st.session_state["current_date"]

                st.success(f"✅ Εντοπίστηκε Μαθητής: **{curr_name}**")
                
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; text-align: center; border: 2px solid #4CAF50;">
                    <h2 style="color: #2e7d32; margin:0;">🏆 Ποσοστό Επιτυχίας: {curr_score}</h2>
                    <p style="color: #555; margin-top: 5px;">Η βαθμολογία αποθηκεύτηκε αυτόματα στην ημερομηνία {curr_date}.</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("✏️ Διόρθωση Ονόματος (Αν η AI διάβασε λάθος τα γράμματα)")
                
                correct_name = st.selectbox(
                    "Επιλέξτε τον σωστό μαθητή από τη λίστα:",
                    ["-- Επιλέξτε αν χρειάζεται διόρθωση --"] + students_db[selected_class],
                    key="fix_name_select"
                )

                if st.button("💾 Ενημέρωση & Διόρθωση Ονόματος"):
                    if correct_name != "-- Επιλέξτε αν χρειάζεται διόρθωση --":
                        df_corr = pd.read_csv(GRADES_FILE)
                        df_corr.iloc[-1, df_corr.columns.get_loc("Μαθητής")] = correct_name
                        df_corr.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                        
                        st.session_state["current_name"] = correct_name
                        st.success(f"✅ Το όνομα διορθώθηκε αμέσως σε **{correct_name}**!")
                        st.rerun()

                with st.expander("🔍 Προβολή Αναλυτικής Αξιολόγησης (Πρόοδος)"):
                    st.markdown(curr_eval)

        # TAB 2: ΕΙΣΑΓΩΓΗ ΚΑΤΑΛΟΓΟΥ (ΜΕ ΕΠΙΛΟΓΗ ΚΑΜΕΡΑΣ Ή ΑΡΧΕΙΟΥ)
        with tab2:
            st.subheader(f"📷 Εισαγωγή Καταλόγου για το Τμήμα {selected_class}")
            
            list_option = st.radio("Τρόπος εισαγωγής καταλόγου:", ["📸 Λήψη Φωτογραφίας με Κάμερα", "📁 Επιλογή Αρχείου από Συλλογή"], key="list_source_opt")
            
            list_img = None
            if list_option == "📸 Λήψη Φωτογραφίας με Κάμερα":
                cam_list_file = st.camera_input("📸 Τραβήξτε φωτογραφία τον κατάλογο της τάξης", key="list_cam_input")
                if cam_list_file:
                    list_img = Image.open(cam_list_file)
            else:
                list_img_file = st.file_uploader("Ανεβάστε φωτογραφία καταλόγου", type=["png", "jpg", "jpeg"], key="list_up")
                if list_img_file:
                    list_img = Image.open(list_img_file)
            
            if list_img:
                st.image(list_img, caption="Φωτογραφία Καταλόγου", use_column_width=True)
                
                if st.button("🤖 Ανάγνωση Ονομάτων από AI"):
                    with st.spinner("Η AI διαβάζει τα ονόματα..."):
                        p_list = "Διάβασε προσεκτικά τους μαθητές και τα ονόματά τους από τη φωτογραφία του καταλόγου. Επίστρεψέ τα ως απλή λίστα χωρισμένη αποκλειστικά με κόμματα (π.χ. Όνομα1, Όνομα2, Όνομα3)."
                        res_list = client.models.generate_content(model='gemini-3.8-flash', contents=[p_list, list_img])
                        
                        names_found = [n.strip() for n in res_list.text.split(",") if n.strip()]
                        st.write("**Βρέθηκαν τα εξής ονόματα:**", names_found)
                        
                        st.session_state["found_names_cache"] = names_found

            if "found_names_cache" in st.session_state and st.session_state["found_names_cache"]:
                if st.button("📥 Αποθήκευση Ονομάτων στο Τμήμα"):
                    added_count = 0
                    for n in st.session_state["found_names_cache"]:
                        if n not in students_db[selected_class]:
                            students_db[selected_class].append(n)
                            added_count += 1
                    students_db[selected_class].sort()
                    save_students(students_db)
                    st.success(f"Επιτυχής προσθήκη {added_count} νέων μαθητών στο τμήμα {selected_class}!")
                    del st.session_state["found_names_cache"]
                    st.rerun()

        # TAB 3: ΑΝΑΦΟΡΕΣ, ΑΠΟΥΣΙΕΣ & ΔΙΑΓΡΑΦΗ
        with tab3:
            st.subheader(f"📊 Στατιστικά Τμήματος {selected_class}")
            st.caption("ℹ️ *Οι εγγραφές διαγράφονται αυτόματα μετά από 7 ημέρες.*")
            
            if st.button("🚨 Κλείσιμο Ημέρας & Σημείωση Όσων ΔΕΝ Έκαναν Ασκήσεις"):
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
                            "Αξιολόγηση": "Δεν κατατέθηκε τετράδιο."
                        })
                
                if missing_records:
                    df_missing = pd.DataFrame(missing_records)
                    df_final = pd.concat([df_g, df_missing], ignore_index=True)
                    df_final.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                    st.warning(f"Σημειώθηκαν {len(missing_records)} μαθητές ως 'Δεν έκανε ασκήσεις' για σήμερα.")
                    st.rerun()
                else:
                    st.success("Όλοι οι μαθητές έχουν βαθμολογηθεί!")

            if os.path.exists(GRADES_FILE):
                df_all = pd.read_csv(GRADES_FILE)
                df_class = df_all[df_all["Τμήμα"] == selected_class]
                
                if not df_class.empty:
                    df_display = df_class[["Ημερομηνία", "Τμήμα", "Μαθητής", "Ποσοστό", "Κατάσταση"]]
                    st.dataframe(df_display, use_container_width=True)

                    st.markdown("---")
                    st.subheader("🗑️ Χειροκίνητη Διαγραφή Εγγραφής")
                    
                    options_to_delete = ["-- Επιλέξτε εγγραφή για διαγραφή --"]
                    indices_map = {}
                    for idx, row in df_class.iterrows():
                        label = f"{row['Ημερομηνία']} | {row['Μαθητής']} | {row['Ποσοστό']} ({row['Κατάσταση']})"
                        options_to_delete.append(label)
                        indices_map[label] = idx

                    selected_del = st.selectbox("Επιλέξτε εγγραφή:", options_to_delete)
                    if st.button("🗑️ Διαγραφή Εγγραφής"):
                        if selected_del != "-- Επιλέξτε εγγραφή για διαγραφή --":
                            target_idx = indices_map[selected_del]
                            df_all = df_all.drop(target_idx)
                            df_all.to_csv(GRADES_FILE, index=False, encoding='utf-8-sig')
                            st.success("Η εγγραφή διαγράφηκε επιτυχώς!")
                            st.rerun()
                else:
                    st.info("Δεν υπάρχουν αποθηκευμένες εγγραφές για αυτό το τμήμα τις τελευταίες 7 ημέρες.")

    except Exception as e:
        st.error(f"Σφάλμα: {e}")
else:
    st.warning("Παρακαλώ εισάγετε το API Key σας.")
