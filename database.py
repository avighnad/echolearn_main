import sqlite3
import hashlib
import uuid
from datetime import datetime
import json
from typing import Optional, Dict, List, Tuple

class DatabaseManager:
    def __init__(self, db_path: str = "echolearn.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with all necessary tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # User sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Conversations/Study sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT,
                    name TEXT,
                    grade TEXT,
                    subject TEXT,
                    book_title TEXT,
                    pdf_content TEXT,
                    total_questions INTEGER DEFAULT 0,
                    questions_answered INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0,
                    max_possible_score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    question_order INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # User answers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    user_answer TEXT,
                    score INTEGER,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    time_taken INTEGER,
                    answer_method TEXT DEFAULT 'text',
                    FOREIGN KEY (question_id) REFERENCES questions (id)
                )
            """)
            
            # User progress tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    subject TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    total_questions_answered INTEGER DEFAULT 0,
                    average_score REAL DEFAULT 0.0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.commit()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_session_token(self) -> str:
        """Generate a unique session token"""
        return str(uuid.uuid4())
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> Tuple[bool, str]:
        """Create a new user account"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                password_hash = self.hash_password(password)
                
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, full_name)
                    VALUES (?, ?, ?, ?)
                """, (username, email, password_hash, full_name))
                
                conn.commit()
                return True, "User created successfully"
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already exists"
            elif "email" in str(e):
                return False, "Email already exists"
            else:
                return False, "User creation failed"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """Authenticate a user and return user info"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                password_hash = self.hash_password(password)
                
                cursor.execute("""
                    SELECT id, username, email, full_name, created_at, is_active
                    FROM users 
                    WHERE username = ? AND password_hash = ? AND is_active = 1
                """, (username, password_hash))
                
                user = cursor.fetchone()
                
                if user:
                    # Update last login
                    cursor.execute("""
                        UPDATE users SET last_login = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (user[0],))
                    conn.commit()
                    
                    user_data = {
                        'id': user[0],
                        'username': user[1],
                        'email': user[2],
                        'full_name': user[3],
                        'created_at': user[4],
                        'is_active': user[5]
                    }
                    return True, user_data, "Login successful"
                else:
                    return False, None, "Invalid username or password"
                    
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    def create_session(self, user_id: int) -> str:
        """Create a new session for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                session_token = self.generate_session_token()
                
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, session_token)
                    VALUES (?, ?)
                """, (user_id, session_token))
                
                conn.commit()
                return session_token
        except Exception as e:
            raise Exception(f"Error creating session: {str(e)}")
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate a session token and return user info"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT u.id, u.username, u.email, u.full_name, s.created_at
                    FROM users u
                    JOIN user_sessions s ON u.id = s.user_id
                    WHERE s.session_token = ? AND s.is_active = 1 AND u.is_active = 1
                """, (session_token,))
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': result[0],
                        'username': result[1],
                        'email': result[2],
                        'full_name': result[3],
                        'session_created': result[4]
                    }
                return None
                
        except Exception as e:
            print(f"Session validation error: {str(e)}")
            return None
    
    def create_conversation(self, user_id: int, name: str, grade: str, subject: str, 
                          book_title: str, pdf_content: str = None) -> int:
        """Create a new conversation/study session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO conversations (user_id, name, grade, subject, book_title, pdf_content)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, name, grade, subject, book_title, pdf_content))
                
                conversation_id = cursor.lastrowid
                conn.commit()
                return conversation_id
                
        except Exception as e:
            raise Exception(f"Error creating conversation: {str(e)}")
    
    def save_questions(self, conversation_id: int, questions_data: List[Dict]) -> bool:
        """Save generated questions to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for i, qa in enumerate(questions_data):
                    cursor.execute("""
                        INSERT INTO questions (conversation_id, question_text, correct_answer, 
                                             difficulty_level, question_order)
                        VALUES (?, ?, ?, ?, ?)
                    """, (conversation_id, qa['question'], qa['answer'], 
                         qa['level'], i + 1))
                
                # Update conversation with total questions
                cursor.execute("""
                    UPDATE conversations 
                    SET total_questions = ?, max_possible_score = ?
                    WHERE id = ?
                """, (len(questions_data), len(questions_data) * 10, conversation_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving questions: {str(e)}")
            return False
    
    def save_user_answer(self, question_id: int, user_answer: str, score: int, 
                        time_taken: int = None, answer_method: str = 'text') -> bool:
        """Save a user's answer to a question"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or update user answer
                cursor.execute("""
                    INSERT OR REPLACE INTO user_answers 
                    (question_id, user_answer, score, time_taken, answer_method)
                    VALUES (?, ?, ?, ?, ?)
                """, (question_id, user_answer, score, time_taken, answer_method))
                
                # Update conversation progress
                cursor.execute("""
                    SELECT conversation_id FROM questions WHERE id = ?
                """, (question_id,))
                conversation_id = cursor.fetchone()[0]
                
                # Calculate current progress
                cursor.execute("""
                    SELECT COUNT(*), SUM(score)
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE q.conversation_id = ?
                """, (conversation_id,))
                
                answered, total_score = cursor.fetchone()
                answered = answered or 0
                total_score = total_score or 0
                
                cursor.execute("""
                    UPDATE conversations 
                    SET questions_answered = ?, total_score = ?
                    WHERE id = ?
                """, (answered, total_score, conversation_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving user answer: {str(e)}")
            return False
    
    def get_conversation_questions(self, conversation_id: int) -> List[Dict]:
        """Get all questions for a conversation with user answers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT q.id, q.question_text, q.correct_answer, q.difficulty_level,
                           q.question_order, ua.user_answer, ua.score, ua.answered_at
                    FROM questions q
                    LEFT JOIN user_answers ua ON q.id = ua.question_id
                    WHERE q.conversation_id = ?
                    ORDER BY q.question_order
                """, (conversation_id,))
                
                questions = []
                for row in cursor.fetchall():
                    questions.append({
                        'id': row[0],
                        'question': row[1],
                        'answer': row[2],
                        'level': row[3],
                        'order': row[4],
                        'user_answer': row[5] or '',
                        'score': row[6],
                        'answered_at': row[7]
                    })
                
                return questions
                
        except Exception as e:
            print(f"Error getting conversation questions: {str(e)}")
            return []
    
    def get_user_conversations(self, user_id: int) -> List[Dict]:
        """Get all conversations for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, grade, subject, book_title, total_questions,
                           questions_answered, total_score, max_possible_score,
                           status, created_at, completed_at
                    FROM conversations
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))
                
                conversations = []
                for row in cursor.fetchall():
                    conversations.append({
                        'id': row[0],
                        'name': row[1],
                        'grade': row[2],
                        'subject': row[3],
                        'book_title': row[4],
                        'total_questions': row[5],
                        'questions_answered': row[6],
                        'total_score': row[7],
                        'max_possible_score': row[8],
                        'status': row[9],
                        'created_at': row[10],
                        'completed_at': row[11]
                    })
                
                return conversations
                
        except Exception as e:
            print(f"Error getting user conversations: {str(e)}")
            return []
    
    def update_user_progress(self, user_id: int, subject: str):
        """Update user's overall progress statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate progress stats
                cursor.execute("""
                    SELECT COUNT(DISTINCT c.id) as sessions,
                           COUNT(ua.id) as total_answers,
                           AVG(CAST(ua.score as FLOAT)) as avg_score
                    FROM conversations c
                    LEFT JOIN questions q ON c.id = q.conversation_id
                    LEFT JOIN user_answers ua ON q.id = ua.question_id
                    WHERE c.user_id = ? AND c.subject = ?
                """, (user_id, subject))
                
                result = cursor.fetchone()
                sessions, total_answers, avg_score = result
                sessions = sessions or 0
                total_answers = total_answers or 0
                avg_score = avg_score or 0.0
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_progress 
                    (user_id, subject, total_sessions, total_questions_answered, 
                     average_score, last_activity)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, subject, sessions, total_answers, avg_score))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error updating user progress: {str(e)}")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user's overall statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT subject, total_sessions, total_questions_answered,
                           average_score, last_activity
                    FROM user_progress
                    WHERE user_id = ?
                """, (user_id,))
                
                progress = {}
                for row in cursor.fetchall():
                    progress[row[0]] = {
                        'sessions': row[1],
                        'questions_answered': row[2],
                        'average_score': row[3],
                        'last_activity': row[4]
                    }
                
                return progress
                
        except Exception as e:
            print(f"Error getting user stats: {str(e)}")
            return {}

# Global database instance
db_manager = DatabaseManager()
