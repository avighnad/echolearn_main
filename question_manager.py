# -*- coding: utf-8 -*-
"""
Question Manager Module for EchoLearn
Handles question generation, parsing, and management
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from langchain.llms import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionGenerator:
    """Handles question generation from PDF content"""
    
    def __init__(self, llm: OpenAI):
        self.llm = llm
    
    def generate_questions_from_pdf(self, pdf_content: str, num_questions: int = 20) -> List[Dict]:
        """
        Generate viva questions from PDF content
        
        Args:
            pdf_content: Extracted text from PDF
            num_questions: Number of questions to generate (default 20)
        
        Returns:
            List of question dictionaries
        """
        try:
            prompt = self._create_generation_prompt(pdf_content, num_questions)
            response = self.llm.invoke(prompt)
            raw_output = response.strip() if isinstance(response, str) else response.content.strip()
            
            return self._parse_generated_questions(raw_output)
            
        except Exception as e:
            logger.error(f"Error generating questions from PDF: {e}")
            return []
    
    def _create_generation_prompt(self, pdf_content: str, num_questions: int) -> str:
        """Create the prompt for question generation"""
        questions_per_level = num_questions // 4
        
        return f"""
You are an expert examiner. Based on the following content:

--- CONTENT START ---
{pdf_content}
--- CONTENT END ---

Generate {num_questions} viva questions along with their answers across different difficulty levels from 1-20:
- {questions_per_level} questions at difficulty level 1-5 (Basic)
- {questions_per_level} questions at difficulty level 6-10 (Intermediate) 
- {questions_per_level} questions at difficulty level 11-15 (Advanced)
- {questions_per_level} questions at difficulty level 16-20 (Expert)

Format exactly like this:

Basic (1-5):
Q1: [Difficulty: 3] ...
A1: ...
Q2: [Difficulty: 4] ...
A2: ...

Intermediate (6-10):
Q6: [Difficulty: 7] ...
A6: ...
Q7: [Difficulty: 8] ...
A7: ...

Advanced (11-15):
Q11: [Difficulty: 13] ...
A11: ...
Q12: [Difficulty: 14] ...
A12: ...

Expert (16-20):
Q16: [Difficulty: 18] ...
A16: ...
Q17: [Difficulty: 19] ...
A17: ...

Make sure each question is:
1. Clear and specific
2. Appropriate for the difficulty level
3. Directly related to the content
4. Has a comprehensive answer
"""
    
    def _parse_generated_questions(self, raw_output: str) -> List[Dict]:
        """Parse the generated questions from LLM output"""
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
        
        return self._process_question_sections(sections)
    
    def _process_question_sections(self, sections: Dict[str, List[str]]) -> List[Dict]:
        """Process question sections into structured format"""
        qa_dict = {}
        all_qas = []
        difficulty_mapping = {"Basic": (1, 5), "Intermediate": (6, 10), "Advanced": (11, 15), "Expert": (16, 20)}
        
        for level, lines in sections.items():
            level_qas = []
            for i in range(0, len(lines), 2):
                try:
                    if i + 1 < len(lines):
                        q_line = lines[i]
                        a_line = lines[i + 1]
                        
                        # Extract difficulty from question if specified
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
                    logger.warning(f"Error processing question pair: {e}")
                    continue
            
            qa_dict[level] = level_qas
        
        return all_qas

class QuestionParser:
    """Handles parsing and validation of questions"""
    
    @staticmethod
    def validate_question_format(question_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate question format and return validation results
        
        Args:
            question_data: Question dictionary to validate
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        required_fields = ['question', 'answer', 'level', 'difficulty']
        for field in required_fields:
            if field not in question_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate question content
        if 'question' in question_data:
            question = question_data['question']
            if not question or len(question.strip()) < 10:
                errors.append("Question is too short or empty")
            if len(question) > 1000:
                errors.append("Question is too long")
        
        # Validate answer content
        if 'answer' in question_data:
            answer = question_data['answer']
            if not answer or len(answer.strip()) < 5:
                errors.append("Answer is too short or empty")
            if len(answer) > 2000:
                errors.append("Answer is too long")
        
        # Validate difficulty
        if 'difficulty' in question_data:
            difficulty = question_data['difficulty']
            if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 20:
                errors.append("Difficulty must be an integer between 1 and 20")
        
        # Validate level
        if 'level' in question_data:
            level = question_data['level']
            valid_levels = ['Basic', 'Intermediate', 'Advanced', 'Expert']
            if level not in valid_levels:
                errors.append(f"Level must be one of: {', '.join(valid_levels)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def clean_question_text(text: str) -> str:
        """Clean and normalize question text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove any markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Ensure proper sentence ending
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    @staticmethod
    def extract_keywords(question: str, answer: str) -> List[str]:
        """Extract keywords from question and answer for better categorization"""
        # Simple keyword extraction - can be enhanced with NLP libraries
        text = f"{question} {answer}".lower()
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        keywords = [word for word in words if word not in stop_words]
        
        # Return unique keywords, limited to 10
        return list(set(keywords))[:10]

