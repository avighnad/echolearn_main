# -*- coding: utf-8 -*-
"""
EchoLearn - Viva Question Evaluator (Refactored)
Main application file using modular architecture
"""

import streamlit as st
import fitz  # PyMuPDF
from langchain.llms import OpenAI
from dotenv import load_dotenv
import os
import time
from auth import auth_manager
from database import db_manager

# Import our new modules
from scoring import AnswerEvaluator, ScoringAnalytics
from ui_components import UIComponents
from question_manager import QuestionManager
from adaptive_learning import AdaptiveLearningEngine
from selective_mutism_support import SelectiveMutismSupport
from audio_lab import audio_lab

# ------------------ Load API & Init Model ------------------
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

llm = OpenAI(openai_api_key=openai_api_key, temperature=0)

# Initialize modules
scoring_evaluator = AnswerEvaluator(llm)
question_manager = QuestionManager(llm)
adaptive_engine = AdaptiveLearningEngine()
selective_mutism_support = SelectiveMutismSupport()

# ------------------ Authentication Check ------------------
auth_manager.require_authentication()

# Show user profile in sidebar
auth_manager.show_user_profile_sidebar()

# Get current user
current_user = auth_manager.get_current_user()

st.title("📘 Echolearn - Viva Question Evaluator")

# ------------------ Session State Initialization ------------------
def initialize_session_state():
    """Initialize all session state variables"""
    default_states = {
        'pdf_text_dict': {},
        'qa_dict': {},
        'all_qas': [],
        'qa_index': 0,
        'used_q_indices': [],
        'current_conversation_id': None,
        'resume_session': False,
        'question_mode': "PDF Upload",
        'current_predefined_session_id': None,
        'resume_predefined_session': False,
        'adaptive_mode': True,
        'current_difficulty': 10,
        'last_answer_correct': None,
        'consecutive_wrong_same_level': 0,
        'difficulty_path': [],
        'session_complete': False,
        'selective_mutism_mode': False,
        'confidence_level': 1,
        'success_streak': 0,
        'sm_progress_milestones': []
    }
    
    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_session_state()

# ------------------ Resume Session Logic ------------------
def handle_resume_sessions():
    """Handle resuming PDF or predefined question sessions"""
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
            
            return name, grade, subject, book_title
    
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
            
            return name, grade, subject, book_title
    
    return None, None, None, None

# ------------------ Main Application Logic ------------------
def main():
    """Main application logic"""
    # Get current user within the function
    current_user = auth_manager.get_current_user()
    
    # Handle resume sessions
    name, grade, subject, book_title = handle_resume_sessions()
    
    if name is None:
        # ------------------ Show User Dashboard ------------------
        auth_manager.show_user_dashboard()
        
        # ------------------ Question Mode Selection ------------------
        st.subheader("📚 Choose Learning Mode")
        question_mode = st.radio(
            "Select how you want to practice:",
            ["PDF Upload", "Predefined Questions", "Audio Training Lab"],
            index=0 if st.session_state.question_mode == "PDF Upload" else (1 if st.session_state.question_mode == "Predefined Questions" else 2),
            horizontal=True,
            help="PDF Upload: Generate questions from your own textbook. Predefined Questions: Practice with curated questions from our question bank. Audio Training Lab: Record and analyze audio for ML training."
        )
        
        st.session_state.question_mode = question_mode
        
        # ------------------ Input Fields ------------------
        st.subheader("📝 Start New Study Session")
        # Handle case where current_user might be None
        default_name = ""
        if current_user:
            default_name = current_user.get('full_name', current_user.get('username', ''))
        name = st.text_input("Name : ", value=default_name)
        
        if question_mode == "PDF Upload":
            grade = st.text_input("Grade : ")
            subject = st.text_input("Subject : ")
            book_title = st.text_input("Book Title : ")
        elif question_mode == "Audio Training Lab":
            # Audio Lab doesn't need grade/subject input
            grade = "N/A"
            subject = "Audio Training"
            book_title = "Audio Training Lab"
        else:
            # Predefined Questions Mode - Initialize all variables first
            subject_id = None
            topic_id = None
            difficulty_min = 1.0
            difficulty_max = 100.0
            subject = ""
            grade = ""
            book_title = ""
            
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
    
    # ------------------ PDF Upload (only for PDF mode) ------------------
    if st.session_state.question_mode == "PDF Upload":
        handle_pdf_upload(name, grade, subject, book_title)
    
    # ------------------ Predefined Questions Mode ------------------
    elif st.session_state.question_mode == "Predefined Questions":
        # Pass all required variables to the function
        predefined_vars = {
            'subject_id': locals().get('subject_id'),
            'topic_id': locals().get('topic_id'),
            'difficulty_min': locals().get('difficulty_min', 1.0),
            'difficulty_max': locals().get('difficulty_max', 100.0),
            'current_user': current_user
        }
        handle_predefined_questions(name, grade, subject, book_title, predefined_vars)
    
    # ------------------ Audio Training Lab Mode ------------------
    elif st.session_state.question_mode == "Audio Training Lab":
        handle_audio_training_lab()
    
    # ------------------ Viva Questions Interface ------------------
    if st.session_state.all_qas:
        handle_viva_interface(name, grade, subject, book_title)

