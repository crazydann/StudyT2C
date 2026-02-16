import json
import config
from groq import Groq
from utils.json_schema import validate_grading_json

# Groq 클라이언트 세팅
groq_client = Groq(api_key=config.GROQ_API_KEY)

def grade_image_to_items(image_url: str) -> list:
    """보안 URL을 받아 AI Vision 모델에 넘기고, 채점 결과(JSON)를 반환합니다."""
    
    prompt = """
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
    """
    
    # 기획안 기반 3번 재시도(Retry) 로직 적용
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 비전 AI 모델 호출 (Groq의 최신 Llama 4 Vision 활용)
            response = groq_client.chat.completions.create(
                model=config.get_env_var("GROQ_VISION_MODEL") or "meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                temperature=0.1, 
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # AI가 혹시라도 마크다운 찌꺼기를 붙였으면 제거
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
                
            parsed_data = json.loads(result_text)
            
            # 스키마 검증 통과하면 결과 리스트 반환
            is_valid, err_msg = validate_grading_json(parsed_data)
            if is_valid:
                return parsed_data.get("items", [])
            else:
                raise ValueError(f"AI 응답 형식 오류: {err_msg}")
                
        except Exception as e:
            print(f"AI 채점 시도 {attempt + 1}/{max_retries} 실패: {e}")
            if attempt == max_retries - 1: # 마지막 3번째 시도까지 실패하면 에러 발생
                raise Exception(f"AI 채점 형식을 3회 연속 실패했습니다. 다시 시도해 주세요. ({str(e)})")
            
            # 재시도 시 프롬프트를 좀 더 강력하게 수정 (가스라이팅 강화)
            prompt += "\n\n경고: 반드시 JSON 양식만 제출하세요! 다른 설명은 절대 금지합니다."