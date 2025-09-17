import streamlit as st
from database import db_manager
import re
from typing import Optional, Dict, Tuple

class AuthManager:
    def __init__(self):
        self.db = db_manager
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
    
    def is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def is_valid_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        if not re.search(r'[A-Za-z]', password):
            return False, "Password must contain at least one letter"
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    def login_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Login a user"""
        if not username or not password:
            return False, "Please enter both username and password"
        
        success, user_data, message = self.db.authenticate_user(username, password)
        
        if success:
            # Create session
            session_token = self.db.create_session(user_data['id'])
            
            # Store in session state
            st.session_state.authenticated = True
            st.session_state.user_data = user_data
            st.session_state.session_token = session_token
            
            return True, message
        else:
            return False, message
    
    def register_user(self, username: str, email: str, password: str, 
                     confirm_password: str, full_name: str = "") -> Tuple[bool, str]:
        """Register a new user"""
        # Validation
        if not username or not email or not password:
            return False, "Please fill in all required fields"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if not self.is_valid_email(email):
            return False, "Please enter a valid email address"
        
        if password != confirm_password:
            return False, "Passwords do not match"
        
        is_valid, password_message = self.is_valid_password(password)
        if not is_valid:
            return False, password_message
        
        # Create user
        success, message = self.db.create_user(username, email, password, full_name)
        return success, message
    
    def logout_user(self):
        """Logout current user"""
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.session_token = None
    
    def check_session(self) -> bool:
        """Check if current session is valid"""
        if not st.session_state.get('session_token'):
            return False
        
        user_data = self.db.validate_session(st.session_state.session_token)
        if user_data:
            st.session_state.user_data = user_data
            st.session_state.authenticated = True
            return True
        else:
            self.logout_user()
            return False
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user data"""
        if st.session_state.authenticated and st.session_state.user_data:
            return st.session_state.user_data
        return None
    
    def require_authentication(self):
        """Require user to be authenticated to continue"""
        if not self.check_session():
            self.show_auth_ui()
            st.stop()
    
    def show_auth_ui(self):
        """Show login/registration UI"""
        st.title("🎓 Echolearn Authentication")
        
        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            self.show_login_form()
        
        with tab2:
            self.show_register_form()
    
    def show_login_form(self):
        """Show login form"""
        st.subheader("Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                success, message = self.login_user(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    def show_register_form(self):
        """Show registration form"""
        st.subheader("Create New Account")
        
        with st.form("register_form"):
            full_name = st.text_input("Full Name (Optional)", key="reg_full_name")
            username = st.text_input("Username*", key="reg_username")
            email = st.text_input("Email*", key="reg_email")
            password = st.text_input("Password*", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password*", type="password", key="reg_confirm")
            
            st.caption("* Required fields")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                submit = st.form_submit_button("Register", use_container_width=True)
            
            if submit:
                success, message = self.register_user(username, email, password, 
                                                   confirm_password, full_name)
                if success:
                    st.success(f"{message}! Please login with your new account.")
                else:
                    st.error(message)
    
    def show_user_profile_sidebar(self):
        """Show user profile information in sidebar"""
        if st.session_state.authenticated and st.session_state.user_data:
            user = st.session_state.user_data
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("👤 User Profile")
            st.sidebar.write(f"**Name:** {user.get('full_name', 'N/A')}")
            st.sidebar.write(f"**Username:** {user['username']}")
            st.sidebar.write(f"**Email:** {user['email']}")
            
            if st.sidebar.button("Logout", key="logout_btn"):
                self.logout_user()
                st.rerun()
            
            st.sidebar.markdown("---")
    
    def show_user_dashboard(self):
        """Show user dashboard with statistics and recent activity"""
        if not st.session_state.authenticated:
            return
        
        user = st.session_state.user_data
        
        st.subheader(f"Welcome back, {user.get('full_name', user['username'])}! 👋")
        
        # Get user statistics
        user_stats = self.db.get_user_stats(user['id'])
        conversations = self.db.get_user_conversations(user['id'])
        predefined_sessions = self.db.get_user_predefined_sessions(user['id'])
        
        # Show statistics
        if user_stats:
            st.subheader("📊 Your Progress")
            
            col1, col2, col3, col4 = st.columns(4)
            
            total_sessions = sum(stats['sessions'] for stats in user_stats.values())
            total_questions = sum(stats['questions_answered'] for stats in user_stats.values())
            avg_score = sum(stats['average_score'] * stats['questions_answered'] for stats in user_stats.values()) / total_questions if total_questions > 0 else 0
            subjects_studied = len(user_stats)
            
            col1.metric("Total Sessions", total_sessions)
            col2.metric("Questions Answered", total_questions)
            col3.metric("Average Score", f"{avg_score:.1f}/10")
            col4.metric("Subjects Studied", subjects_studied)
            
            # Show subject-wise breakdown
            if len(user_stats) > 1:
                st.subheader("📚 Subject Breakdown")
                for subject, stats in user_stats.items():
                    with st.expander(f"{subject} - {stats['sessions']} sessions"):
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Sessions:** {stats['sessions']}")
                        col2.write(f"**Questions:** {stats['questions_answered']}")
                        col3.write(f"**Avg Score:** {stats['average_score']:.1f}/10")
        
        # Show recent study sessions (both PDF and predefined)
        if conversations or predefined_sessions:
            st.subheader("📖 Recent Study Sessions")
            
            # Combine and sort all sessions by creation date
            all_sessions = []
            
            # Add PDF-based conversations
            for conv in conversations:
                all_sessions.append({
                    'type': 'pdf',
                    'id': conv['id'],
                    'title': f"📄 {conv['subject']} - {conv['book_title']}",
                    'created_at': conv['created_at'],
                    'grade': conv['grade'],
                    'questions_answered': conv['questions_answered'],
                    'total_questions': conv['total_questions'],
                    'total_score': conv['total_score'],
                    'max_possible_score': conv['max_possible_score'],
                    'status': conv['status']
                })
            
            # Add predefined question sessions
            for session in predefined_sessions:
                topic_display = f" - {session['topic']}" if session['topic'] else ""
                all_sessions.append({
                    'type': 'predefined',
                    'id': session['id'],
                    'title': f"📋 {session['subject']}{topic_display}",
                    'created_at': session['created_at'],
                    'grade': session['grade'],
                    'questions_answered': session['questions_answered'],
                    'total_questions': session['total_questions'],
                    'total_score': session['total_score'],
                    'max_possible_score': session['max_possible_score'],
                    'status': session['status']
                })
            
            # Sort by creation date (newest first)
            all_sessions.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Show last 8 sessions
            for session in all_sessions[:8]:
                with st.expander(f"{session['title']} ({session['created_at'][:10]})"):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.write(f"**Grade:** {session['grade']}")
                    col2.write(f"**Questions:** {session['questions_answered']}/{session['total_questions']}")
                    col3.write(f"**Score:** {session['total_score']}/{session['max_possible_score']}")
                    col4.write(f"**Status:** {session['status'].title()}")
                    
                    resume_key = f"resume_{session['type']}_{session['id']}"
                    if st.button(f"Resume Session", key=resume_key):
                        if session['type'] == 'pdf':
                            st.session_state.current_conversation_id = session['id']
                            st.session_state.resume_session = True
                        else:  # predefined
                            st.session_state.current_predefined_session_id = session['id']
                            st.session_state.resume_predefined_session = True
                        st.rerun()

# Global auth manager instance
auth_manager = AuthManager()
