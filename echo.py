import streamlit as st
import fitz  # PyMuPDF
from langchain.llms import OpenAI
from dotenv import load_dotenv
import os
import io
import pyttsx3
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr
import time
from auth import auth_manager
from database import db_manager

# ------------------ Load API & Init Model ------------------
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

llm = OpenAI(openai_api_key=openai_api_key, temperature=0)

# ------------------ Authentication Check ------------------
auth_manager.require_authentication()

# Show user profile in sidebar
auth_manager.show_user_profile_sidebar()

# Get current user
current_user = auth_manager.get_current_user()

st.title("📘 Echolearn - Viva Question Evaluator")

# ------------------ Session State ------------------
if "pdf_text_dict" not in st.session_state:
    st.session_state.pdf_text_dict = {}
if "qa_dict" not in st.session_state:
    st.session_state.qa_dict = {}
if "all_qas" not in st.session_state:
    st.session_state.all_qas = []
if "qa_index" not in st.session_state:
    st.session_state.qa_index = 0
if "used_q_indices" not in st.session_state:
    st.session_state.used_q_indices = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "resume_session" not in st.session_state:
    st.session_state.resume_session = False
if "question_mode" not in st.session_state:
    st.session_state.question_mode = "PDF Upload"
if "current_predefined_session_id" not in st.session_state:
    st.session_state.current_predefined_session_id = None
if "resume_predefined_session" not in st.session_state:
    st.session_state.resume_predefined_session = False

# ------------------ Check for Resume Session ------------------
if st.session_state.resume_session and st.session_state.current_conversation_id:
    # Load PDF-based conversation data
    conversations = db_manager.get_user_conversations(current_user['id'])
    current_conv = next((c for c in conversations if c['id'] == st.session_state.current_conversation_id), None)
    
    if current_conv:
        st.info(f"🔄 Resuming PDF session: {current_conv['subject']} - {current_conv['book_title']}")
        
        # Load conversation details
        name = current_conv['name']
        grade = current_conv['grade']
        subject = current_conv['subject']
        book_title = current_conv['book_title']
        
        # Load questions and answers
        questions = db_manager.get_conversation_questions(st.session_state.current_conversation_id)
        st.session_state.all_qas = questions
        
        # Set current question index to first unanswered question
        answered_indices = [i for i, q in enumerate(questions) if q['score'] is not None]
        st.session_state.used_q_indices = answered_indices
        
        # Find next unanswered question
        next_unanswered = next((i for i, q in enumerate(questions) if q['score'] is None), 0)
        st.session_state.qa_index = next_unanswered
        
        st.session_state.resume_session = False
        st.session_state.question_mode = "PDF Upload"
    
    # Skip input fields when resuming
elif st.session_state.resume_predefined_session and st.session_state.current_predefined_session_id:
    # Load predefined question session data
    session_info, questions = db_manager.get_predefined_session_questions(st.session_state.current_predefined_session_id)
    
    if session_info:
        st.info(f"🔄 Resuming predefined session: {session_info['subject_name']} - {session_info.get('topic_name', 'All Topics')}")
        
        # Load session details
        name = session_info['name']
        grade = session_info['grade']
        subject = session_info['subject_name']
        book_title = f"Predefined Questions - {session_info['subject_name']}"
        
        # Convert predefined questions to the format expected by the UI
        st.session_state.all_qas = questions
        
        # Set current question index to first unanswered question
        answered_indices = [i for i, q in enumerate(questions) if q['score'] is not None]
        st.session_state.used_q_indices = answered_indices
        
        # Find next unanswered question
        next_unanswered = next((i for i, q in enumerate(questions) if q['score'] is None), 0)
        st.session_state.qa_index = next_unanswered
        
        st.session_state.resume_predefined_session = False
        st.session_state.question_mode = "Predefined Questions"
    
    # Skip input fields when resuming
