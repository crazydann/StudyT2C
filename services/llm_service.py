import json
import config
from groq import Groq

groq_client = Groq(api_key=config.GROQ_API_KEY)

def classify_subject(text: str) -> dict:
    """질문을 분석하여 과목을 자동 분류합니다."""
    prompt = f"질문: '{text}'\n이 질문의 과목을 KOREAN, ENGLISH, MATH, SCIENCE, OTHER 중 하나로 분류하세요. 반드시 JSON 형식으로 응답하세요. 예: {{\"subject\": \"MATH\", \"confidence\": 0.9}}"
    try:
        res = groq_client.chat.completions.create(
            model=config.get_env_var("GROQ_TEXT_MODEL") or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        text = res.choices[0].message.content.strip()
        if "{" in text: text = text[text.find("{"):text.rfind("}")+1]
        return json.loads(text)
    except: return {"subject": "OTHER", "confidence": 0.0}

def chat_with_tutor(user_message: str, mode: str = "studying") -> str:
    system_prompt = f"당신은 친절한 AI 튜터입니다. 현재 모드: {mode}. 'studying' 모드 시 학습 외 질문은 차단하세요."
    try:
        res = groq_client.chat.completions.create(
            model=config.get_env_var("GROQ_TEXT_MODEL") or "llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=0.5,
        )
        return res.choices[0].message.content
    except Exception as e: return f"AI 튜터 연결 오류: {e}"

def generate_practice_question(key_concepts: list) -> dict:
    prompt = f"개념 [{', '.join(key_concepts)}]에 대한 객관식 문제 1개를 생성하세요. 반드시 JSON 구조로 응답: {{\"question\": \"문제\\n1)..\", \"answer_key\": \"1\", \"explanation\": \"해설\"}}"
    try:
        res = groq_client.chat.completions.create(
            model=config.get_env_var("GROQ_TEXT_MODEL") or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = res.choices[0].message.content.strip()
        if "{" in text: text = text[text.find("{"):text.rfind("}")+1]
        return json.loads(text)
    except: return None

def generate_parent_report(student_name: str, stats: dict) -> str:
    prompt = f"학생 {student_name}의 통계(질문:{stats['chat_count']}회, 오답:{stats['total_wrong']}개, 취약개념:{', '.join(stats.get('top_weak_concepts', []))}) 분석 리포트를 한글로 작성하세요."
    try:
        res = groq_client.chat.completions.create(
            model=config.get_env_var("GROQ_TEXT_MODEL") or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return res.choices[0].message.content
    except: return "리포트 생성 실패"