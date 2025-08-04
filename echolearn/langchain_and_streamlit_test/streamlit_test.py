import streamlit as st
import langchain
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import fitz
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()
model = ChatOpenAI(model="o4-mini")
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

st.title("Echolearn AI")
file_uploaded = st.file_uploader("Choose a file")
data_file = ""
if file_uploaded is not None:
    data_file = extract_text_from_pdf(file_uploaded)
    


load_dotenv()

chat_history = [SystemMessage(content=f"""You are an expert examiner conducting a viva based on the contents of the following PDF content:

--- START OF PDF CONTENT ---
{data_file}
--- END OF PDF CONTENT ---

Ask me questions directly based on this content. After I respond, evaluate my answer strictly with reference to the PDF. Explain if wrong. Do not reveal answers unless I try. Be professional, like a real viva.""")]



model = ChatOpenAI(model="o4-mini")

while True:
    user_input = input("You: ")
    chat_history.append(HumanMessage(content=user_input))
    if user_input == "exit":
        break
    result = model.invoke(chat_history)
    chat_history.append(AIMessage(content=result.content))
    print("AI: ", result.content)














