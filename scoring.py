# -*- coding: utf-8 -*-
"""
Scoring Module for EchoLearn
Handles answer evaluation with improved consistency and reliability
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from langchain.llms import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScoringRubric:
    """Defines scoring criteria and rubrics for different evaluation modes"""
    
    STANDARD_RUBRIC = {
        10: "Perfect answer - completely correct, comprehensive, and well-explained",
        9: "Excellent answer - mostly correct with minor gaps or slight imprecision",
        8: "Very good answer - correct main points with some missing details",
        7: "Good answer - correct core concepts but missing important details",
        6: "Satisfactory answer - partially correct with some understanding shown",
        5: "Fair answer - shows some knowledge but significant gaps",
        4: "Poor answer - minimal understanding or mostly incorrect",
        3: "Very poor answer - little to no correct information",
        2: "Incorrect answer - shows misunderstanding of concepts",
        1: "Completely wrong answer - no relevant information",
        0: "No answer or completely irrelevant response"
    }
    
    SELECTIVE_MUTISM_RUBRIC = {
        10: "Outstanding! Perfect understanding and excellent communication",
        9: "Fantastic! Very strong understanding with minor gaps",
        8: "Great job! Good understanding of main concepts",
        7: "Well done! Shows solid understanding of key points",
        6: "Good effort! Demonstrates understanding of basic concepts",
        5: "Nice try! Shows some understanding and effort",
        4: "Thank you for participating! Every attempt builds confidence"
    }

class AnswerEvaluator:
    """Handles answer evaluation with improved consistency and reliability"""
    
    def __init__(self, llm: OpenAI):
        self.llm = llm
        self.rubric = ScoringRubric()
    
    def extract_score_from_response(self, response: str) -> int:
        """Extract numeric score from LLM response with robust parsing"""
        try:
            # Clean the response
            response = str(response).strip()
            
            # Try to find score patterns
            patterns = [
                r'(\d+)/10',  # "8/10"
                r'score[:\s]*(\d+)',  # "score: 8" or "score 8"
                r'(\d+)\s*out\s*of\s*10',  # "8 out of 10"
                r'rating[:\s]*(\d+)',  # "rating: 8"
                r'(\d+)',  # Just a number
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    return max(0, min(10, score))  # Clamp between 0-10
            
            # If no pattern matches, try to extract any number
            numbers = re.findall(r'\d+', response)
            if numbers:
                score = int(numbers[0])
                return max(0, min(10, score))
            
            logger.warning(f"Could not extract score from response: {response}")
            return 5  # Default middle score instead of 0
            
        except Exception as e:
            logger.error(f"Error extracting score from response '{response}': {e}")
            return 5  # Default middle score
    
    def evaluate_answer_standard(self, question: str, correct_answer: str, user_answer: str) -> Dict:
        """
        Evaluate answer using standard academic criteria
        
        Returns:
            Dict with 'score', 'reasoning', 'feedback', and 'suggestions'
        """
        if not user_answer or not user_answer.strip():
            return {
                'score': 0,
                'reasoning': 'No answer provided',
                'feedback': 'Please provide an answer to receive a score.',
                'suggestions': 'Try to answer based on your understanding of the topic.'
            }
        
        eval_prompt = f"""
You are an expert educator evaluating a student's answer. Use the following rubric:

10: Perfect answer - completely correct, comprehensive, and well-explained
9: Excellent answer - mostly correct with minor gaps or slight imprecision  
8: Very good answer - correct main points with some missing details
7: Good answer - correct core concepts but missing important details
6: Satisfactory answer - partially correct with some understanding shown
5: Fair answer - shows some knowledge but significant gaps
4: Poor answer - minimal understanding or mostly incorrect
3: Very poor answer - little to no correct information
2: Incorrect answer - shows misunderstanding of concepts
1: Completely wrong answer - no relevant information
0: No answer or completely irrelevant response

Question: {question}

Correct Answer: {correct_answer}

Student's Answer: {user_answer}

Evaluate the student's answer based on:
1. Accuracy of key concepts
2. Completeness of the response
3. Understanding demonstrated
4. Relevance to the question