else:
    # ------------------ Show User Dashboard ------------------
    auth_manager.show_user_dashboard()
    
    # ------------------ Question Mode Selection ------------------
    st.subheader("📚 Choose Learning Mode")
    question_mode = st.radio(
        "Select how you want to practice:",
        ["PDF Upload", "Predefined Questions"],
        index=0 if st.session_state.question_mode == "PDF Upload" else 1,
        horizontal=True,
        help="PDF Upload: Generate questions from your own textbook. Predefined Questions: Practice with curated questions from our question bank."
    )
    
    st.session_state.question_mode = question_mode
    
    # ------------------ Input Fields ------------------
    st.subheader("📝 Start New Study Session")
    name = st.text_input("Name : ", value=current_user.get('full_name', current_user['username']))
    
    if question_mode == "PDF Upload":
        grade = st.text_input("Grade : ")
        subject = st.text_input("Subject : ")
        book_title = st.text_input("Book Title : ")
    else:
        # Predefined Questions Mode
        subjects = db_manager.get_subjects()
        
        if subjects:
            selected_subject = st.selectbox(
                "Subject:",
                options=[s['name'] for s in subjects],
                help="Select the subject for your practice session"
            )
            
            subject_id = next((s['id'] for s in subjects if s['name'] == selected_subject), None)
            
            if subject_id:
                # Get available grades for this subject
                grades = db_manager.get_grades_by_subject(subject_id)
                if grades:
                    grade = st.selectbox("Grade:", grades)
                else:
                    grade = st.text_input("Grade:", value="11")
                
                # Get topics for this subject
                topics = db_manager.get_topics_by_subject(subject_id)
                topic_options = ["All Topics"] + [t['name'] for t in topics]
                selected_topic = st.selectbox("Topic:", topic_options)
                
                topic_id = None
                if selected_topic != "All Topics":
                    topic_id = next((t['id'] for t in topics if t['name'] == selected_topic), None)
                
                # Difficulty range
                col1, col2 = st.columns(2)
                with col1:
                    difficulty_min = st.slider("Minimum Difficulty:", 1.0, 100.0, 1.0, 1.0)
                with col2:
                    difficulty_max = st.slider("Maximum Difficulty:", 1.0, 100.0, 100.0, 1.0)
                
                # Preview available questions
                preview_questions = db_manager.get_predefined_questions(
                    subject_id=subject_id,
                    topic_id=topic_id,
                    grade=grade,
                    difficulty_min=difficulty_min,
                    difficulty_max=difficulty_max
                )
                
                st.info(f"📊 {len(preview_questions)} questions available with your current filters")
                
                subject = selected_subject
                book_title = f"Predefined Questions - {selected_subject}"
        else:
            st.error("No subjects found in the question bank. Please contact administrator.")
            subject = ""
            grade = ""
            book_title = ""

# ------------------ PDF Upload (only for PDF mode) ------------------
if st.session_state.question_mode == "PDF Upload":
    st.header("Upload the Book's PDF")
    book_pdf_file = st.file_uploader("Choose a PDF", type="pdf")

    if book_pdf_file is not None:
        doc = fitz.open(stream=book_pdf_file.read(), filetype="pdf")
        st.session_state.pdf_text_dict.clear()

        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                st.session_state.pdf_text_dict[i + 1] = text

        st.success("✅ PDF uploaded and text extracted.")
        
        # Create new conversation in database
        if not st.session_state.current_conversation_id and name and grade and subject and book_title:
            try:
                pdf_content = "\n\n".join(st.session_state.pdf_text_dict.values())
                conversation_id = db_manager.create_conversation(
                    user_id=current_user['id'],
                    name=name,
                    grade=grade,
                    subject=subject,
                    book_title=book_title,
                    pdf_content=pdf_content
                )
                st.session_state.current_conversation_id = conversation_id
                st.success(f"📚 Study session created and saved!")
            except Exception as e:
                st.error(f"Error creating study session: {str(e)}")

    # ------------------ Page Viewer ------------------
    if st.session_state.pdf_text_dict:
        selected_page = st.selectbox("View a Page:", list(st.session_state.pdf_text_dict.keys()))
        st.text_area("Extracted Text", st.session_state.pdf_text_dict[selected_page], height=300)

    # ------------------ Question Generation ------------------
    if st.button("🔍 Generate Viva Questions"):
        if st.session_state.pdf_text_dict:
            full_text = "\n\n".join(st.session_state.pdf_text_dict.values())

            prompt = f"""
You are an expert examiner. Based on the following content:

--- CONTENT START ---
{full_text}
--- CONTENT END ---

Generate 15 viva questions along with their answers:
- 5 Easy
- 5 Moderate
- 5 Difficult

Format exactly like this:

Easy:
Q1: ...
A1: ...
...

Moderate:
Q6: ...
A6: ...
...

Difficult:
Q11: ...
A11: ...
...
            """

            response = llm.invoke(prompt)
            raw_output = response.strip() if isinstance(response, str) else response.content.strip()

            sections = {"Easy": [], "Moderate": [], "Difficult": []}
            current_section = None

            for line in raw_output.splitlines():
                line = line.strip()
                if not line:
                    continue
                if "Easy" in line:
                    current_section = "Easy"
                elif "Moderate" in line:
                    current_section = "Moderate"
                elif "Difficult" in line:
                    current_section = "Difficult"
                elif current_section and (line.startswith("Q") or line.startswith("A")):
                    sections[current_section].append(line)

            qa_dict = {}
            all_qas = []
            for level, lines in sections.items():
                level_qas = []
                for i in range(0, len(lines), 2):
                    try:
                        q = lines[i].split(":", 1)[1].strip()
                        a = lines[i + 1].split(":", 1)[1].strip()
                        qa_item = {
                            "level": level,
                            "question": q,
                            "answer": a,
                            "user_answer": "",
                            "score": None
                        }
                        level_qas.append(qa_item)
                        all_qas.append(qa_item)
                    except Exception:
                        continue
                qa_dict[level] = level_qas

            st.session_state.qa_dict = qa_dict
            st.session_state.all_qas = all_qas
            st.session_state.qa_index = 0
            st.session_state.used_q_indices = []
            
            # Save questions to database
            if st.session_state.current_conversation_id:
                success = db_manager.save_questions(st.session_state.current_conversation_id, all_qas)
                if success:
                    st.success("✅ Viva questions generated and saved to database.")
                else:
                    st.warning("✅ Viva questions generated but couldn't save to database.")
            else:
                st.success("✅ Viva questions generated.")

