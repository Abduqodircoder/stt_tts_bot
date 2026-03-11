import json
import logging
import re
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class QuizGenerator:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def extract_vocabulary(self, transcript: str) -> list[dict]:
        """Extract important vocabulary from transcript"""
        
        prompt = f"""
You are an English language teacher. Analyze this movie/video transcript and extract 10-15 important vocabulary words that would be useful for English learners.

TRANSCRIPT:
{transcript[:3000]}

For each word, provide:
1. The word or phrase
2. Simple definition in English
3. An example sentence from context (or a new one)
4. Part of speech (noun, verb, adjective, etc.)

Respond ONLY with valid JSON array, no other text:
[
  {{
    "word": "word here",
    "definition": "simple definition",
    "example": "example sentence",
    "pos": "part of speech"
  }}
]
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON if needed
            content = re.sub(r"```json\s*|\s*```", "", content).strip()
            
            vocabulary = json.loads(content)
            logger.info(f"{len(vocabulary)} ta so'z ajratildi")
            return vocabulary
            
        except Exception as e:
            logger.error(f"Vocabulary extraction error: {e}")
            return []
    
    async def generate_quiz(self, transcript: str, vocabulary: list[dict]) -> list[dict]:
        """Generate 10 quiz questions from transcript and vocabulary"""
        
        vocab_text = "\n".join([
            f"- {v['word']}: {v['definition']}" 
            for v in vocabulary[:15]
        ])
        
        prompt = f"""
You are an English language teacher creating a quiz for ESL students learning English through movies.

TRANSCRIPT (from the video):
{transcript[:3000]}

KEY VOCABULARY:
{vocab_text}

Create EXACTLY 10 multiple choice quiz questions based on the transcript and vocabulary.

Mix these question types:
- Vocabulary meaning (What does X mean?)
- Fill in the blank (Complete the sentence)
- Context understanding (Based on the conversation, what...)
- Word usage (Which sentence uses X correctly?)

Rules:
- Each question has EXACTLY 4 options (A, B, C, D)
- Only ONE correct answer per question
- Make wrong answers plausible but clearly incorrect
- Include a brief explanation for the correct answer

Respond ONLY with valid JSON array, no other text:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": 0,
    "explanation": "Brief explanation why this is correct"
  }}
]

Note: correct_answer is the INDEX (0, 1, 2, or 3) of the correct option.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean JSON
            content = re.sub(r"```json\s*|\s*```", "", content).strip()
            
            questions = json.loads(content)
            
            # Validate questions
            valid_questions = []
            for q in questions:
                if (
                    isinstance(q.get("question"), str) and
                    isinstance(q.get("options"), list) and
                    len(q["options"]) == 4 and
                    isinstance(q.get("correct_answer"), int) and
                    0 <= q["correct_answer"] <= 3
                ):
                    valid_questions.append(q)
            
            # Ensure exactly 10 questions
            valid_questions = valid_questions[:10]
            
            logger.info(f"{len(valid_questions)} ta savol tuzildi")
            return valid_questions
            
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            return self._fallback_questions(vocabulary)
    
    def _fallback_questions(self, vocabulary: list[dict]) -> list[dict]:
        """Generate simple fallback questions if AI fails"""
        questions = []
        
        for i, vocab in enumerate(vocabulary[:10]):
            if not vocab.get("word") or not vocab.get("definition"):
                continue
                
            question = {
                "question": f"What does the word '{vocab['word']}' mean?",
                "options": [
                    vocab["definition"],
                    "To move quickly",
                    "A type of food",
                    "Feeling happy"
                ],
                "correct_answer": 0,
                "explanation": f"'{vocab['word']}' means: {vocab['definition']}"
            }
            questions.append(question)
        
        return questions[:10]