Provide your evaluation in this exact format:
SCORE: [number from 0-10]
REASONING: [brief explanation of the score]
FEEDBACK: [constructive feedback for the student]
SUGGESTIONS: [specific suggestions for improvement]
"""
        
        try:
            result = self.llm.invoke(eval_prompt)
            response = result.strip() if isinstance(result, str) else result.content.strip()
            
            # Parse the structured response
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=FEEDBACK:|$)', response, re.IGNORECASE | re.DOTALL)
            feedback_match = re.search(r'FEEDBACK:\s*(.+?)(?=SUGGESTIONS:|$)', response, re.IGNORECASE | re.DOTALL)
            suggestions_match = re.search(r'SUGGESTIONS:\s*(.+?)$', response, re.IGNORECASE | re.DOTALL)
            
            score = int(score_match.group(1)) if score_match else self.extract_score_from_response(response)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "Evaluation completed"
            feedback = feedback_match.group(1).strip() if feedback_match else "Good effort on this question."
            suggestions = suggestions_match.group(1).strip() if suggestions_match else "Keep studying and practicing!"
            
            return {
                'score': max(0, min(10, score)),
                'reasoning': reasoning,
                'feedback': feedback,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error in standard evaluation: {e}")
            return {
                'score': 5,
                'reasoning': 'Evaluation error occurred',
                'feedback': 'There was an issue evaluating your answer. Please try again.',
                'suggestions': 'Make sure your answer is clear and relevant to the question.'
            }
    
    def evaluate_answer_selective_mutism(self, question: str, correct_answer: str, user_answer: str, confidence_level: int = 1) -> Dict:
        """
        Evaluate answer with selective mutism support - more encouraging approach
        
        Returns:
            Dict with 'score', 'reasoning', 'feedback', 'encouragement', and 'confidence_boost'
        """
        if not user_answer or not user_answer.strip():
            return {
                'score': 4,
                'reasoning': 'No answer provided, but participation is valued',
                'feedback': 'Thank you for being here! Every step counts.',
                'encouragement': 'You\'re doing great just by participating!',
                'confidence_boost': 0
            }
        
        eval_prompt = f"""
You are a supportive and encouraging teacher working with a student who has selective mutism. 
Your goal is to build their confidence while still providing meaningful feedback.

Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {user_answer}

Evaluation Guidelines:
- Focus on what the student got right, even partially correct concepts
- Give credit for effort and any relevant information provided
- Be encouraging and supportive in your feedback
- Score range: 4-10 (minimum 4 to maintain confidence, maximum 10 for excellent answers)
- Consider that this student is working hard to overcome communication challenges

