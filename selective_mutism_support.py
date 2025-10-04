# -*- coding: utf-8 -*-
"""
Selective Mutism Support Module for EchoLearn
Handles specialized support for students with selective mutism
"""

import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SelectiveMutismState:
    """Represents the current state of selective mutism support"""
    confidence_level: int = 1  # Scale 1-5
    success_streak: int = 0
    progress_milestones: List[Dict] = None
    communication_methods_used: List[str] = None
    comfort_level_with_speech: float = 0.3  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.progress_milestones is None:
            self.progress_milestones = []
        if self.communication_methods_used is None:
            self.communication_methods_used = []

class SelectiveMutismSupport:
    """Main class for selective mutism support functionality"""
    
    def __init__(self):
        self.state = SelectiveMutismState()
        self.encouraging_messages = self._initialize_encouraging_messages()
        self.confidence_thresholds = {
            1: 3,  # Need 3 successes to reach level 2
            2: 5,  # Need 5 successes to reach level 3
            3: 7,  # Need 7 successes to reach level 4
            4: 10  # Need 10 successes to reach level 5
        }
    
    def _initialize_encouraging_messages(self) -> Dict[int, List[str]]:
        """Initialize encouraging messages for different score ranges"""
        return {
            10: [
                "🌟 Outstanding work! You're showing incredible understanding!",
                "🏆 Perfect answer! Your hard work is really paying off!",
                "✨ Excellent! You should be very proud of yourself!",
                "🎉 Amazing! You're doing fantastically well!"
            ],
            9: [
                "⭐ Fantastic job! You're doing wonderfully!",
                "🎉 Great answer! You're building so much confidence!",
                "💪 Impressive! Keep up this excellent work!",
                "🌈 Wonderful! You're making great progress!"
            ],
            8: [
                "😊 Very good! You're making excellent progress!",
                "👏 Well done! Your understanding is growing stronger!",
                "🌈 Great work! You should feel proud!",
                "💚 Excellent effort! You're doing great!"
            ],
            7: [
                "👍 Good job! You're on the right track!",
                "🎯 Nice work! You're showing real progress!",
                "💚 Well done! Keep going!",
                "☀️ Great effort! You're learning well!"
            ],
            6: [
                "🤝 Good effort! You're learning and growing!",
                "📚 You're doing well! Keep practicing!",
                "☀️ Nice try! You're moving forward!",
                "💪 Keep it up! You're making progress!"
            ],
            5: [
                "💛 You're trying hard, and that's what matters!",
                "🌱 You're growing! Keep up the good work!",
                "🤗 Great effort! You're on your way!",
                "🌟 Every attempt makes you stronger!"
            ],
            4: [
                "🌟 You participated, and that takes courage!",
                "💖 Thank you for trying! That's a big step!",
                "🌸 You did it! Be proud of yourself!",
                "💪 You're being so brave! Keep going!"
            ]
        }
    
    def update_confidence_level(self, success: bool, communication_method: str = "unknown") -> Dict:
        """
        Update confidence level based on success/failure
        
        Args:
            success: Whether the answer was successful (score >= 6)
            communication_method: Method used for communication
        
        Returns:
            Dict with updated state and encouragement
        """
        # Track communication method
        if communication_method not in self.state.communication_methods_used:
            self.state.communication_methods_used.append(communication_method)
        
        if success:
            self.state.success_streak += 1
            
            # Check if ready for confidence level increase
            current_threshold = self.confidence_thresholds.get(self.state.confidence_level, float('inf'))
            
            if self.state.success_streak >= current_threshold and self.state.confidence_level < 5:
                old_level = self.state.confidence_level
                self.state.confidence_level += 1
                
                # Record milestone
                milestone = {
                    'type': 'confidence_increase',
                    'level': self.state.confidence_level,
                    'timestamp': time.time(),
                    'success_streak': self.state.success_streak,
                    'communication_method': communication_method
                }
                self.state.progress_milestones.append(milestone)
                
                return {
                    'confidence_increased': True,
                    'old_level': old_level,
                    'new_level': self.state.confidence_level,
                    'milestone': milestone,
                    'encouragement': self._get_confidence_level_up_message()
                }
            else:
                return {
                    'confidence_increased': False,
                    'encouragement': self._get_success_message()
                }
        else:
            self.state.success_streak = 0
            
            # Slightly decrease confidence but never below 1
            if self.state.confidence_level > 1:
                self.state.confidence_level = max(1, self.state.confidence_level - 0.5)
            
            return {
                'confidence_increased': False,
                'encouragement': self._get_encouragement_message()
            }
    
    def _get_confidence_level_up_message(self) -> str:
        """Get message for confidence level increase"""
        level_messages = {
            2: "🎉 Congratulations! You've reached confidence level 2! You're building real strength!",
            3: "🌟 Amazing! Confidence level 3! You're becoming so much more comfortable!",
            4: "🏆 Incredible! Confidence level 4! You're showing tremendous courage!",
            5: "🎊 Outstanding! Maximum confidence level! You've come so far!"
        }
        return level_messages.get(self.state.confidence_level, "Great job on your progress!")
    
    def _get_success_message(self) -> str:
        """Get general success message"""
        success_messages = [
            "💪 You're doing great! Keep up the excellent work!",
            "🌟 Wonderful! You're building so much confidence!",
            "🎉 Great job! Every answer makes you stronger!",
            "✨ You're making fantastic progress!"
        ]
        return random.choice(success_messages)
    
    def _get_encouragement_message(self) -> str:
        """Get encouragement message for when things don't go perfectly"""
        encouragement_messages = [
            "💖 Don't worry! Every attempt is valuable and you're learning!",
            "🌱 You're still growing! This is all part of the learning process!",
            "🤗 You're being so brave! That's what matters most!",
            "💪 Keep going! You're doing wonderfully just by participating!"
        ]
        return random.choice(encouragement_messages)
    
    def get_encouraging_message(self, score: int) -> str:
        """Get encouraging message based on score"""
        messages = self.encouraging_messages.get(score, self.encouraging_messages[4])
        return random.choice(messages)
    
    def generate_multiple_choice_options(self, correct_answer: str, question: str, llm) -> Tuple[List[str], int]:
        """
        Generate plausible multiple choice options for selective mutism mode
        
        Args:
            correct_answer: The correct answer
            question: The question text
            llm: Language model for generating options
        
        Returns:
            Tuple of (options_list, correct_index)
        """
        prompt = f"""
Create 3 plausible but incorrect answer choices for this question along with the correct answer.
Make the wrong answers believable but clearly different from the correct answer.
Focus on creating options that help build confidence through participation.

Question: {question}
Correct Answer: {correct_answer}

Provide exactly 4 options in this format:
A) [option 1]
B) [option 2] 
C) [option 3]
D) [option 4]

Make sure one of these options matches the correct answer exactly.
Make the wrong options reasonable but distinguishable from the correct answer.
"""
        try:
            result = llm.invoke(prompt)
            response = result.strip() if isinstance(result, str) else result.content.strip()
            
            # Parse the response to extract options
            options = []
            correct_index = 0
            
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('A)') or line.startswith('B)') or line.startswith('C)') or line.startswith('D)')):
                    option_text = line[3:].strip()  # Remove "A) " prefix
                    options.append(option_text)
                    
                    # Check if this option matches the correct answer
                    if (correct_answer.lower().strip() in option_text.lower() or 
                        option_text.lower().strip() in correct_answer.lower()):
                        correct_index = len(options) - 1
            
            if len(options) == 4:
                return options, correct_index
            else:
                # Fallback: create simple options
                return [correct_answer, "Not applicable", "Insufficient information", "Cannot be determined"], 0
                
        except Exception as e:
            logger.error(f"Error generating multiple choice options: {e}")
            # Fallback options
            return [correct_answer, "Not applicable", "Insufficient information", "Cannot be determined"], 0
    
    def get_comfort_level_recommendations(self) -> List[str]:
        """Get recommendations based on current comfort level"""
        recommendations = []
        
        if self.state.confidence_level >= 4:
            recommendations.extend([
                "🌟 You're doing amazingly well! Consider trying longer speaking sessions.",
                "🎉 Your confidence is high! You might enjoy leading discussions.",
                "💪 You're ready for more challenging communication tasks!"
            ])
        elif self.state.confidence_level >= 3:
            recommendations.extend([
                "😊 Great progress! Try speaking a bit more each time.",
                "🎯 You're building strong confidence! Keep practicing!",
                "💚 You're ready to try slightly longer responses."
            ])
        elif self.state.confidence_level >= 2:
            recommendations.extend([
                "🌱 You're making good progress! Every small step counts.",
                "🤗 Try to speak a little more each time you practice.",
                "💪 You're building confidence! Keep going!"
            ])
        else:
            recommendations.extend([
                "💖 You're being so brave! Every attempt is wonderful.",
                "🌟 Start with whatever feels comfortable - even one word is great!",
                "🤗 Take your time and go at your own pace."
            ])
        
        return recommendations
    
    def get_progress_summary(self) -> Dict:
        """Get comprehensive progress summary"""
        return {
            'confidence_level': self.state.confidence_level,
            'success_streak': self.state.success_streak,
            'total_milestones': len(self.state.progress_milestones),
            'communication_methods_tried': len(self.state.communication_methods_used),
            'comfort_level': self.state.comfort_level_with_speech,
            'recent_progress': self._analyze_recent_progress(),
            'recommendations': self.get_comfort_level_recommendations()
        }
    
    def _analyze_recent_progress(self) -> str:
        """Analyze recent progress patterns"""
        if len(self.state.progress_milestones) < 2:
            return "Just getting started - every step is progress!"
        
        recent_milestones = self.state.progress_milestones[-3:]
        confidence_increases = [m for m in recent_milestones if m['type'] == 'confidence_increase']
        
        if len(confidence_increases) >= 2:
            return "Excellent progress! You're gaining confidence rapidly!"
        elif len(confidence_increases) == 1:
            return "Good progress! You're building confidence steadily!"
        else:
            return "Steady progress! Keep participating and you'll see growth!"
    
    def create_celebration_message(self, score: int, communication_method: str) -> str:
        """Create celebration message for successful participation"""
        base_message = self.get_encouraging_message(score)
        
        method_celebrations = {
            'speech': "🎙️ You spoke up and that's incredible! Your voice matters!",
            'text': "✍️ You expressed yourself beautifully in writing!",
            'multiple_choice': "🎯 Great job participating! Every choice you make builds confidence!"
        }
        
        method_message = method_celebrations.get(communication_method, "You participated and that's wonderful!")
        
        return f"{base_message} {method_message}"
    
    def get_session_encouragement(self) -> str:
        """Get encouragement message for the start of a session"""
        encouragement_messages = {
            1: "🌱 Welcome! You're taking a wonderful first step. Remember, every attempt is valuable!",
            2: "😊 Great to see you again! You're building confidence with each session!",
            3: "🌟 You're doing so well! Your courage is inspiring!",
            4: "🎉 Amazing progress! You're becoming so much more comfortable!",
            5: "🏆 Outstanding! You've come so far! You're an inspiration!"
        }
        
        return encouragement_messages.get(self.state.confidence_level, "You're doing great! Keep going!")
    
    def reset_state(self) -> None:
        """Reset selective mutism state"""
        self.state = SelectiveMutismState()
        logger.info("Selective mutism state reset")
    
    def export_progress_data(self) -> Dict:
        """Export progress data for analysis"""
        return {
            'current_state': {
                'confidence_level': self.state.confidence_level,
                'success_streak': self.state.success_streak,
                'comfort_level': self.state.comfort_level_with_speech
            },
            'progress_milestones': self.state.progress_milestones,
            'communication_methods_used': self.state.communication_methods_used,
            'summary': self.get_progress_summary()
        }

