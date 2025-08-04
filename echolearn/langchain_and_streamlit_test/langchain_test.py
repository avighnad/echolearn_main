import langchain
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import fitz

#systemmessage to assign a role, how to behave 
#prompt passed as humanmessage
#ai response is aimessage

def extract_pdf_text(pdf_path):
    pdf_content = fitz.open(pdf_path)
    pdf_text=""
    for page in pdf_content:
        pdf_text += page.get_text()
    return pdf_text
   


ml_pdf_path = r"/Users/avighnadaruk/Desktop/Omotec/echolearn_draft1/echolearn/langchain_and_streamlit_test/machine_learning_tutorial.pdf"
ml_pdf_content = extract_pdf_text(ml_pdf_path) 
ml_pdf_content_shortened = ml_pdf_content[:2000] #slicing



load_dotenv()

chat_history = [SystemMessage(content=f"""You are an expert examiner conducting a viva based on the contents of the following PDF content:

--- START OF PDF CONTENT ---
{ml_pdf_content_shortened}
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



# print(langchain.__version__)