# ------------------ Predefined Questions Mode ------------------
elif st.session_state.question_mode == "Predefined Questions":
    st.header("📋 Predefined Question Bank")
    
    # Start predefined question session button
    if st.button("🚀 Start Question Session"):
        if name and grade and subject and 'subject_id' in locals() and subject_id:
            try:
                session_id = db_manager.create_predefined_question_session(
                    user_id=current_user['id'],
                    name=name,
                    grade=grade,
                    subject_id=subject_id,
                    topic_id=topic_id if 'topic_id' in locals() else None,
                    difficulty_min=difficulty_min if 'difficulty_min' in locals() else 1.0,
                    difficulty_max=difficulty_max if 'difficulty_max' in locals() else 100.0
                )
                
                st.session_state.current_predefined_session_id = session_id
                
                # Load questions for the session
                session_info, questions = db_manager.get_predefined_session_questions(session_id)
                st.session_state.all_qas = questions
                st.session_state.qa_index = 0
                st.session_state.used_q_indices = []
                
                st.success(f"📚 Question session started with {len(questions)} questions!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error creating question session: {str(e)}")
        else:
            st.error("Please fill in all required fields and select valid options.")

# ------------------ Answer Evaluation ------------------
def evaluate_answer(question, correct_answer, user_answer):
    eval_prompt = f"""
You are a strict examiner. Here is the question, the correct answer, and a student's answer.

Question: {question}

Correct Answer: {correct_answer}

Student's Answer: {user_answer}

Evaluate the student's answer strictly and give a score out of 10. Just reply with a number between 0 and 10. No explanation, no extra words.
"""
    result = llm.invoke(eval_prompt)
    try:
        score = int(result.strip()) if isinstance(result, str) else int(result.content.strip())
        return max(0, min(10, score))
    except Exception:
        return 0

# ------------------ Adaptive Question Selector ------------------
# ------------------ Adaptive Question Selector ------------------
def get_next_question(score):
    if score < 4:
        level = "Easy"
    elif score < 7:
        level = "Moderate"
    else:
        level = "Difficult"

    # First try to find a question of the desired level
    for i, qa in enumerate(st.session_state.all_qas):
        if qa["level"] == level and i not in st.session_state.used_q_indices:
            st.session_state.qa_index = i
            return
    
    # If none found, find any unused question
    for i, qa in enumerate(st.session_state.all_qas):
        if i not in st.session_state.used_q_indices:
            st.session_state.qa_index = i
            return

