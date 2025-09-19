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
# Adaptive learning state variables
if "adaptive_mode" not in st.session_state:
    st.session_state.adaptive_mode = True
if "current_difficulty" not in st.session_state:
    st.session_state.current_difficulty = 10  # Start at middle difficulty
if "last_answer_correct" not in st.session_state:
    st.session_state.last_answer_correct = None
if "consecutive_wrong_same_level" not in st.session_state:
    st.session_state.consecutive_wrong_same_level = 0
if "difficulty_path" not in st.session_state:
    st.session_state.difficulty_path = []
if "session_complete" not in st.session_state:
    st.session_state.session_complete = False

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

Generate 20 viva questions along with their answers across different difficulty levels from 1-20:
- 5 questions at difficulty level 1-5 (Basic)
- 5 questions at difficulty level 6-10 (Intermediate) 
- 5 questions at difficulty level 11-15 (Advanced)
- 5 questions at difficulty level 16-20 (Expert)

Format exactly like this:

Basic (1-5):
Q1: [Difficulty: 3] ...
A1: ...
...

Intermediate (6-10):
Q6: [Difficulty: 7] ...
A6: ...
...

Advanced (11-15):
Q11: [Difficulty: 13] ...
A11: ...
...

Expert (16-20):
Q16: [Difficulty: 18] ...
A16: ...
            """

            response = llm.invoke(prompt)
            raw_output = response.strip() if isinstance(response, str) else response.content.strip()

            sections = {"Basic": [], "Intermediate": [], "Advanced": [], "Expert": []}
            current_section = None

            for line in raw_output.splitlines():
                line = line.strip()
                if not line:
                    continue
                if "Basic" in line:
                    current_section = "Basic"
                elif "Intermediate" in line:
                    current_section = "Intermediate"
                elif "Advanced" in line:
                    current_section = "Advanced"
                elif "Expert" in line:
                    current_section = "Expert"
                elif current_section and (line.startswith("Q") or line.startswith("A")):
                    sections[current_section].append(line)

            qa_dict = {}
            all_qas = []
            difficulty_mapping = {"Basic": (1, 5), "Intermediate": (6, 10), "Advanced": (11, 15), "Expert": (16, 20)}
            
            for level, lines in sections.items():
                level_qas = []
                for i in range(0, len(lines), 2):
                    try:
                        q_line = lines[i]
                        a_line = lines[i + 1]
                        
                        # Extract difficulty from question if specified
                        import re
                        difficulty_match = re.search(r'\[Difficulty: (\d+)\]', q_line)
                        if difficulty_match:
                            difficulty = int(difficulty_match.group(1))
                            q = q_line.split(":", 1)[1].replace(f"[Difficulty: {difficulty}]", "").strip()
                        else:
                            # Use default difficulty for the section
                            min_diff, max_diff = difficulty_mapping[level]
                            difficulty = (min_diff + max_diff) // 2
                            q = q_line.split(":", 1)[1].strip()
                        
                        a = a_line.split(":", 1)[1].strip()
                        qa_item = {
                            "level": level,
                            "question": q,
                            "answer": a,
                            "difficulty": difficulty,
                            "user_answer": "",
                            "score": None
                        }
                        level_qas.append(qa_item)
                        all_qas.append(qa_item)
                    except Exception as e:
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

# ------------------ Adaptive Question Logic (Following Flowchart) ------------------
def get_next_question_adaptive(user_score):
    """Implements the adaptive logic from the flowchart"""
    
    # Determine if answer was correct (score >= 6 considered correct)
    is_correct = user_score >= 6
    st.session_state.last_answer_correct = is_correct
    st.session_state.difficulty_path.append({
        'difficulty': st.session_state.current_difficulty,
        'score': user_score,
        'correct': is_correct,
        'question_index': st.session_state.qa_index
    })
    
    if is_correct:
        # Correct answer logic
        st.session_state.consecutive_wrong_same_level = 0
        
        # Move to random question from higher difficulty
        higher_difficulties = [d for d in range(st.session_state.current_difficulty + 1, 21)]
        if higher_difficulties:
            import random
            st.session_state.current_difficulty = random.choice(higher_difficulties)
        
    else:
        # Wrong answer logic
        st.session_state.consecutive_wrong_same_level += 1
        
        if st.session_state.consecutive_wrong_same_level >= 2:
            # Two consecutive wrong answers at same level -> drop down difficulty
            if st.session_state.current_difficulty > 1:
                st.session_state.current_difficulty = max(1, st.session_state.current_difficulty - 2)
            st.session_state.consecutive_wrong_same_level = 0
        # Otherwise stay at same difficulty for another question
    
    # Find next question at target difficulty level
    find_question_by_difficulty(st.session_state.current_difficulty)

def find_question_by_difficulty(target_difficulty):
    """Find an unused question closest to target difficulty"""
    
    # First try exact match
    for i, qa in enumerate(st.session_state.all_qas):
        if (i not in st.session_state.used_q_indices and 
            qa.get('difficulty', get_difficulty_from_level(qa['level'])) == target_difficulty):
            st.session_state.qa_index = i
            return True
    
    # If no exact match, find closest difficulty
    best_match = None
    best_diff = float('inf')
    
    for i, qa in enumerate(st.session_state.all_qas):
        if i not in st.session_state.used_q_indices:
            qa_difficulty = qa.get('difficulty', get_difficulty_from_level(qa['level']))
            diff = abs(qa_difficulty - target_difficulty)
            if diff < best_diff:
                best_diff = diff
                best_match = i
    
    if best_match is not None:
        st.session_state.qa_index = best_match
        return True
    
    return False

def get_difficulty_from_level(level):
    """Convert text levels to numeric difficulty for compatibility"""
    mapping = {
        'Basic': 3, 'Easy': 3,
        'Intermediate': 8, 'Moderate': 8, 
        'Advanced': 13, 'Difficult': 13,
        'Expert': 18
    }
    return mapping.get(level, 10)

# ------------------ Viva UI ------------------
if st.session_state.all_qas:
    st.subheader("🧠 Viva Questions")
    
    # Adaptive Mode Toggle
    col_adaptive, col_info = st.columns([1, 3])
    with col_adaptive:
        adaptive_mode = st.checkbox(
            "🎯 Adaptive Mode", 
            value=st.session_state.adaptive_mode,
            help="Enable intelligent difficulty adjustment based on performance"
        )
        if adaptive_mode != st.session_state.adaptive_mode:
            st.session_state.adaptive_mode = adaptive_mode
            st.rerun()
    
    with col_info:
        if st.session_state.adaptive_mode:
            st.caption(f"Current adaptive difficulty: **{st.session_state.current_difficulty}/20** | Consecutive wrong: **{st.session_state.consecutive_wrong_same_level}**")

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
            
        # Show current adaptive difficulty if in adaptive mode
        if st.session_state.adaptive_mode:
            current_qa_difficulty = qa.get('difficulty', get_difficulty_from_level(qa['level']))
            st.info(f"🎯 Current Target Difficulty: {st.session_state.current_difficulty} | This Question: {current_qa_difficulty}")


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
            st.session_state.session_complete = True
            total_score = sum(q['score'] for q in st.session_state.all_qas if q.get('score') is not None)
            max_score = 10 * len(st.session_state.all_qas)
            st.balloons()
            
            # Comprehensive final scoring display
            display_final_score_report()
            
            st.success(f"🎉 All questions completed! Total Score: {total_score}/{max_score}")
        else:
            if st.session_state.adaptive_mode:
                # Run adaptive selection based on flowchart logic
                current_index_before_adaptive = st.session_state.qa_index
                
                get_next_question_adaptive(score)
                
                # If adaptive selection changed the index, show a message and rerun
                if current_index_before_adaptive != st.session_state.qa_index:
                    st.info(f"🎯 Adaptive system selected question {st.session_state.qa_index + 1} (Difficulty: {st.session_state.current_difficulty})")
                    st.rerun()
                else:
                    st.warning("⚠️ No more suitable questions found at current difficulty level.")
            else:
                # Manual mode - just proceed to next unanswered question
                next_unanswered = next((i for i, q in enumerate(st.session_state.all_qas) 
                                      if i not in st.session_state.used_q_indices), None)
                if next_unanswered is not None:
                    st.session_state.qa_index = next_unanswered
                    st.rerun()
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
            
        # Show adaptive learning progress if enabled
        if st.session_state.adaptive_mode and st.session_state.difficulty_path:
            st.subheader("🎯 Adaptive Learning Journey")
            display_adaptive_progress()
    
    # Add option to start new session
    if st.button("🆕 Start New Session"):
        # Clear session state for both PDF and predefined question sessions
        keys_to_clear = [
            'current_conversation_id', 'current_predefined_session_id', 
            'pdf_text_dict', 'qa_dict', 'all_qas', 'qa_index', 'used_q_indices', 
            'resume_session', 'resume_predefined_session', 'question_mode',
            'adaptive_mode', 'current_difficulty', 'last_answer_correct',
            'consecutive_wrong_same_level', 'difficulty_path', 'session_complete'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ------------------ Final Scoring and Analytics ------------------
def display_final_score_report():
    """Comprehensive final scoring report with detailed analytics"""
    st.subheader("🏆 Final Score Report")
    
    # Basic statistics
    total_questions = len(st.session_state.all_qas)
    answered_questions = len([q for q in st.session_state.all_qas if q.get('score') is not None])
    total_score = sum(q.get('score', 0) for q in st.session_state.all_qas if q.get('score') is not None)
    max_possible_score = answered_questions * 10
    
    # Performance metrics
    if answered_questions > 0:
        average_score = total_score / answered_questions
        percentage = (total_score / max_possible_score) * 100
        
        # Grade classification
        if percentage >= 90:
            grade = "A+", "🏅 Outstanding!"
        elif percentage >= 80:
            grade = "A", "⭐ Excellent!"
        elif percentage >= 70:
            grade = "B", "😊 Good Job!"
        elif percentage >= 60:
            grade = "C", "👍 Fair Performance"
        elif percentage >= 50:
            grade = "D", "💪 Need Improvement"
        else:
            grade = "F", "📚 Keep Studying!"
    else:
        average_score = 0
        percentage = 0
        grade = "N/A", "No questions answered"
    
    # Display main metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="🎯 Overall Score",
            value=f"{total_score}/{max_possible_score}",
            delta=f"{percentage:.1f}%"
        )
    
    with col2:
        st.metric(
            label="📊 Average per Question",
            value=f"{average_score:.1f}/10",
            delta=f"{(average_score/10)*100:.0f}%"
        )
    
    with col3:
        st.metric(
            label="🏅 Final Grade",
            value=grade[0],
            delta=grade[1]
        )
    
    # Difficulty distribution analysis
    if st.session_state.all_qas:
        st.subheader("📈 Performance by Difficulty")
        
        difficulty_stats = {}
        for qa in st.session_state.all_qas:
            if qa.get('score') is not None:
                difficulty = qa.get('difficulty', get_difficulty_from_level(qa.get('level', 'Basic')))
                
                # Group into ranges
                if difficulty <= 5:
                    diff_range = "1-5 (Basic)"
                elif difficulty <= 10:
                    diff_range = "6-10 (Intermediate)"
                elif difficulty <= 15:
                    diff_range = "11-15 (Advanced)"
                else:
                    diff_range = "16-20 (Expert)"
                
                if diff_range not in difficulty_stats:
                    difficulty_stats[diff_range] = {'scores': [], 'total': 0, 'max': 0}
                
                difficulty_stats[diff_range]['scores'].append(qa['score'])
                difficulty_stats[diff_range]['total'] += qa['score']
                difficulty_stats[diff_range]['max'] += 10
        
        # Display difficulty performance
        for diff_range, stats in difficulty_stats.items():
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            percentage = (stats['total'] / stats['max']) * 100 if stats['max'] > 0 else 0
            
            st.write(f"**{diff_range}:** {len(stats['scores'])} questions, {avg_score:.1f}/10 avg ({percentage:.1f}%)")
            st.progress(percentage / 100)
    
    # Adaptive learning insights (if applicable)
    if st.session_state.adaptive_mode and st.session_state.difficulty_path:
        st.subheader("🧠 Adaptive Learning Insights")
        
        # Calculate learning trajectory
        initial_difficulty = st.session_state.difficulty_path[0]['difficulty']
        final_difficulty = st.session_state.current_difficulty
        difficulty_change = final_difficulty - initial_difficulty
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Starting Difficulty",
                f"{initial_difficulty}/20",
                help="Difficulty level of first question"
            )
        
        with col2:
            st.metric(
                "Final Difficulty", 
                f"{final_difficulty}/20",
                delta=f"{difficulty_change:+d}"
            )
        
        with col3:
            correct_answers = sum(1 for step in st.session_state.difficulty_path if step['correct'])
            accuracy = (correct_answers / len(st.session_state.difficulty_path)) * 100 if st.session_state.difficulty_path else 0
            st.metric(
                "Accuracy Rate",
                f"{accuracy:.1f}%",
                delta=f"{correct_answers}/{len(st.session_state.difficulty_path)}"
            )
        
        # Learning trajectory chart
        if len(st.session_state.difficulty_path) > 1:
            st.write("**📈 Learning Trajectory:**")
            
            difficulty_progression = [step['difficulty'] for step in st.session_state.difficulty_path]
            scores_progression = [step['score'] for step in st.session_state.difficulty_path]
            
            import pandas as pd
            
            df = pd.DataFrame({
                'Question': range(1, len(difficulty_progression) + 1),
                'Difficulty Level': difficulty_progression,
                'Score': scores_progression
            })
            
            st.line_chart(df.set_index('Question'))
            
            # Performance insights
            if difficulty_change > 0:
                st.success(f"🚀 Great progress! You advanced {difficulty_change} difficulty levels.")
            elif difficulty_change == 0:
                st.info("🎯 You maintained a consistent difficulty level throughout the session.")
            else:
                st.info(f"📚 The system adapted to your learning pace, focusing on foundational concepts.")

def display_adaptive_progress():
    """Display adaptive learning progress visualization"""
    if not st.session_state.difficulty_path:
        return
    
    # Show recent difficulty changes
    recent_steps = st.session_state.difficulty_path[-5:] if len(st.session_state.difficulty_path) > 5 else st.session_state.difficulty_path
    
    st.write("**Recent Progress:**")
    for i, step in enumerate(recent_steps, 1):
        status = "✅" if step['correct'] else "❌"
        st.write(f"{status} Q{step['question_index']+1}: Difficulty {step['difficulty']} → Score {step['score']}/10")
    
    # Show difficulty trend
    if len(st.session_state.difficulty_path) >= 3:
        recent_difficulties = [step['difficulty'] for step in st.session_state.difficulty_path[-3:]]
        if recent_difficulties[-1] > recent_difficulties[0]:
            st.success("📈 Trending upward in difficulty!")
        elif recent_difficulties[-1] < recent_difficulties[0]:
            st.info("📉 Focusing on strengthening fundamentals")
        else:
            st.info("🎯 Maintaining consistent challenge level")
