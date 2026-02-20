import json
import logging
import time
from typing import Any, Dict, Optional

import config
from groq import Groq

logger = logging.getLogger("studyt2c.llm")

# 내부 캐시
_groq_client: Optional[Groq] = None


class LlmServiceError(Exception):
    """LLM 호출/파싱 관련 에러를 명확히 전달하기 위한 예외."""


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not config.GROQ_API_KEY:
            raise LlmServiceError("GROQ_API_KEY가 설정되지 않았습니다.")
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _model_text() -> str:
    return config.get_env_var("GROQ_TEXT_MODEL") or "llama-3.3-70b-versatile"


def _extract_json(text: str) -> Dict[str, Any]:
    """
    모델이 JSON 앞뒤로 설명/코드펜스를 붙였을 때 최대한 복구.
    """
    t = (text or "").strip()

    # 코드 펜스 제거
    if t.startswith("```"):
        # ```json ... ``` 형태 포함
        t = t.strip("`").strip()
        # 위 방식이 부족할 수 있어 아래도 한 번 더
        if t.lower().startswith("json"):
            t = t[4:].strip()

    # 중괄호 영역만 잘라내기
    if "{" in t and "}" in t:
        t = t[t.find("{") : t.rfind("}") + 1]

    return json.loads(t)


def classify_subject(text: str) -> dict:
    """
    질문을 분석하여 과목 자동 분류.
    실패해도 UI가 죽지 않도록 안전한 기본값 반환.
    """
    prompt = (
        f"질문: '{text}'\n"
        "이 질문의 과목을 KOREAN, ENGLISH, MATH, SCIENCE, OTHER 중 하나로 분류하세요.\n"
        "반드시 JSON 형식으로만 응답하세요.\n"
        '예: {"subject": "MATH", "confidence": 0.9}'
    )

    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = res.choices[0].message.content
        data = _extract_json(raw)
        # 최소 보정
        if "subject" not in data:
            return {"subject": "OTHER", "confidence": 0.0}
        return data
    except Exception as e:
        logger.exception("classify_subject failed: %s", e)
        return {"subject": "OTHER", "confidence": 0.0}


def chat_with_tutor(user_message: str, mode: str = "studying") -> str:
    """
    AI 튜터 대화.
    실패 시 사용자에게 보이는 메시지로 반환(서비스 예외를 그대로 내지 않음).
    """
    system_prompt = (
        f"당신은 친절한 AI 튜터입니다. 현재 모드: {mode}.\n"
        "'studying' 모드 시 학습 외 질문은 정중히 거절하고, 학습으로 유도하세요."
    )
    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=0.5,
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.exception("chat_with_tutor failed: %s", e)
        return f"AI 튜터 연결 오류: {e}"


def generate_practice_question(key_concepts: list) -> Optional[dict]:
    """
    개념 기반 연습문제 생성.
    실패하면 None (UI에서 '생성 실패' 처리)
    """
    prompt = (
        f"개념 [{', '.join(key_concepts)}]에 대한 객관식 문제 1개를 생성하세요.\n"
        "반드시 JSON 구조로만 응답:\n"
        '{"question": "문제\\n1)..", "answer_key": "1", "explanation": "해설"}'
    )

    # 간단 재시도 (JSON 깨짐 방지)
    for attempt in range(2):
        try:
            client = _get_groq_client()
            res = client.chat.completions.create(
                model=_model_text(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = res.choices[0].message.content
            data = _extract_json(raw)

            if not isinstance(data, dict) or not data.get("question"):
                raise ValueError("practice json missing 'question'")

            return data
        except Exception as e:
            logger.exception("generate_practice_question failed (attempt=%s): %s", attempt + 1, e)
            prompt += "\n\n주의: 반드시 JSON만 출력. 다른 문장/마크다운 금지."
            time.sleep(0.3)

    return None


def generate_parent_report(student_name: str, stats: dict) -> str:
    """
    학부모용 리포트 생성.
    실패 시 짧은 실패 문구 반환(UX 유지)
    """
    prompt = (
        f"학생 {student_name}의 통계(질문:{stats.get('chat_count', 0)}회, "
        f"오답:{stats.get('total_wrong', 0)}개, "
        f"취약개념:{', '.join(stats.get('top_weak_concepts', []))})\n"
        "을 바탕으로 학부모용 리포트를 한글로 작성하세요. (짧고 명확하게)"
    )

    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.exception("generate_parent_report failed: %s", e)
        return "리포트 생성 실패"