# ------------------ Viva UI ------------------
if st.session_state.all_qas:
    st.subheader("🧠 Viva Questions")

    current = st.session_state.qa_index
    qa = st.session_state.all_qas[current]
    total_questions = len(st.session_state.all_qas)
    answered_count = len(st.session_state.used_q_indices)

    # Create columns for navigation buttons
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        # Previous button - only enabled if not on first question
        # if st.button("⬅️ Previous", disabled=(current == 0)):
        #     st.session_state.qa_index = current - 1
        #     st.rerun()
            pass
            
    with col2:
        # Show current question position and progress
        st.markdown(f"**Question level: ** ({qa['level']})")
        st.markdown(f"**Progress: {answered_count} of {total_questions} answered**")
        
    with col3:
        # Next button - only enabled if not on last question
        # if st.button("Next ➡️", disabled=(current == total_questions - 1)):
        #     st.session_state.qa_index = current + 1
        #     st.rerun()
        pass

    st.markdown(f"**Q:** {qa['question']}")
    
    # Show score if already answered
    if qa['score'] is not None:
        st.success(f"Scored: {qa['score']}/10")


    # TTS using pyttsx3
    if st.button("🔊 Read Question Aloud"):
        try:
            engine = pyttsx3.init()
            engine.say(qa["question"])
            engine.runAndWait()
        except Exception as e:
            st.warning(f"TTS failed: {e}")

    # Audio recording and transcription
    record_seconds = st.slider("Select recording time (seconds):", 3, 15, 5)

    if st.button("🎙️ Record Your Answer"):
        try:
            st.info("Recording... Speak now!")
            fs = 44100
            audio = sd.rec(int(record_seconds * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            wav.write("temp.wav", fs, audio)

            # Transcribe
            recognizer = sr.Recognizer()
            with sr.AudioFile("temp.wav") as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)

                st.session_state.all_qas[current]["user_answer"] = text
                st.success("✅ Transcription Successful")
                st.text_area("Your Answer (from audio)", value=text, key=f"audio_text_{current}")
                
                # Auto-evaluate and save audio answer
                score = evaluate_answer(qa["question"], qa["answer"], text)
                st.session_state.all_qas[current]["score"] = score
                
                # Save to database
                if st.session_state.current_conversation_id:
                    # PDF-generated questions
                    questions = db_manager.get_conversation_questions(st.session_state.current_conversation_id)
                    if current < len(questions):
                        question_id = questions[current]['id']
                        db_manager.save_user_answer(question_id, text, score, answer_method='audio')
                        db_manager.update_user_progress(current_user['id'], subject)
                elif st.session_state.current_predefined_session_id:
                    # Predefined questions
                    question_id = qa.get('id')
                    if question_id:
                        db_manager.save_predefined_question_answer(
                            st.session_state.current_predefined_session_id,
                            question_id,
                            text,
                            score,
                            answer_method='audio'
                        )
                        db_manager.update_user_progress(current_user['id'], subject)
                
                # Add to used indices
                if current not in st.session_state.used_q_indices:
                    st.session_state.used_q_indices.append(current)
                
                st.success(f"🎙️ Audio answer scored: {score}/10")

        except Exception as e:
            st.error(f"❌ Error during recording/transcription: {e}")

    # Manual edit box
    manual_answer = st.text_area("Edit Your Answer", value=qa.get("user_answer", ""), key=f"user_answer_{current}")

    if st.button("✅ Submit Answer"):
        st.session_state.all_qas[current]["user_answer"] = manual_answer
        score = evaluate_answer(qa["question"], qa["answer"], manual_answer)
        st.session_state.all_qas[current]["score"] = score
        
        # Save answer to database
        if st.session_state.current_conversation_id:
            # PDF-generated questions
            questions = db_manager.get_conversation_questions(st.session_state.current_conversation_id)
            if current < len(questions):
                question_id = questions[current]['id']
                db_manager.save_user_answer(question_id, manual_answer, score, answer_method='text')
                
                # Update user progress
                db_manager.update_user_progress(current_user['id'], subject)
        elif st.session_state.current_predefined_session_id:
            # Predefined questions
            question_id = qa.get('id')  # Use the question ID from predefined bank
            if question_id:
                db_manager.save_predefined_question_answer(
                    st.session_state.current_predefined_session_id, 
                    question_id, 
                    manual_answer, 
                    score, 
                    answer_method='text'
                )
                
                # Update user progress
                db_manager.update_user_progress(current_user['id'], subject)
        
        # Only add to used indices if not already added
        if current not in st.session_state.used_q_indices:
            st.session_state.used_q_indices.append(current)
            
        st.success(f"✅ Answer saved and scored: {score}/10")
        time.sleep(1)  # Short delay to allow user to see the message
        
        # Check if session is complete
        if len(st.session_state.used_q_indices) >= len(st.session_state.all_qas):
            # Mark session as completed
            if st.session_state.current_conversation_id:
                # Mark PDF conversation as completed
                try:
                    import sqlite3
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE conversations 
                            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (st.session_state.current_conversation_id,))
                        conn.commit()
                except Exception as e:
                    print(f"Error marking conversation complete: {e}")
            elif st.session_state.current_predefined_session_id:
                # Mark predefined question session as completed
                try:
                    import sqlite3
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE predefined_question_sessions 
                            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (st.session_state.current_predefined_session_id,))
                        conn.commit()
                except Exception as e:
                    print(f"Error marking predefined session complete: {e}")
            
            st.info("✅ All questions completed.")
            total_score = sum(q['score'] for q in st.session_state.all_qas if q.get('score') is not None)
            max_score = 10 * len(st.session_state.all_qas)
            st.balloons()
            st.success(f"🎉 All questions completed! Total Score: {total_score}/{max_score}")
        else:
            # Only run adaptive selection if not all questions are answered
            # Preserve the current index for manual navigation
            current_index_before_adaptive = st.session_state.qa_index
            
            # Run adaptive selection
            get_next_question(score)
            
            # If adaptive selection changed the index, show a message and rerun
            if current_index_before_adaptive != st.session_state.qa_index:
                st.info(f"🔀 Adaptive selection moved to question {st.session_state.qa_index + 1}")
                st.rerun()  # ADDED THIS LINE TO FORCE REFRESH
            else:
                st.warning("⚠️ Couldn't find a suitable next question. Please use navigation buttons.")
