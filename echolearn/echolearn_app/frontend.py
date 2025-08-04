import streamlit as st
import time 



st.set_page_config(page_title="Viva chatbot for students with learning disorders", layout="centered")
st.title("Viva simulator for students with disabilities") #instead of selecting dropdown, LLM adjusts by itself potential disorders by itself rather than use needing to input it.
#instead of dropdown selecting the difficulty the model with move up difficulties from easy to difficult by itself judging on the quality of the users answers

st.subheader("Upload course materials")
st.markdown("PDFs accepted on the material to ask questions from for the Viva/text questioning")

uploaded_pdf = st.file_uploader("Upload your file here (Only PDFs accepted)", type=["pdf"])
if "pdf_uploaded" not in st.session_state:
    st.session_state["pdf_uploaded"] = False
if uploaded_pdf is not None and not st.session_state["pdf_uploaded"]:
    progress_text="Uploading PDF, please wait..."
    with st.spinner(progress_text):
        progress_bar = st.progress(0)
        for percent_complete in range(100):
            time.sleep(0.01)
            progress_bar.progress(percent_complete+1)
        st.success("PDF Uploaded successfully")

    pdf_file_data = uploaded_pdf.read()
    st.session_state["pdf_data"] = pdf_file_data
    st.session_state["pdf_uploaded"] = True

st.subheader("Viva controls")
column1, column2 = st.columns(2)
with column1:
    start_clicked = st.button("Start Viva 🏁")
    if start_clicked:
        st.session_state["viva_running"] = True 
        st.success("Viva has started")
with column2:
    stop_clicked = st.button("Stop Viva 🛑")
    if stop_clicked:
        st.session_state["viva_running"] = False 
        st.warning("Viva has stopped")
 




                        