class SelectiveMutismUI:
    """UI components specifically for selective mutism support"""
    
    @staticmethod
    def display_confidence_level_indicator(confidence_level: int) -> None:
        """Display confidence level indicator"""
        stars = "⭐" * confidence_level
        empty_stars = "☆" * (5 - confidence_level)
        
        st.markdown(f"**Confidence Level:** {stars}{empty_stars} ({confidence_level}/5)")
    
    @staticmethod
    def display_success_streak(success_streak: int) -> None:
        """Display success streak"""
        if success_streak > 0:
            streak_emoji = "🔥" * min(success_streak, 5)
            st.markdown(f"**Success Streak:** {streak_emoji} {success_streak}")
        else:
            st.markdown("**Success Streak:** 🌱 Ready to start!")
    
    @staticmethod
    def display_progress_milestones(milestones: List[Dict]) -> None:
        """Display progress milestones"""
        if not milestones:
            st.info("🌱 Your journey is just beginning! Every step counts!")
            return
        
        st.subheader("🎯 Your Confidence Journey")
        
        for i, milestone in enumerate(milestones, 1):
            if milestone['type'] == 'confidence_increase':
                stars = "⭐" * milestone['level']
                st.write(f"**Step {i}:** Reached confidence level {stars} ({milestone['level']}/5)")
    
    @staticmethod
    def display_communication_methods_summary(methods_used: List[str]) -> None:
        """Display summary of communication methods used"""
        if not methods_used:
            return
        
        method_counts = {}
        for method in methods_used:
            method_counts[method] = method_counts.get(method, 0) + 1
        
        st.subheader("💬 Communication Methods Used")
        
        for method, count in method_counts.items():
            method_names = {
                'speech': '🎙️ Speaking',
                'text': '✍️ Writing',
                'multiple_choice': '🎯 Multiple Choice'
            }
            display_name = method_names.get(method, method)
            st.write(f"**{display_name}:** {count} times")
    
    @staticmethod
    def display_comfort_level_slider() -> float:
        """Display comfort level slider for self-assessment"""
        st.subheader("😊 How are you feeling today?")
        
        comfort_level = st.slider(
            "Rate your comfort level with speaking today:",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="This helps us adjust the session to your comfort level"
        )
        
        comfort_labels = {
            0.0: "Very nervous",
            0.2: "A bit nervous", 
            0.4: "Somewhat comfortable",
            0.6: "Pretty comfortable",
            0.8: "Very comfortable",
            1.0: "Completely comfortable"
        }
        
        # Find closest label
        closest_level = min(comfort_labels.keys(), key=lambda x: abs(x - comfort_level))
        st.info(f"💭 You're feeling: **{comfort_labels[closest_level]}**")
        
        return comfort_level
