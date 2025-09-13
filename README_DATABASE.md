# Echolearn Database Integration

## Overview

The Echolearn application now includes comprehensive SQLite database integration with user authentication, conversation tracking, and data retention capabilities.

## New Features

### 🔐 User Authentication
- **User Registration**: Create new accounts with username, email, and password
- **Secure Login**: Password hashing with SHA256
- **Session Management**: Persistent login sessions
- **User Profile**: View user information in sidebar

### 💾 Data Persistence
- **Conversation Tracking**: All study sessions are saved to database
- **Question Storage**: Generated questions and correct answers are stored
- **Answer Recording**: User answers and scores are permanently saved
- **Progress Tracking**: Overall user progress and statistics

### 📊 Enhanced Features
- **Resume Sessions**: Continue previous study sessions
- **User Dashboard**: View statistics and recent activity
- **Session History**: Access all previous study sessions
- **Progress Analytics**: Subject-wise breakdown of performance

## Database Schema

The application uses SQLite with the following main tables:
- `users`: User account information
- `conversations`: Study sessions with metadata
- `questions`: Generated viva questions
- `user_answers`: Student responses and scores
- `user_progress`: Aggregated statistics

## How to Use

### First Time Setup
1. Run the application: `streamlit run echo.py`
2. You'll see the authentication screen
3. Click "Register" tab to create a new account
4. Fill in username, email, and password
5. Click "Register" button

### Logging In
1. Use the "Login" tab on the authentication screen
2. Enter your username and password
3. Click "Login" button

### Using the Application
1. After login, you'll see your dashboard with statistics
2. Start a new study session by filling in the form
3. Upload a PDF file for question generation
4. The app will automatically save your session to the database
5. Generated questions and your answers are saved in real-time

### Resuming Sessions
1. From the dashboard, click "Resume Session" on any incomplete session
2. The app will load your previous progress
3. Continue from where you left off

## Files Added

- `database.py`: Database management and operations
- `auth.py`: User authentication and session management
- `echolearn.db`: SQLite database file (created automatically)

## Files Modified

- `echo.py`: Enhanced with database integration and authentication

## Key Improvements

1. **User Management**: Each user has their own isolated data
2. **Data Persistence**: No more lost progress when browser closes
3. **Session History**: Review past performance and track improvement
4. **Enhanced Security**: Secure password storage and session management
5. **Progress Analytics**: Detailed insights into learning progress

## Database Operations

The system automatically handles:
- Creating user accounts
- Saving study sessions
- Storing generated questions
- Recording user answers and scores
- Calculating progress statistics
- Managing session tokens

## Technical Details

- **Database**: SQLite (file-based, no server required)
- **ORM**: Pure SQL with sqlite3 module
- **Authentication**: Session token-based
- **Password Security**: SHA256 hashing
- **Data Integrity**: Foreign key constraints and validation

## Troubleshooting

If you encounter any issues:
1. Make sure you have write permissions in the application directory
2. Check that `database.py` and `auth.py` are in the same directory as `echo.py`
3. The SQLite database file will be created automatically on first run
4. If database issues persist, delete `echolearn.db` and restart the app

## Benefits

✅ **Secure**: User data is protected with authentication  
✅ **Persistent**: Progress is never lost  
✅ **Scalable**: Can handle multiple users  
✅ **Analytical**: Rich progress tracking and statistics  
✅ **User-Friendly**: Seamless integration with existing workflow  
