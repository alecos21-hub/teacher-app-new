import streamlit as st
from google import genai
import os

# Ρύθμιση τίτλου σελίδας
st.set_page_config(page_title="Teacher Assistant", page_icon="📚")

st.title("📚 Εκπαιδευτικός Βοηθός AI")
st.write("Καλώς ήρθατε! Υποβάλετε το ερώτημα ή το θέμα του μαθήματος για να λάβετε υποστήριξη.")

# Εισαγωγή Gemini API Key
api_key = st.text_input("Εισάγετε το Gemini API Key σας:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    
    prompt = st.text_area("Γράψτε το θέμα ή την ερώτησή σας εδώ:")
    
    if st.button("Δημιουργία Απάντησης"):
        if prompt:
            with st.spinner("Δημιουργία περιεχομένου..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    st.success("Ετοιμο!")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Σφάλμα κατά την επεξεργασία: {e}")
        else:
            st.warning("Παρακαλώ συμπληρώστε το πεδίο κειμένου.")
else:
    st.info("Παρακαλώ εισάγετε το API Key σας για να συνεχίσετε.")