def handle_pdf_upload(name, grade, subject, book_title):
    """Handle PDF upload and question generation"""
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
            
            # Use the new question manager
            questions, validation_errors = question_manager.generate_and_validate_questions(full_text, 20)
            
            if validation_errors:
                st.warning("Some questions had validation issues:")
                for error in validation_errors:
                    st.write(f"• {error}")
            
            if questions:
                st.session_state.all_qas = questions
                st.session_state.qa_index = 0
                st.session_state.used_q_indices = []
                
                # Save questions to database
                if st.session_state.current_conversation_id:
                    success = db_manager.save_questions(st.session_state.current_conversation_id, questions)
                    if success:
                        st.success("✅ Viva questions generated and saved to database.")
                    else:
                        st.warning("✅ Viva questions generated but couldn't save to database.")
                else:
                    st.success("✅ Viva questions generated.")
            else:
                st.error("Failed to generate valid questions. Please try again.")

def handle_predefined_questions(name, grade, subject, book_title, predefined_vars):
    """Handle predefined questions mode"""
    st.header("📋 Predefined Question Bank")
    
    # Extract variables from the passed dictionary
    subject_id = predefined_vars.get('subject_id')
    topic_id = predefined_vars.get('topic_id')
    difficulty_min = predefined_vars.get('difficulty_min', 1.0)
    difficulty_max = predefined_vars.get('difficulty_max', 100.0)
    current_user = predefined_vars.get('current_user')
    
    # Start predefined question session button
    if st.button("🚀 Start Question Session"):
        # Detailed validation with specific error messages
        validation_errors = []
        
        if not name or name.strip() == "":
            validation_errors.append("Name is required")
        if not grade or grade.strip() == "":
            validation_errors.append("Grade is required")
        if not subject or subject.strip() == "":
            validation_errors.append("Subject is required")
        if not subject_id:
            validation_errors.append("Please select a valid subject")
        if not current_user:
            validation_errors.append("User authentication required")
        
        if validation_errors:
            st.error("❌ **Please fix the following issues:**")
            for error in validation_errors:
                st.error(f"   • {error}")
        else:
            try:
                session_id = db_manager.create_predefined_question_session(
                    user_id=current_user['id'],
                    name=name,
                    grade=grade,
                    subject_id=subject_id,
                    topic_id=topic_id,
                    difficulty_min=difficulty_min,
                    difficulty_max=difficulty_max
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

def handle_audio_training_lab():
    """Handle the Audio Training Lab interface"""
    audio_lab.display_audio_lab_interface()

def handle_viva_interface(name, grade, subject, book_title):
    """Handle the main viva questions interface"""
    st.subheader("🧠 Viva Questions")
    
    # Display mode toggles
    mode_settings = UIComponents.display_mode_toggles()
    adaptive_mode = mode_settings['adaptive_mode']
    selective_mutism_mode = mode_settings['selective_mutism_mode']
    
    current = st.session_state.qa_index
    qa = st.session_state.all_qas[current]
    total_questions = len(st.session_state.all_qas)
    
    # Display question navigation
    UIComponents.display_question_navigation(current, total_questions, qa)
    
    # Display question info
    UIComponents.display_question_info(qa, adaptive_mode)
    
    # Display TTS button
    UIComponents.display_tts_button(qa)
    
    # Handle audio recording
    transcribed_text = UIComponents.display_audio_recording_interface(qa, current, selective_mutism_mode)
    
    if transcribed_text:
        handle_audio_answer(qa, current, transcribed_text, selective_mutism_mode, adaptive_mode, subject)
    
    # Handle text input
    if not selective_mutism_mode:
        handle_text_input(qa, current, adaptive_mode, subject)
    else:
        handle_selective_mutism_text_input(qa, current, subject)
    
    # Display session statistics
    UIComponents.display_session_statistics(st.session_state.all_qas)
    
    # Display report download
    user_info = {'name': name, 'subject': subject, 'book_title': book_title}
    UIComponents.display_report_download(st.session_state.all_qas, user_info)
    
    # Add option to start new session
    if st.button("🆕 Start New Session"):
        clear_session_state()
        st.rerun()

def handle_audio_answer(qa, current, transcribed_text, selective_mutism_mode, adaptive_mode, subject):
    """Handle audio answer processing"""
    st.session_state.all_qas[current]["user_answer"] = transcribed_text
    
    # Evaluate answer using appropriate method
    if selective_mutism_mode:
        evaluation = scoring_evaluator.evaluate_answer_selective_mutism(
            qa["question"], qa["answer"], transcribed_text, st.session_state.confidence_level
        )
        score = evaluation['score']
        
        # Update confidence and show encouragement
        confidence_update = selective_mutism_support.update_confidence_level(
            score >= 6, 'speech'
        )
        
        UIComponents.display_evaluation_result(evaluation, 'selective_mutism')
        
        # Special celebration for speech training
        if score >= 6:
            st.balloons()
            st.success("🎙️ **You did it! You spoke up and that's incredible!** Your voice matters!")
        else:
            st.info("🎙️ **You were so brave to speak! Every time you practice, you get stronger!**")
        
        # Update session state
        st.session_state.confidence_level = selective_mutism_support.state.confidence_level
        st.session_state.success_streak = selective_mutism_support.state.success_streak
        st.session_state.sm_progress_milestones = selective_mutism_support.state.progress_milestones
        
    else:
        evaluation = scoring_evaluator.evaluate_answer_standard(
            qa["question"], qa["answer"], transcribed_text
        )
        score = evaluation['score']
        UIComponents.display_evaluation_result(evaluation, 'standard')
    
    st.session_state.all_qas[current]["score"] = score
    
    # Save to database
    save_answer_to_database(current, transcribed_text, score, 'audio', subject)
    
    # Add to used indices
    if current not in st.session_state.used_q_indices:
        st.session_state.used_q_indices.append(current)
    
    # Handle next question logic
    handle_next_question_logic(score, adaptive_mode, selective_mutism_mode)

def handle_text_input(qa, current, adaptive_mode, subject):
    """Handle regular text input"""
    manual_answer = UIComponents.display_text_input(qa, current, False)
    
    if UIComponents.display_submit_button("standard"):
        if manual_answer.strip():
            st.session_state.all_qas[current]["user_answer"] = manual_answer
            
            # Evaluate answer
            evaluation = scoring_evaluator.evaluate_answer_standard(
                qa["question"], qa["answer"], manual_answer
            )
            score = evaluation['score']
            st.session_state.all_qas[current]["score"] = score
            
            # Display result
            UIComponents.display_evaluation_result(evaluation, 'standard')
            
            # Save to database
            save_answer_to_database(current, manual_answer, score, 'text', subject)
            
            # Add to used indices
            if current not in st.session_state.used_q_indices:
                st.session_state.used_q_indices.append(current)
            
            # Handle next question logic
            handle_next_question_logic(score, adaptive_mode, False)
        else:
            st.warning("Please provide an answer.")

def handle_selective_mutism_text_input(qa, current, subject):
    """Handle selective mutism text input"""
    backup_answer = UIComponents.display_text_input(qa, current, True)
    
    if UIComponents.display_submit_button("selective_mutism_text"):
        if backup_answer.strip():
            # Evaluate answer
            evaluation = scoring_evaluator.evaluate_answer_selective_mutism(
                qa["question"], qa["answer"], backup_answer, st.session_state.confidence_level
            )
            score = evaluation['score']
            
            st.session_state.all_qas[current]["user_answer"] = backup_answer
            st.session_state.all_qas[current]["score"] = score
            
            # Update confidence and show encouragement
            confidence_update = selective_mutism_support.update_confidence_level(
                score >= 6, 'text'
            )
            
            UIComponents.display_evaluation_result(evaluation, 'selective_mutism')
            st.info("💪 **Great job expressing yourself in writing! You're building communication skills!**")
            
            # Update session state
            st.session_state.confidence_level = selective_mutism_support.state.confidence_level
            st.session_state.success_streak = selective_mutism_support.state.success_streak
            st.session_state.sm_progress_milestones = selective_mutism_support.state.progress_milestones
            
            # Save to database
            save_answer_to_database(current, backup_answer, score, 'selective_mutism_text', subject)
            
            # Add to used indices
            if current not in st.session_state.used_q_indices:
                st.session_state.used_q_indices.append(current)
            
            # Handle next question logic
            handle_next_question_logic(score, False, True)
        else:
            st.warning("💖 Please write something! Even a few words show you're trying.")

def handle_next_question_logic(score, adaptive_mode, selective_mutism_mode):
    """Handle logic for moving to next question"""
    time.sleep(1)  # Short delay to allow user to see the message
    
    # Check if session is complete
    if len(st.session_state.used_q_indices) >= len(st.session_state.all_qas):
        mark_session_complete()
        st.session_state.session_complete = True
        UIComponents.display_final_score_report(st.session_state.all_qas)
        st.success(f"🎉 All questions completed! Total Score: {sum(q.get('score', 0) for q in st.session_state.all_qas if q.get('score') is not None)}/{len(st.session_state.all_qas) * 10}")
    else:
        if adaptive_mode and not selective_mutism_mode:
            # Run adaptive selection
            current_index_before_adaptive = st.session_state.qa_index
            
            # Update adaptive engine
            question_difficulty = qa.get('difficulty', 10)
            recommendations = adaptive_engine.update_state(score, current, question_difficulty)
            
            # Find next question
            next_question_index = adaptive_engine.find_next_question(
                st.session_state.all_qas, st.session_state.used_q_indices
            )
            
            if next_question_index is not None:
                st.session_state.qa_index = next_question_index
                st.session_state.current_difficulty = recommendations['target_difficulty']
                st.info(f"🎯 Adaptive system selected question {st.session_state.qa_index + 1} (Difficulty: {st.session_state.current_difficulty})")
                st.rerun()
            else:
                st.warning("⚠️ No more suitable questions found at current difficulty level.")
        else:
            # Manual mode or selective mutism mode - just proceed to next unanswered question
            next_unanswered = next((i for i, q in enumerate(st.session_state.all_qas) 
                                  if i not in st.session_state.used_q_indices), None)
            if next_unanswered is not None:
                st.session_state.qa_index = next_unanswered
                st.rerun()

def save_answer_to_database(current, answer_text, score, method, subject):
    """Save answer to database"""
    try:
        if st.session_state.current_conversation_id:
            # PDF-generated questions
            questions = db_manager.get_conversation_questions(st.session_state.current_conversation_id)
            if current < len(questions):
                question_id = questions[current]['id']
                db_manager.save_user_answer(question_id, answer_text, score, answer_method=method)
                db_manager.update_user_progress(current_user['id'], subject)
        elif st.session_state.current_predefined_session_id:
            # Predefined questions
            qa = st.session_state.all_qas[current]
            question_id = qa.get('id')
            if question_id:
                db_manager.save_predefined_question_answer(
                    st.session_state.current_predefined_session_id,
                    question_id,
                    answer_text,
                    score,
                    answer_method=method
                )
                db_manager.update_user_progress(current_user['id'], subject)
    except Exception as e:
        st.error(f"Error saving answer: {str(e)}")

def mark_session_complete():
    """Mark session as completed in database"""
    try:
        import sqlite3
        if st.session_state.current_conversation_id:
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE conversations 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (st.session_state.current_conversation_id,))
                conn.commit()
        elif st.session_state.current_predefined_session_id:
            with sqlite3.connect(db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE predefined_question_sessions 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (st.session_state.current_predefined_session_id,))
                conn.commit()
    except Exception as e:
        st.error(f"Error marking session complete: {str(e)}")

def clear_session_state():
    """Clear session state for new session"""
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
    
    # Reset modules
    adaptive_engine.reset_state()
    selective_mutism_support.reset_state()

# ------------------ Run Main Application ------------------
if __name__ == "__main__":
    main()