Provide your evaluation in this exact format:
SCORE: [number from 4-10]
REASONING: [encouraging explanation of the score]
FEEDBACK: [supportive feedback highlighting positives]
ENCOURAGEMENT: [motivational message]
CONFIDENCE_BOOST: [0 or 1 - whether this should boost confidence]
"""
        
        try:
            result = self.llm.invoke(eval_prompt)
            response = result.strip() if isinstance(result, str) else result.content.strip()
            
            # Parse the structured response
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=FEEDBACK:|$)', response, re.IGNORECASE | re.DOTALL)
            feedback_match = re.search(r'FEEDBACK:\s*(.+?)(?=ENCOURAGEMENT:|$)', response, re.IGNORECASE | re.DOTALL)
            encouragement_match = re.search(r'ENCOURAGEMENT:\s*(.+?)(?=CONFIDENCE_BOOST:|$)', response, re.IGNORECASE | re.DOTALL)
            confidence_boost_match = re.search(r'CONFIDENCE_BOOST:\s*([01])', response, re.IGNORECASE)
            
            score = int(score_match.group(1)) if score_match else 6
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "Great effort!"
            feedback = feedback_match.group(1).strip() if feedback_match else "You're doing wonderfully!"
            encouragement = encouragement_match.group(1).strip() if encouragement_match else "Keep up the great work!"
            confidence_boost = int(confidence_boost_match.group(1)) if confidence_boost_match else 0
            
            # Ensure score is in range 4-10
            score = max(4, min(10, score))
            
            # Bonus points for higher confidence levels
            if confidence_level >= 3:
                score = min(10, score + 1)  # +1 bonus for medium-high confidence
            elif confidence_level >= 5:
                score = min(10, score + 2)  # +2 bonus for highest confidence
            
            return {
                'score': score,
                'reasoning': reasoning,
                'feedback': feedback,
                'encouragement': encouragement,
                'confidence_boost': confidence_boost
            }
            
        except Exception as e:
            logger.error(f"Error in selective mutism evaluation: {e}")
            return {
                'score': 6,
                'reasoning': 'Evaluation completed with encouragement',
                'feedback': 'You\'re doing great! Keep participating!',
                'encouragement': 'Every answer you give makes you stronger!',
                'confidence_boost': 1
            }
    
    def evaluate_answer_adaptive(self, question: str, correct_answer: str, user_answer: str, difficulty_level: int) -> Dict:
        """
        Evaluate answer with adaptive learning considerations
        
        Returns:
            Dict with evaluation results and adaptive learning insights
        """
        # Use standard evaluation as base
        evaluation = self.evaluate_answer_standard(question, correct_answer, user_answer)
        
        # Add adaptive learning insights
        score = evaluation['score']
        
        # Determine if answer was correct for adaptive purposes (score >= 6)
        is_correct = score >= 6
        
        # Calculate difficulty-adjusted performance
        if difficulty_level <= 5:
            difficulty_category = "Basic"
            expected_min_score = 6
        elif difficulty_level <= 10:
            difficulty_category = "Intermediate"
            expected_min_score = 5
        elif difficulty_level <= 15:
            difficulty_category = "Advanced"
            expected_min_score = 4
        else:
            difficulty_category = "Expert"
            expected_min_score = 3
        
        # Performance assessment
        if score >= expected_min_score + 3:
            performance_level = "Excellent"
        elif score >= expected_min_score + 1:
            performance_level = "Good"
        elif score >= expected_min_score:
            performance_level = "Satisfactory"
        else:
            performance_level = "Needs Improvement"
        
        evaluation.update({
            'is_correct': is_correct,
            'difficulty_category': difficulty_category,
            'performance_level': performance_level,
            'adaptive_insights': {
                'ready_for_higher_difficulty': score >= 8,
                'needs_reinforcement': score < 6,
                'suggested_next_difficulty': self._suggest_next_difficulty(difficulty_level, score)
            }
        })
        
        return evaluation
    
    def _suggest_next_difficulty(self, current_difficulty: int, score: int) -> int:
        """Suggest next difficulty level based on current performance"""
        if score >= 8:
            # Excellent performance - increase difficulty
            return min(20, current_difficulty + 2)
        elif score >= 6:
            # Good performance - slight increase
            return min(20, current_difficulty + 1)
        elif score >= 4:
            # Fair performance - maintain difficulty
            return current_difficulty
        else:
            # Poor performance - decrease difficulty
            return max(1, current_difficulty - 1)
    
    def batch_evaluate(self, evaluations: List[Dict]) -> List[Dict]:
        """
        Evaluate multiple answers in batch for efficiency
        
        Args:
            evaluations: List of dicts with 'question', 'correct_answer', 'user_answer', 'mode'
        
        Returns:
            List of evaluation results
        """
        results = []
        
        for eval_data in evaluations:
            mode = eval_data.get('mode', 'standard')
            confidence_level = eval_data.get('confidence_level', 1)
            difficulty_level = eval_data.get('difficulty_level', 10)
            
            if mode == 'selective_mutism':
                result = self.evaluate_answer_selective_mutism(
                    eval_data['question'],
                    eval_data['correct_answer'],
                    eval_data['user_answer'],
                    confidence_level
                )
            elif mode == 'adaptive':
                result = self.evaluate_answer_adaptive(
                    eval_data['question'],
                    eval_data['correct_answer'],
                    eval_data['user_answer'],
                    difficulty_level
                )
            else:
                result = self.evaluate_answer_standard(
                    eval_data['question'],
                    eval_data['correct_answer'],
                    eval_data['user_answer']
                )
            
            results.append(result)
        
        return results

class ScoringAnalytics:
    """Provides analytics and insights on scoring patterns"""
    
    @staticmethod
    def calculate_session_statistics(evaluations: List[Dict]) -> Dict:
        """Calculate comprehensive session statistics"""
        if not evaluations:
            return {
                'total_questions': 0,
                'answered_questions': 0,
                'total_score': 0,
                'max_possible_score': 0,
                'average_score': 0,
                'percentage': 0,
                'grade': 'N/A'
            }
        
        answered_evaluations = [e for e in evaluations if e.get('score') is not None]
        
        total_questions = len(evaluations)
        answered_questions = len(answered_evaluations)
        total_score = sum(e.get('score', 0) for e in answered_evaluations)
        max_possible_score = answered_questions * 10
        
        if answered_questions > 0:
            average_score = total_score / answered_questions
            percentage = (total_score / max_possible_score) * 100
            
            # Grade classification
            if percentage >= 90:
                grade = "A+"
            elif percentage >= 80:
                grade = "A"
            elif percentage >= 70:
                grade = "B"
            elif percentage >= 60:
                grade = "C"
            elif percentage >= 50:
                grade = "D"
            else:
                grade = "F"
        else:
            average_score = 0
            percentage = 0
            grade = "N/A"
        
        return {
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'total_score': total_score,
            'max_possible_score': max_possible_score,
            'average_score': average_score,
            'percentage': percentage,
            'grade': grade
        }
    
    @staticmethod
    def analyze_difficulty_performance(evaluations: List[Dict]) -> Dict:
        """Analyze performance across different difficulty levels"""
        difficulty_stats = {}
        
        for eval_data in evaluations:
            if eval_data.get('score') is not None:
                difficulty = eval_data.get('difficulty_level', 10)
                
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
                    difficulty_stats[diff_range] = {
                        'scores': [],
                        'total': 0,
                        'max': 0,
                        'count': 0
                    }
                
                score = eval_data.get('score', 0)
                difficulty_stats[diff_range]['scores'].append(score)
                difficulty_stats[diff_range]['total'] += score
                difficulty_stats[diff_range]['max'] += 10
                difficulty_stats[diff_range]['count'] += 1
        
        # Calculate averages
        for diff_range, stats in difficulty_stats.items():
            if stats['count'] > 0:
                stats['average'] = stats['total'] / stats['count']
                stats['percentage'] = (stats['total'] / stats['max']) * 100
            else:
                stats['average'] = 0
                stats['percentage'] = 0
        
        return difficulty_stats