# ------------------ Save Report ------------------
def save_qa_to_text_file(name, grade, subject, book_title, all_qas):
    output = io.StringIO()
    output.write(f"Name: {name}\nGrade: {grade}\nSubject: {subject}\nBook Title: {book_title}\n\n")
    output.write("Structured Viva Questions, Answers, and Scores\n")
    output.write("=" * 70 + "\n\n")

    for i, qa in enumerate(all_qas, 1):
        output.write(f"[{i}] Difficulty: {qa['level']}\n")
        output.write(f"Q: {qa['question']}\n")
        output.write(f"LLM Answer: {qa['answer']}\n")
        output.write(f"User Answer: {qa['user_answer'] if qa['user_answer'] else '[Not answered]'}\n")
        output.write(f"Score: {qa['score'] if qa['score'] is not None else '[Not evaluated]'} / 10\n")
        output.write("-" * 70 + "\n")

    return output.getvalue()

if st.session_state.all_qas:
    st.subheader("📄 Download Q&A + Scores")

    if st.button("📥 Generate Report"):
        # Get current values or use saved values
        report_name = name if 'name' in locals() else current_user.get('full_name', current_user['username'])
        report_grade = grade if 'grade' in locals() else 'N/A'
        report_subject = subject if 'subject' in locals() else 'N/A'
        report_book_title = book_title if 'book_title' in locals() else 'N/A'
        
        file_content = save_qa_to_text_file(report_name, report_grade, report_subject, report_book_title, st.session_state.all_qas)
        st.download_button(
            label="Download as Text File",
            data=file_content,
            file_name=f"viva_evaluation_report_{current_user['username']}_{int(time.time())}.txt",
            mime="text/plain"
        )
        
    # Show session statistics
    if st.session_state.current_conversation_id or st.session_state.current_predefined_session_id:
        st.subheader("📊 Session Statistics")
        
        total_questions = len(st.session_state.all_qas) if st.session_state.all_qas else 0
        answered_questions = len(st.session_state.used_q_indices)
        total_score = sum(q.get('score', 0) for q in st.session_state.all_qas if q.get('score') is not None) if st.session_state.all_qas else 0
        max_score = answered_questions * 10
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Questions", total_questions)
        col2.metric("Answered", answered_questions)
        col3.metric("Score", f"{total_score}/{max_score}")
        if answered_questions > 0:
            col4.metric("Average Score", f"{total_score/answered_questions:.1f}/10")
        else:
            col4.metric("Average Score", "0/10")
    
    # Add option to start new session
    if st.button("🆕 Start New Session"):
        # Clear session state for both PDF and predefined question sessions
        keys_to_clear = [
            'current_conversation_id', 'current_predefined_session_id', 
            'pdf_text_dict', 'qa_dict', 'all_qas', 'qa_index', 'used_q_indices', 
            'resume_session', 'resume_predefined_session', 'question_mode'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
