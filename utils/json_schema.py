def validate_grading_json(data: dict) -> tuple[bool, str]:
    """AI가 반환한 JSON이 우리가 기획한 규격에 맞는지 검사합니다."""
    if "items" not in data:
        return False, "'items' 리스트가 없습니다."
    
    for item in data["items"]:
        # 필수 항목들이 모두 있는지 체크
        required_keys = ["item_no", "question_text", "is_correct", "explanation_summary", "explanation_detail"]
        if not all(k in item for k in required_keys):
            return False, "문항 데이터에 필수 항목이 누락되었습니다."
            
    return True, ""