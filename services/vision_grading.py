import json
import logging
import time
from typing import Any, Dict, List, Optional

import config
from groq import Groq

# 기존 프로젝트 구조 호환: utils/json_schema.py 쪽에 validate_grading_json이 있다고 가정
from utils.json_schema import validate_grading_json

logger = logging.getLogger("studyt2c.vision")

_groq_client: Optional[Groq] = None


class VisionGradingError(Exception):
    """비전 채점 파이프라인 에러를 명확히 전달하기 위한 예외."""


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not config.GROQ_API_KEY:
            raise VisionGradingError("GROQ_API_KEY가 설정되지 않았습니다.")
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _model_vision() -> str:
    return config.get_env_var("GROQ_VISION_MODEL") or "meta-llama/llama-4-scout-17b-16e-instruct"


def _strip_fences(t: str) -> str:
    s = (t or "").strip()
    if s.startswith("```json"):
        s = s[7:].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    elif s.startswith("```"):
        s = s[3:].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s


def _extract_json_object(t: str) -> Dict[str, Any]:
    s = _strip_fences(t)
    if "{" in s and "}" in s:
        s = s[s.find("{") : s.rfind("}") + 1]
    return json.loads(s)


def grade_image_to_items(image_url: str) -> List[dict]:
    """
    보안 URL을 받아 Groq Vision 모델에 넘기고, 채점 결과 items(list)를 반환합니다.
    - JSON 스키마 검증 실패 시 재시도
    - 실패 원인 로깅 강화
    """
    base_prompt = """
주어진 문제지 이미지를 분석해서 각 문제의 채점 결과와 해설을 JSON 형식으로만 출력해.
마크다운 코드 블록(```json 등)이나 인사말은 절대 사용하지 말고 순수 JSON 텍스트만 반환해.
반드시 아래 구조를 지킬 것:
{
  "items": [
    {
      "item_no": 1,
      "question_text": "문제의 텍스트 내용",
      "is_correct": true,
      "explanation_summary": "학생이 이해하기 쉬운 한 줄 해설",
      "explanation_detail": "자세한 풀이 과정",
      "key_concepts": ["개념1", "개념2"]
    }
  ]
}
""".strip()

    prompt = base_prompt
    max_retries = 3
    client = _get_groq_client()

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=_model_vision(),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                temperature=0.1,
            )

            raw = resp.choices[0].message.content.strip()
            parsed = _extract_json_object(raw)

            ok, err = validate_grading_json(parsed)
            if not ok:
                raise ValueError(f"schema_validation_failed: {err}")

            items = parsed.get("items", [])
            if not isinstance(items, list):
                raise ValueError("items is not a list")

            return items

        except Exception as e:
            logger.exception("grade_image_to_items failed (attempt=%s/%s): %s", attempt + 1, max_retries, e)

            if attempt == max_retries - 1:
                raise VisionGradingError(
                    f"AI 채점에 실패했습니다. (원인: {e})"
                )

            # 재시도 시 프롬프트 강화 + 짧은 backoff
            prompt = base_prompt + "\n\n경고: 반드시 JSON만 출력. 다른 텍스트/마크다운/설명 금지."
            time.sleep(0.6 + 0.4 * attempt)

    # 여긴 사실상 도달하지 않음
    raise VisionGradingError("AI 채점 실패(unknown)")