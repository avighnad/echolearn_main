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
            
            # Subjects table for predefined question bank
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Topics table for organizing questions within subjects
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    UNIQUE(subject_id, name)
                )
            """)
            
            # Predefined question bank
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_bank (
                    id TEXT PRIMARY KEY,
                    subject_id INTEGER NOT NULL,
                    topic_id INTEGER,
                    grade TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    difficulty REAL NOT NULL,
                    audio_heavy BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    FOREIGN KEY (topic_id) REFERENCES topics (id)
                )
            """)
            
            # Predefined question sessions - tracks when users work on predefined questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predefined_question_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT,
                    grade TEXT,
                    subject_id INTEGER,
                    topic_id INTEGER,
                    difficulty_range_min REAL DEFAULT 1.0,
                    difficulty_range_max REAL DEFAULT 100.0,
                    total_questions INTEGER DEFAULT 0,
                    questions_answered INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0,
                    max_possible_score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    FOREIGN KEY (topic_id) REFERENCES topics (id)
                )
            """)
            
            # Predefined question answers - tracks user answers to predefined questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predefined_question_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    user_answer TEXT,
                    score INTEGER,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    time_taken INTEGER,
                    answer_method TEXT DEFAULT 'text',
                    FOREIGN KEY (session_id) REFERENCES predefined_question_sessions (id),
                    FOREIGN KEY (question_id) REFERENCES question_bank (id),
                    UNIQUE(session_id, question_id)
                )
            """)
            
            conn.commit()
            
            # Initialize default subjects and basic data
            self._initialize_default_data()
    
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
    
    def _initialize_default_data(self):
        """Initialize default subjects and sample question data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add default subjects if they don't exist
                subjects = ['Economics', 'Chemistry', 'Physics', 'Mathematics']
                for subject in subjects:
                    cursor.execute("""
                        INSERT OR IGNORE INTO subjects (name, description) 
                        VALUES (?, ?)
                    """, (subject, f"{subject} questions for various grade levels"))
                
                conn.commit()
                
                # Add sample questions if question bank is empty
                cursor.execute("SELECT COUNT(*) FROM question_bank")
                if cursor.fetchone()[0] == 0:
                    self._add_sample_questions()
                    
        except Exception as e:
            print(f"Error initializing default data: {str(e)}")
    
    def _add_sample_questions(self):
        """Add sample questions from user data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get subject IDs
                cursor.execute("SELECT id, name FROM subjects")
                subject_map = {name: id for id, name in cursor.fetchall()}
                
                # Sample questions data based on user's provided data
                sample_questions = [
                    # Economics questions
                    {
                        'id': '23f31',
                        'subject': 'Economics',
                        'topic': 'Production Possibilities',
                        'grade': '11',
                        'question': 'Explain why, for an economy operating at a point on its production possibilities curve (PPC), choices about what to produce might be necessary. [10]',
                        'answer': 'When an economy operates on its PPC, it is using all its resources efficiently. At this point, producing more of one good requires sacrificing some of another good due to resource constraints and opportunity cost. Choices are necessary because: 1) Resources are scarce relative to wants, 2) Different combinations of goods can be produced along the PPC, 3) Society must decide which combination best meets its needs and preferences, 4) Opportunity cost exists - choosing more of one good means less of another.',
                        'difficulty': 25,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ec001',
                        'subject': 'Economics',
                        'topic': 'Economic Models',
                        'grade': '11',
                        'question': 'Explain why economists employ the ceteris paribus assumption when modelling and predicting economic activity.[2] Comment on John Maynard Keynes\'s impact on the government\'s role in the economy.[2]',
                        'answer': 'Ceteris paribus (other things being equal) allows economists to isolate the effect of one variable by assuming all other variables remain constant, making complex economic relationships easier to analyze and understand. Keynes revolutionized economics by arguing that government intervention was necessary to address market failures and economic downturns, particularly through fiscal policy and demand management, shifting away from classical free-market approaches.',
                        'difficulty': 20,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ec002',
                        'subject': 'Economics',
                        'topic': 'Supply and Demand',
                        'grade': '11',
                        'question': 'Explain one reason for increased quantity supplied and one reason for an increase in supply.',
                        'answer': 'Increased quantity supplied occurs when price increases, causing producers to move along the same supply curve to produce more at the higher price. An increase in supply occurs when the entire supply curve shifts right due to factors like: lower production costs, improved technology, government subsidies, or favorable weather conditions, allowing producers to supply more at every price level.',
                        'difficulty': 30,
                        'audio_heavy': True
                    },
                    
                    # Chemistry questions  
                    {
                        'id': '89gh2',
                        'subject': 'Chemistry',
                        'topic': 'Atomic Structure',
                        'grade': '11', 
                        'question': 'The atom of element X has a mass number of 127 and has 74 neutrons. The ion derived from X has 54 electrons. Calculate the number of protons of element X. [1] State the nuclear symbol of the ion formed (refer to the periodic table). [2] An isotope of X has a mass number of 132. Determine the number of neutrons in its atom. [2]',
                        'answer': 'Number of protons = Mass number - Neutrons = 127 - 74 = 53 protons. Since the ion has 54 electrons and the atom has 53 protons, this is an anion with charge -1. Element with 53 protons is Iodine (I). Nuclear symbol: ¹²⁷I⁻. For the isotope with mass number 132: Number of neutrons = 132 - 53 = 79 neutrons.',
                        'difficulty': 16,
                        'audio_heavy': False
                    },
                    
                    # Physics questions
                    {
                        'id': 'ph001',
                        'subject': 'Physics',
                        'topic': 'Energy and Motion',
                        'grade': '11',
                        'question': 'A ball is released from rest at the top of a frictionless incline. Explain, using energy considerations, why the ball accelerates as it moves down the slope.',
                        'answer': 'Initially, the ball has maximum gravitational potential energy (PE = mgh) and zero kinetic energy. As it moves down the incline, potential energy converts to kinetic energy (KE = ½mv²). Since total mechanical energy is conserved on a frictionless surface, the loss in potential energy equals the gain in kinetic energy. As kinetic energy increases, velocity increases, meaning the ball accelerates down the slope.',
                        'difficulty': 35,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ph002',
                        'subject': 'Physics',
                        'topic': 'Kinetic Theory',
                        'grade': '11',
                        'question': 'Describe how the kinetic model of matter explains the pressure exerted by a gas in a container.',
                        'answer': 'According to kinetic theory, gas molecules are in constant random motion, colliding elastically with container walls. Each collision exerts a small force on the wall. With billions of molecules colliding per second, these individual forces combine to create a steady pressure. Pressure depends on: 1) Number of collisions per unit time, 2) Average force per collision (related to molecular speed/kinetic energy), 3) Temperature (higher temperature = faster molecules = more frequent, harder collisions).',
                        'difficulty': 45,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ph003',
                        'subject': 'Physics',
                        'topic': 'Waves',
                        'grade': '11',
                        'question': 'Outline how the principle of superposition leads to the formation of standing waves in a stretched string fixed at both ends.',
                        'answer': 'When a wave travels down the string and reflects from the fixed ends, incident and reflected waves travel in opposite directions. According to superposition principle, these waves combine algebraically. At specific frequencies, constructive interference creates nodes (points of zero amplitude) and antinodes (points of maximum amplitude) at fixed positions. The wavelength relationship λ = 2L/n (where L is string length, n is harmonic number) ensures waves fit exactly between fixed ends, creating stable standing wave patterns.',
                        'difficulty': 25,
                        'audio_heavy': True
                    },
                    
                    # Additional Economics questions from user data
                    {
                        'id': 'ec003',
                        'subject': 'Economics',
                        'topic': 'Market Analysis',
                        'grade': '11',
                        'question': 'Using a demand and supply diagram, explain how the lack of infrastructure may have affected the manufacturing sector in Colombia. [4]',
                        'answer': 'Lack of infrastructure increases production costs for manufacturers. This shifts the supply curve leftward (decrease in supply), resulting in higher equilibrium price and lower equilibrium quantity. The diagram would show: 1) Original supply curve S1, 2) New supply curve S2 (shifted left), 3) Higher price P2 vs P1, 4) Lower quantity Q2 vs Q1. This reduces competitiveness and output in the manufacturing sector.',
                        'difficulty': 45,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ec004',
                        'subject': 'Economics',
                        'topic': 'Market Relationships',
                        'grade': '11',
                        'question': 'Sketch a demand and supply diagram to show the effect of an increase in the price of mate gourds on the bombilla market.[3] Using your answer, outline why a change in the price of mate gourds impacts the bombilla market.[2]',
                        'answer': 'Mate gourds and bombillas are complementary goods. When gourd prices increase: 1) Demand for gourds decreases, 2) This reduces demand for bombillas (leftward shift of demand curve), 3) Results in lower equilibrium price and quantity for bombillas. The impact occurs because complementary goods are consumed together - when one becomes more expensive, demand for both products falls.',
                        'difficulty': 42,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ec005',
                        'subject': 'Economics',
                        'topic': 'Supply Relationships',
                        'grade': '11',
                        'question': 'Explain how an increase in the price of beef might affect the supply of leather and the supply of poultry. [10]',
                        'answer': 'Beef and leather are joint products (produced together from cattle). Higher beef prices increase cattle slaughter, increasing leather supply (rightward shift). For poultry: beef and chicken are substitute goods in consumption. Higher beef prices increase poultry demand, raising poultry prices and encouraging increased poultry supply (rightward shift). Both effects demonstrate how price changes in one market can create spillover effects in related markets through production and consumption linkages.',
                        'difficulty': 46,
                        'audio_heavy': True
                    },
                    
                    # Additional Physics questions
                    {
                        'id': 'ph004',
                        'subject': 'Physics',
                        'topic': 'Electromagnetism',
                        'grade': '11',
                        'question': 'Explain, with reference to electron flow, why a current-carrying conductor placed in a magnetic field experiences a force.',
                        'answer': 'When current flows through a conductor, electrons move in a specific direction. In a magnetic field, moving charged particles experience a magnetic force (Lorentz force). The force on each electron is F = qvB sinθ, where q is electron charge, v is drift velocity, and B is magnetic field strength. The collective effect of forces on all moving electrons is transmitted to the conductor itself, causing the conductor to experience a net force in the direction given by Fleming\'s left-hand rule.',
                        'difficulty': 50,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ph005',
                        'subject': 'Physics',
                        'topic': 'Orbital Mechanics',
                        'grade': '11',
                        'question': 'Explain why satellites in orbit around Earth are said to be in "free fall" even though they do not appear to fall towards Earth.',
                        'answer': 'Satellites are in continuous free fall toward Earth under gravitational force. However, they also have sufficient horizontal velocity that as they fall, Earth\'s curved surface falls away beneath them at the same rate. This creates a stable orbit where the satellite is always falling but never getting closer to Earth\'s surface. The centripetal acceleration (v²/r) exactly equals gravitational acceleration (GM/r²), maintaining constant orbital radius.',
                        'difficulty': 35,
                        'audio_heavy': True
                    },
                    {
                        'id': 'ph006',
                        'subject': 'Physics',
                        'topic': 'Quantum Physics',
                        'grade': '11',
                        'question': 'Explain why the emission spectrum of hydrogen contains only specific wavelengths of light.',
                        'answer': 'According to the Bohr model, electrons in hydrogen atoms can only occupy specific energy levels (quantized energy states). When an electron transitions from a higher energy level to a lower one, it emits a photon with energy equal to the energy difference (E = hf). Since only specific energy level transitions are possible, only specific photon energies (and therefore wavelengths) are emitted, creating the characteristic line spectrum with discrete wavelengths rather than a continuous spectrum.',
                        'difficulty': 60,
                        'audio_heavy': True
                    },
                    
                    # Additional Chemistry questions
                    {
                        'id': 'ch001',
                        'subject': 'Chemistry',
                        'topic': 'Chemical Bonding',
                        'grade': '11',
                        'question': 'Explain the difference between ionic and covalent bonding, giving one example of each.',
                        'answer': 'Ionic bonding occurs when electrons are transferred from one atom to another, creating charged ions that attract electrostatically. Example: NaCl (sodium chloride) - sodium loses an electron to become Na+, chlorine gains an electron to become Cl-. Covalent bonding occurs when atoms share electrons to achieve stable electron configurations. Example: H2O (water) - oxygen shares electrons with two hydrogen atoms, forming polar covalent bonds.',
                        'difficulty': 20,
                        'audio_heavy': False
                    },
                    
                    # Mathematics questions
                    {
                        'id': 'ma001',
                        'subject': 'Mathematics',
                        'topic': 'Calculus',
                        'grade': '11',
                        'question': 'Find the derivative of f(x) = 3x² + 5x - 2 using the power rule.',
                        'answer': 'Using the power rule d/dx(x^n) = nx^(n-1) and the fact that derivatives are linear: f\'(x) = d/dx(3x²) + d/dx(5x) - d/dx(2) = 3(2x¹) + 5(1x⁰) - 0 = 6x + 5. Therefore, f\'(x) = 6x + 5.',
                        'difficulty': 15,
                        'audio_heavy': False
                    },
                    {
                        'id': 'ma002',
                        'subject': 'Mathematics',
                        'topic': 'Trigonometry',
                        'grade': '11',
                        'question': 'Solve the equation sin(2θ) = √3/2 for 0° ≤ θ ≤ 180°.',
                        'answer': 'First, find when sin(2θ) = √3/2. This occurs when 2θ = 60° or 2θ = 120° (in the range 0° to 360°). Solving for θ: When 2θ = 60°, θ = 30°. When 2θ = 120°, θ = 60°. We also need to consider that sin is positive in both first and second quadrants, so 2θ could also equal 180° - 60° = 120° or 180° - 120° = 60°. However, checking our range 0° ≤ θ ≤ 180°, the solutions are θ = 30° and θ = 60°.',
                        'difficulty': 35,
                        'audio_heavy': False
                    }
                ]
                
                # Insert sample questions
                for q in sample_questions:
                    subject_id = subject_map.get(q['subject'])
                    if subject_id:
                        # Create topic if it doesn't exist
                        cursor.execute("""
                            INSERT OR IGNORE INTO topics (subject_id, name, description) 
                            VALUES (?, ?, ?)
                        """, (subject_id, q['topic'], f"{q['topic']} questions for {q['subject']}"))
                        
                        # Get topic ID
                        cursor.execute("""
                            SELECT id FROM topics WHERE subject_id = ? AND name = ?
                        """, (subject_id, q['topic']))
                        topic_id = cursor.fetchone()[0]
                        
                        # Insert question
                        cursor.execute("""
                            INSERT OR IGNORE INTO question_bank 
                            (id, subject_id, topic_id, grade, question_text, answer_text, difficulty, audio_heavy)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (q['id'], subject_id, topic_id, q['grade'], q['question'], 
                             q['answer'], q['difficulty'], q['audio_heavy']))
                
                conn.commit()
                
        except Exception as e:
            print(f"Error adding sample questions: {str(e)}")
    
    def get_subjects(self) -> List[Dict]:
        """Get all available subjects"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description FROM subjects ORDER BY name")
                return [{'id': row[0], 'name': row[1], 'description': row[2]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting subjects: {str(e)}")
            return []
    
    def get_topics_by_subject(self, subject_id: int) -> List[Dict]:
        """Get all topics for a specific subject"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, description FROM topics 
                    WHERE subject_id = ? ORDER BY name
                """, (subject_id,))
                return [{'id': row[0], 'name': row[1], 'description': row[2]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting topics: {str(e)}")
            return []
    
    def get_grades_by_subject(self, subject_id: int) -> List[str]:
        """Get available grades for a specific subject"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT grade FROM question_bank 
                    WHERE subject_id = ? ORDER BY grade
                """, (subject_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting grades: {str(e)}")
            return []
    
    def get_predefined_questions(self, subject_id: int = None, topic_id: int = None, 
                               grade: str = None, difficulty_min: float = 1.0, 
                               difficulty_max: float = 100.0, limit: int = None) -> List[Dict]:
        """Get predefined questions based on filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT qb.id, s.name as subject, t.name as topic, qb.grade,
                           qb.question_text, qb.answer_text, qb.difficulty, qb.audio_heavy
                    FROM question_bank qb
                    JOIN subjects s ON qb.subject_id = s.id
                    LEFT JOIN topics t ON qb.topic_id = t.id
                    WHERE qb.difficulty BETWEEN ? AND ?
                """
                params = [difficulty_min, difficulty_max]
                
                if subject_id:
                    query += " AND qb.subject_id = ?"
                    params.append(subject_id)
                
                if topic_id:
                    query += " AND qb.topic_id = ?"
                    params.append(topic_id)
                
                if grade:
                    query += " AND qb.grade = ?"
                    params.append(grade)
                
                query += " ORDER BY qb.difficulty, qb.id"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query, params)
                
                questions = []
                for row in cursor.fetchall():
                    questions.append({
                        'id': row[0],
                        'subject': row[1],
                        'topic': row[2],
                        'grade': row[3],
                        'question': row[4],
                        'answer': row[5],
                        'difficulty': row[6],
                        'audio_heavy': row[7],
                        'level': self._get_difficulty_level(row[6])
                    })
                
                return questions
                
        except Exception as e:
            print(f"Error getting predefined questions: {str(e)}")
            return []
    
    def _get_difficulty_level(self, difficulty: float) -> str:
        """Convert numeric difficulty to text level"""
        if difficulty <= 30:
            return "Easy"
        elif difficulty <= 60:
            return "Moderate"
        else:
            return "Difficult"
    
    def create_predefined_question_session(self, user_id: int, name: str, grade: str,
                                         subject_id: int, topic_id: int = None,
                                         difficulty_min: float = 1.0, difficulty_max: float = 100.0) -> int:
        """Create a new session for predefined questions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO predefined_question_sessions 
                    (user_id, name, grade, subject_id, topic_id, difficulty_range_min, difficulty_range_max)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, name, grade, subject_id, topic_id, difficulty_min, difficulty_max))
                
                session_id = cursor.lastrowid
                
                # Count available questions for this session
                question_count_query = """
                    SELECT COUNT(*) FROM question_bank 
                    WHERE subject_id = ? AND difficulty BETWEEN ? AND ?
                """
                params = [subject_id, difficulty_min, difficulty_max]
                
                if grade:
                    question_count_query += " AND grade = ?"
                    params.append(grade)
                
                if topic_id:
                    question_count_query += " AND topic_id = ?"
                    params.append(topic_id)
                
                cursor.execute(question_count_query, params)
                total_questions = cursor.fetchone()[0]
                
                # Update session with question count
                cursor.execute("""
                    UPDATE predefined_question_sessions 
                    SET total_questions = ?, max_possible_score = ?
                    WHERE id = ?
                """, (total_questions, total_questions * 10, session_id))
                
                conn.commit()
                return session_id
                
        except Exception as e:
            print(f"Error creating predefined question session: {str(e)}")
            raise Exception(f"Error creating session: {str(e)}")
    
    def save_predefined_question_answer(self, session_id: int, question_id: str, 
                                      user_answer: str, score: int, 
                                      time_taken: int = None, answer_method: str = 'text') -> bool:
        """Save a user's answer to a predefined question"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or update answer
                cursor.execute("""
                    INSERT OR REPLACE INTO predefined_question_answers 
                    (session_id, question_id, user_answer, score, time_taken, answer_method)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, question_id, user_answer, score, time_taken, answer_method))
                
                # Update session progress
                cursor.execute("""
                    SELECT COUNT(*), SUM(score) FROM predefined_question_answers 
                    WHERE session_id = ?
                """, (session_id,))
                
                answered, total_score = cursor.fetchone()
                answered = answered or 0
                total_score = total_score or 0
                
                cursor.execute("""
                    UPDATE predefined_question_sessions 
                    SET questions_answered = ?, total_score = ?
                    WHERE id = ?
                """, (answered, total_score, session_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving predefined question answer: {str(e)}")
            return False
    
    def get_predefined_session_questions(self, session_id: int) -> Tuple[Dict, List[Dict]]:
        """Get session info and its questions with user answers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get session info
                cursor.execute("""
                    SELECT pqs.*, s.name as subject_name, t.name as topic_name
                    FROM predefined_question_sessions pqs
                    JOIN subjects s ON pqs.subject_id = s.id
                    LEFT JOIN topics t ON pqs.topic_id = t.id
                    WHERE pqs.id = ?
                """, (session_id,))
                
                session_row = cursor.fetchone()
                if not session_row:
                    return None, []
                
                session_info = {
                    'id': session_row[0],
                    'user_id': session_row[1],
                    'name': session_row[2],
                    'grade': session_row[3],
                    'subject_id': session_row[4],
                    'topic_id': session_row[5],
                    'difficulty_min': session_row[6],
                    'difficulty_max': session_row[7],
                    'total_questions': session_row[8],
                    'questions_answered': session_row[9],
                    'total_score': session_row[10],
                    'max_possible_score': session_row[11],
                    'status': session_row[12],
                    'created_at': session_row[13],
                    'completed_at': session_row[14],
                    'subject_name': session_row[15],
                    'topic_name': session_row[16]
                }
                
                # Get questions with user answers
                questions = self.get_predefined_questions(
                    subject_id=session_info['subject_id'],
                    topic_id=session_info['topic_id'],
                    grade=session_info['grade'],
                    difficulty_min=session_info['difficulty_min'],
                    difficulty_max=session_info['difficulty_max']
                )
                
                # Add user answer info
                for question in questions:
                    cursor.execute("""
                        SELECT user_answer, score, answered_at, answer_method
                        FROM predefined_question_answers
                        WHERE session_id = ? AND question_id = ?
                    """, (session_id, question['id']))
                    
                    answer_row = cursor.fetchone()
                    if answer_row:
                        question['user_answer'] = answer_row[0]
                        question['score'] = answer_row[1]
                        question['answered_at'] = answer_row[2]
                        question['answer_method'] = answer_row[3]
                    else:
                        question['user_answer'] = ''
                        question['score'] = None
                        question['answered_at'] = None
                        question['answer_method'] = None
                
                return session_info, questions
                
        except Exception as e:
            print(f"Error getting predefined session questions: {str(e)}")
            return None, []
    
    def get_user_predefined_sessions(self, user_id: int) -> List[Dict]:
        """Get all predefined question sessions for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT pqs.id, pqs.name, pqs.grade, s.name as subject_name, 
                           t.name as topic_name, pqs.total_questions, pqs.questions_answered,
                           pqs.total_score, pqs.max_possible_score, pqs.status,
                           pqs.created_at, pqs.completed_at
                    FROM predefined_question_sessions pqs
                    JOIN subjects s ON pqs.subject_id = s.id
                    LEFT JOIN topics t ON pqs.topic_id = t.id
                    WHERE pqs.user_id = ?
                    ORDER BY pqs.created_at DESC
                """, (user_id,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        'id': row[0],
                        'name': row[1],
                        'grade': row[2],
                        'subject': row[3],
                        'topic': row[4],
                        'total_questions': row[5],
                        'questions_answered': row[6],
                        'total_score': row[7],
                        'max_possible_score': row[8],
                        'status': row[9],
                        'created_at': row[10],
                        'completed_at': row[11]
                    })
                
                return sessions
                
        except Exception as e:
            print(f"Error getting user predefined sessions: {str(e)}")
            return []

# Global database instance
db_manager = DatabaseManager()
