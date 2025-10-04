# -*- coding: utf-8 -*-
"""
Adaptive Learning Module for EchoLearn
Handles intelligent difficulty adjustment based on student performance
"""

import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AdaptiveState:
    """Represents the current state of adaptive learning"""
    current_difficulty: int = 10
    consecutive_wrong_same_level: int = 0
    last_answer_correct: Optional[bool] = None
    difficulty_path: List[Dict] = None
    performance_history: List[Dict] = None
    
    def __post_init__(self):
        if self.difficulty_path is None:
            self.difficulty_path = []
        if self.performance_history is None:
            self.performance_history = []

class AdaptiveLearningEngine:
    """Implements adaptive learning algorithm based on performance"""
    
    def __init__(self):
        self.state = AdaptiveState()
        self.difficulty_bounds = (1, 20)  # Min and max difficulty levels
        self.correct_threshold = 6  # Score >= 6 considered correct
    
    def update_state(self, score: int, question_index: int, question_difficulty: int) -> Dict:
        """
        Update adaptive learning state based on student performance
        
        Args:
            score: Student's score (0-10)
            question_index: Index of the current question
            question_difficulty: Difficulty level of the current question
        
        Returns:
            Dict with updated state and recommendations
        """
        is_correct = score >= self.correct_threshold
        self.state.last_answer_correct = is_correct
        
        # Record performance
        performance_record = {
            'question_index': question_index,
            'score': score,
            'difficulty': question_difficulty,
            'correct': is_correct,
            'timestamp': self._get_timestamp()
        }
        
        self.state.performance_history.append(performance_record)
        self.state.difficulty_path.append(performance_record)
        
        # Update adaptive logic
        if is_correct:
            self._handle_correct_answer()
        else:
            self._handle_incorrect_answer()
        
        return self._get_recommendations()
    
    def _handle_correct_answer(self) -> None:
        """Handle logic when student answers correctly"""
        self.state.consecutive_wrong_same_level = 0
        
        # Move to random question from higher difficulty
        higher_difficulties = [d for d in range(self.state.current_difficulty + 1, self.difficulty_bounds[1] + 1)]
        if higher_difficulties:
            self.state.current_difficulty = random.choice(higher_difficulties)
            logger.info(f"Correct answer: Increased difficulty to {self.state.current_difficulty}")
    
    def _handle_incorrect_answer(self) -> None:
        """Handle logic when student answers incorrectly"""
        self.state.consecutive_wrong_same_level += 1
        
        if self.state.consecutive_wrong_same_level >= 2:
            # Two consecutive wrong answers at same level -> drop down difficulty
            if self.state.current_difficulty > self.difficulty_bounds[0]:
                self.state.current_difficulty = max(self.difficulty_bounds[0], self.state.current_difficulty - 2)
                logger.info(f"Two consecutive wrong: Decreased difficulty to {self.state.current_difficulty}")
            self.state.consecutive_wrong_same_level = 0
        else:
            logger.info(f"Wrong answer: Staying at difficulty {self.state.current_difficulty}")
    
    def _get_recommendations(self) -> Dict:
        """Get recommendations based on current state"""
        return {
            'target_difficulty': self.state.current_difficulty,
            'consecutive_wrong': self.state.consecutive_wrong_same_level,
            'last_correct': self.state.last_answer_correct,
            'ready_for_higher_difficulty': self._is_ready_for_higher_difficulty(),
            'needs_reinforcement': self._needs_reinforcement(),
            'learning_trend': self._analyze_learning_trend()
        }
    
    def _is_ready_for_higher_difficulty(self) -> bool:
        """Check if student is ready for higher difficulty"""
        if len(self.state.performance_history) < 3:
            return False
        
        recent_scores = [p['score'] for p in self.state.performance_history[-3:]]
        return all(score >= 8 for score in recent_scores)
    
    def _needs_reinforcement(self) -> bool:
        """Check if student needs reinforcement at current level"""
        if len(self.state.performance_history) < 3:
            return False
        
        recent_scores = [p['score'] for p in self.state.performance_history[-3:]]
        return all(score < 6 for score in recent_scores)
    
    def _analyze_learning_trend(self) -> str:
        """Analyze learning trend over recent performance"""
        if len(self.state.performance_history) < 5:
            return "insufficient_data"
        
        recent_scores = [p['score'] for p in self.state.performance_history[-5:]]
        
        # Calculate trend
        if len(recent_scores) >= 3:
            first_half = sum(recent_scores[:len(recent_scores)//2]) / (len(recent_scores)//2)
            second_half = sum(recent_scores[len(recent_scores)//2:]) / (len(recent_scores) - len(recent_scores)//2)
            
            if second_half > first_half + 1:
                return "improving"
            elif second_half < first_half - 1:
                return "declining"
            else:
                return "stable"
        
        return "stable"
    
    def find_next_question(self, questions: List[Dict], used_indices: List[int]) -> Optional[int]:
        """
        Find the next question based on adaptive learning algorithm
        
        Args:
            questions: List of available questions
            used_indices: Indices of already used questions
        
        Returns:
            Index of recommended next question or None
        """
        target_difficulty = self.state.current_difficulty
        
        # First try exact match
        for i, q in enumerate(questions):
            if (i not in used_indices and 
                q.get('difficulty', self._get_difficulty_from_level(q.get('level', 'Basic'))) == target_difficulty):
                return i
        
        # If no exact match, find closest difficulty
        best_match = None
        best_diff = float('inf')
        
        for i, q in enumerate(questions):
            if i not in used_indices:
                qa_difficulty = q.get('difficulty', self._get_difficulty_from_level(q.get('level', 'Basic')))
                diff = abs(qa_difficulty - target_difficulty)
                if diff < best_diff:
                    best_diff = diff
                    best_match = i
        
        return best_match
    
    def _get_difficulty_from_level(self, level: str) -> int:
        """Convert text levels to numeric difficulty for compatibility"""
        mapping = {
            'Basic': 3, 'Easy': 3,
            'Intermediate': 8, 'Moderate': 8, 
            'Advanced': 13, 'Difficult': 13,
            'Expert': 18
        }
        return mapping.get(level, 10)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        import time
        return time.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_learning_analytics(self) -> Dict:
        """Get comprehensive learning analytics"""
        if not self.state.performance_history:
            return {
                'total_questions': 0,
                'accuracy_rate': 0,
                'average_score': 0,
                'difficulty_progression': [],
                'learning_trend': 'no_data',
                'recommendations': []
            }
        
        total_questions = len(self.state.performance_history)
        correct_answers = sum(1 for p in self.state.performance_history if p['correct'])
        accuracy_rate = (correct_answers / total_questions) * 100
        average_score = sum(p['score'] for p in self.state.performance_history) / total_questions
        
        difficulty_progression = [p['difficulty'] for p in self.state.performance_history]
        learning_trend = self._analyze_learning_trend()
        
        recommendations = self._generate_recommendations()
        
        return {
            'total_questions': total_questions,
            'accuracy_rate': accuracy_rate,
            'average_score': average_score,
            'difficulty_progression': difficulty_progression,
            'learning_trend': learning_trend,
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate personalized learning recommendations"""
        recommendations = []
        
        analytics = self.get_learning_analytics()
        
        if analytics['accuracy_rate'] >= 80:
            recommendations.append("Excellent performance! You're ready for more challenging questions.")
        elif analytics['accuracy_rate'] >= 60:
            recommendations.append("Good progress! Focus on strengthening areas where you scored lower.")
        else:
            recommendations.append("Consider reviewing fundamental concepts before moving to advanced topics.")
        
        if analytics['learning_trend'] == 'improving':
            recommendations.append("Great job! Your performance is improving consistently.")
        elif analytics['learning_trend'] == 'declining':
            recommendations.append("Your recent performance suggests you might benefit from reviewing previous topics.")
        
        if self.state.consecutive_wrong_same_level >= 2:
            recommendations.append("Don't worry about recent difficulties. The system will adjust to help you succeed.")
        
        return recommendations
    
    def reset_state(self) -> None:
        """Reset adaptive learning state"""
        self.state = AdaptiveState()
        logger.info("Adaptive learning state reset")
    
    def export_learning_data(self) -> Dict:
        """Export learning data for analysis"""
        return {
            'state': {
                'current_difficulty': self.state.current_difficulty,
                'consecutive_wrong_same_level': self.state.consecutive_wrong_same_level,
                'last_answer_correct': self.state.last_answer_correct
            },
            'performance_history': self.state.performance_history,
            'difficulty_path': self.state.difficulty_path,
            'analytics': self.get_learning_analytics()
        }

class AdaptiveLearningVisualizer:
    """Handles visualization of adaptive learning progress"""
    
    @staticmethod
    def create_progress_chart(performance_history: List[Dict]) -> Dict:
        """Create data for progress visualization"""
        if not performance_history:
            return {'questions': [], 'scores': [], 'difficulties': []}
        
        questions = list(range(1, len(performance_history) + 1))
        scores = [p['score'] for p in performance_history]
        difficulties = [p['difficulty'] for p in performance_history]
        
        return {
            'questions': questions,
            'scores': scores,
            'difficulties': difficulties
        }
    
    @staticmethod
    def create_difficulty_distribution(performance_history: List[Dict]) -> Dict:
        """Create difficulty distribution data"""
        if not performance_history:
            return {}
        
        distribution = {}
        for p in performance_history:
            diff = p['difficulty']
            if diff not in distribution:
                distribution[diff] = {'total': 0, 'correct': 0, 'scores': []}
            
            distribution[diff]['total'] += 1
            if p['correct']:
                distribution[diff]['correct'] += 1
            distribution[diff]['scores'].append(p['score'])
        
        # Calculate averages
        for diff in distribution:
            scores = distribution[diff]['scores']
            distribution[diff]['average_score'] = sum(scores) / len(scores)
            distribution[diff]['accuracy'] = (distribution[diff]['correct'] / distribution[diff]['total']) * 100
        
        return distribution
    
    @staticmethod
    def create_learning_trajectory(performance_history: List[Dict]) -> Dict:
        """Create learning trajectory analysis"""
        if len(performance_history) < 3:
            return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0}
        
        # Simple linear regression to find trend
        x_values = list(range(len(performance_history)))
        y_values = [p['score'] for p in performance_history]
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend
        if slope > 0.1:
            trend = 'improving'
        elif slope < -0.1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'slope': slope,
            'r_squared': r_squared,
            'intercept': intercept
        }
