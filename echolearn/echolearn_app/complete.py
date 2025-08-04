import streamlit as st
import langchain
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import fitz
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()
model = ChatOpenAI(model="o4-mini")

st.title("Echolearn")

name = st.text_input("Name: ")

grade = st.text_input("Grade: ")

subject = st.text_input("Subject : ")

book_title = st.text_input("Book Title : ")

st.header("Upload a Book's PDF File")
book_pdf_file = st.file_uploader("Choose a Book's PDF file", type="pdf")

first_page_text=""
if book_pdf_file is not None:
    # Read and open the PDF from memory
    doc = fitz.open(stream=book_pdf_file.read(), filetype="pdf") #read function to read the pdf
    print(type(doc))
    # Display number of pages
    st.write(f"Total Pages: {len(doc)}") 

    # Show text from first page
    first_page_text = doc[3].get_text() #all the content of the pdf is returned to the doc 
    st.text_area("Text from Page 3", first_page_text, height=300)
    print(first_page_text) #reads the pdf page by page, help choose what page you want through indexing. gets the length of the pdf doc 

if first_page_text is not None:
    chat_history = [SystemMessage(content=f"""You are an expert examiner conducting a viva based on the contents of the following PDF content:

    --- START OF PDF CONTENT ---
    {first_page_text}
    --- END OF PDF CONTENT ---

    Ask me questions directly based on this content. After I respond, evaluate my answer strictly with reference to the PDF. Explain if wrong. Do not reveal answers unless I try. Be professional, like a real viva.""")]

# Initialize state
if "viva_status" not in st.session_state:
    st.session_state.viva_status = "stopped"

# Two buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("Start 🏁"):
        st.session_state.viva_status = "started"

with col2:
    if st.button("Stop 🛑"):
        st.session_state.viva_status = "stopped"

# Show current status
st.info(f"Current status: {st.session_state.viva_status}")

# if "answer_completion" not in st.session_state:
#     st.session_state.answer_completion=False




while st.session_state.viva_status=="started":
    result = model.invoke(chat_history)
    chat_history.append(AIMessage(content=result.content))
    st.write(f"Question: {result.content} ")
    user_answer = st.text_input("Enter your answer")
    if len(user_answer)==10:
        chat_history.append(HumanMessage(content=user_answer))
    if st.session_state.viva_status=="stopped":
        break