class QuestionManager:
    """Main class for managing questions throughout the application"""
    
    def __init__(self, llm: OpenAI):
        self.generator = QuestionGenerator(llm)
        self.parser = QuestionParser()
    
    def generate_and_validate_questions(self, pdf_content: str, num_questions: int = 20) -> Tuple[List[Dict], List[str]]:
        """
        Generate questions and validate them
        
        Returns:
            Tuple of (valid_questions, validation_errors)
        """
        questions = self.generator.generate_questions_from_pdf(pdf_content, num_questions)
        
        valid_questions = []
        validation_errors = []
        
        for i, question in enumerate(questions):
            is_valid, errors = self.parser.validate_question_format(question)
            
            if is_valid:
                # Clean the question text
                question['question'] = self.parser.clean_question_text(question['question'])
                question['answer'] = self.parser.clean_question_text(question['answer'])
                
                # Add keywords
                question['keywords'] = self.parser.extract_keywords(question['question'], question['answer'])
                
                valid_questions.append(question)
            else:
                validation_errors.append(f"Question {i+1}: {'; '.join(errors)}")
        
        return valid_questions, validation_errors
    
    def get_questions_by_difficulty(self, questions: List[Dict], difficulty_range: Tuple[int, int]) -> List[Dict]:
        """Get questions within a specific difficulty range"""
        min_diff, max_diff = difficulty_range
        return [q for q in questions if min_diff <= q.get('difficulty', 0) <= max_diff]
    
    def get_questions_by_level(self, questions: List[Dict], level: str) -> List[Dict]:
        """Get questions by difficulty level"""
        return [q for q in questions if q.get('level') == level]
    
    def get_unanswered_questions(self, questions: List[Dict]) -> List[Dict]:
        """Get questions that haven't been answered yet"""
        return [q for q in questions if q.get('score') is None]
    
    def get_answered_questions(self, questions: List[Dict]) -> List[Dict]:
        """Get questions that have been answered"""
        return [q for q in questions if q.get('score') is not None]
    
    def find_question_by_difficulty(self, questions: List[Dict], target_difficulty: int, exclude_indices: List[int] = None) -> Optional[int]:
        """
        Find a question index closest to target difficulty
        
        Args:
            questions: List of questions
            target_difficulty: Target difficulty level
            exclude_indices: Indices to exclude from search
        
        Returns:
            Index of best matching question or None
        """
        if exclude_indices is None:
            exclude_indices = []
        
        # First try exact match
        for i, q in enumerate(questions):
            if i not in exclude_indices and q.get('difficulty') == target_difficulty:
                return i
        
        # If no exact match, find closest difficulty
        best_match = None
        best_diff = float('inf')
        
        for i, q in enumerate(questions):
            if i not in exclude_indices:
                qa_difficulty = q.get('difficulty', 10)
                diff = abs(qa_difficulty - target_difficulty)
                if diff < best_diff:
                    best_diff = diff
                    best_match = i
        
        return best_match
    
    def calculate_question_statistics(self, questions: List[Dict]) -> Dict:
        """Calculate statistics for a set of questions"""
        if not questions:
            return {
                'total': 0,
                'answered': 0,
                'unanswered': 0,
                'average_score': 0,
                'difficulty_distribution': {},
                'level_distribution': {}
            }
        
        answered_questions = self.get_answered_questions(questions)
        unanswered_questions = self.get_unanswered_questions(questions)
        
        # Calculate average score
        total_score = sum(q.get('score', 0) for q in answered_questions)
        average_score = total_score / len(answered_questions) if answered_questions else 0
        
        # Difficulty distribution
        difficulty_dist = {}
        for q in questions:
            diff = q.get('difficulty', 10)
            difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
        
        # Level distribution
        level_dist = {}
        for q in questions:
            level = q.get('level', 'Unknown')
            level_dist[level] = level_dist.get(level, 0) + 1
        
        return {
            'total': len(questions),
            'answered': len(answered_questions),
            'unanswered': len(unanswered_questions),
            'average_score': average_score,
            'difficulty_distribution': difficulty_dist,
            'level_distribution': level_dist
        }
    
    def export_questions_to_text(self, questions: List[Dict], user_info: Dict) -> str:
        """Export questions to formatted text"""
        import io
        
        output = io.StringIO()
        output.write(f"Name: {user_info.get('name', 'N/A')}\n")
        output.write(f"Subject: {user_info.get('subject', 'N/A')}\n")
        output.write(f"Book Title: {user_info.get('book_title', 'N/A')}\n\n")
        output.write("Generated Viva Questions and Answers\n")
        output.write("=" * 50 + "\n\n")
        
        for i, q in enumerate(questions, 1):
            output.write(f"[{i}] Level: {q.get('level', 'Unknown')} | Difficulty: {q.get('difficulty', 'N/A')}\n")
            output.write(f"Q: {q.get('question', 'N/A')}\n")
            output.write(f"A: {q.get('answer', 'N/A')}\n")
            if q.get('user_answer'):
                output.write(f"User Answer: {q.get('user_answer')}\n")
            if q.get('score') is not None:
                output.write(f"Score: {q.get('score')}/10\n")
            output.write("-" * 50 + "\n")
        
        return output.getvalue()
