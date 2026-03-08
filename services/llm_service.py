import json
import logging
import time
from typing import Any, Dict, List, Optional

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


def generate_quiz_from_qa(question_text: str, answer_text: str) -> Optional[Dict[str, Any]]:
    """
    AI 튜터에서 나온 질문·답변을 바탕으로 5지선다 객관식 1문항 생성.
    반환: {"question": "...", "options": ["1) ...", "2) ...", ... 5개], "correct_index": 0~4}
    실패 시 None.
    """
    prompt = (
        "다음은 학생이 AI 튜터에게 했던 질문과 튜터의 답변입니다.\n\n"
        f"질문: {question_text[:400]}\n\n답변: {answer_text[:600]}\n\n"
        "이 내용을 바탕으로 **객관식 문제 1개**를 만들어 주세요. "
        "보기는 반드시 **5개(1번~5번)**이고, 정답은 1개만 있습니다.\n\n"
        "반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 금지.\n"
        '{"question": "문제 문장", "options": ["1) 보기1", "2) 보기2", "3) 보기3", "4) 보기4", "5) 보기5"], "correct_index": 0}\n'
        "correct_index는 정답이 몇 번째 보기인지 0부터 셀 때의 인덱스(0~4)입니다."
    )
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
                raise ValueError("quiz json missing question")
            options = data.get("options") or []
            if not isinstance(options, list) or len(options) < 5:
                # 5개 미만이면 나머지 빈 문자열로 채움
                options = list(options)[:5]
                while len(options) < 5:
                    options.append(f"{len(options)+1}) (보기 없음)")
            else:
                options = [str(o) for o in options[:5]]
            correct_index = int(data.get("correct_index", 0))
            if correct_index < 0 or correct_index > 4:
                correct_index = 0
            return {
                "question": str(data.get("question", "")).strip(),
                "options": options,
                "correct_index": correct_index,
            }
        except Exception as e:
            logger.exception("generate_quiz_from_qa failed (attempt=%s): %s", attempt + 1, e)
            time.sleep(0.3)
    return None


def generate_weakness_analysis_from_quiz(
    student_name: str,
    stats: Dict[str, Any],
    wrong_items: List[Dict[str, Any]],
    recent_attempts: List[Dict[str, Any]],
) -> str:
    """
    질의개념복습 이력을 보고 AI가 취약점을 분석해 문단으로 반환.
    """
    total = stats.get("total") or 0
    correct = stats.get("correct") or 0
    wrong = stats.get("wrong") or 0
    accuracy_pct = stats.get("accuracy_pct") or 0

    prompt = (
        f"다음은 학생 '{student_name}'의 **질의개념복습** 풀이 이력 요약입니다.\n\n"
        f"- 총 풀이: {total}문항, 정답: {correct}, 오답: {wrong}, 정답률: {accuracy_pct}%\n\n"
    )
    if recent_attempts:
        prompt += "【최근 풀이 샘플 (최대 10건)】\n"
        for i, a in enumerate(recent_attempts[:10], 1):
            q = (a.get("source_question") or "")[:150]
            quiz_q = (a.get("quiz_question") or "")[:120]
            ok = "O" if a.get("is_correct") else "X"
            prompt += f"{i}. 원질문: {q}... | 출제문제: {quiz_q}... | {ok}\n"
        prompt += "\n"
    if wrong_items:
        prompt += "【오답 목록 (취약점 분석 핵심)】\n"
        for i, w in enumerate(wrong_items[:15], 1):
            sq = (w.get("source_question") or "")[:200]
            sa = (w.get("source_answer") or "")[:200]
            prompt += f"{i}. 원질문: {sq}\n   원답변: {sa}\n"
        prompt += "\n"
    prompt += (
        "위 데이터를 **전부 참고**해서, 이 학생의 학습 취약점을 2~4문장으로 요약해 주세요. "
        "구체적인 개념·유형을 언급하고, 복습 권장 방향을 한 줄 정도 포함해 주세요. 한글로만 작성하세요."
    )

    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return (res.choices[0].message.content or "").strip() or "취약점 분석을 생성하지 못했습니다."
    except Exception as e:
        logger.exception("generate_weakness_analysis_from_quiz failed: %s", e)
        return "취약점 분석 생성 실패"


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


def recommend_concepts_from_chat(chat_items: List[Dict[str, Any]], max_concepts: int = 6) -> List[str]:
    """
    AI 튜터 Q&A 이력을 보고, 더 이해하면 좋을 개념을 추천.
    chat_items: [{"question": "...", "answer": "..."}, ...]
    반환: 개념 이름 리스트 (예: ["일차방정식 풀이", "제곱수 계산"])
    """
    if not chat_items:
        return []
    summary = "\n\n".join(
        f"Q: {(it.get('question') or '')[:200]}\nA: {(it.get('answer') or '')[:300]}"
        for it in chat_items[:15]
    )
    prompt = (
        "다음은 학생이 AI 튜터와 나눈 질문·답변 일부입니다.\n\n"
        f"{summary}\n\n"
        "이 대화를 바탕으로, 이 학생이 **더 공부하면 좋을 개념**을 "
        f"한글 개념명으로 최대 {max_concepts}개 추천해 주세요. "
        "초·중·고 수준에 맞는 구체적인 개념명으로 (예: 일차방정식 풀이, 제곱수 계산, 삼각형 성질).\n\n"
        "반드시 JSON 배열만 한 줄로 출력하세요. 예: [\"개념1\", \"개념2\"]"
    )
    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = (res.choices[0].message.content or "").strip()
        if raw.startswith("["):
            arr = json.loads(raw)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr[:max_concepts] if x]
        return []
    except Exception as e:
        logger.exception("recommend_concepts_from_chat failed: %s", e)
        return []


def explain_concept(concept_name: str) -> str:
    """개념 이름에 대한 짧은 설명 문단 (학생용)."""
    prompt = (
        f"'{concept_name}' 개념을 초·중·고 학생이 이해할 수 있도록 "
        "2~4문장으로 쉽게 설명해 주세요. 한글로만 작성하세요."
    )
    try:
        client = _get_groq_client()
        res = client.chat.completions.create(
            model=_model_text(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return (res.choices[0].message.content or "").strip() or "설명을 불러오지 못했습니다."
    except Exception as e:
        logger.exception("explain_concept failed: %s", e)
        return "설명을 불러오는 중 오류가 발생했습니다."