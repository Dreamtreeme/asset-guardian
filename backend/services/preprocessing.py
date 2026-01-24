"""
데이터 전처리 유틸리티
LLM에게 전달하기 전에 숫자를 인간 친화적 형식으로 변환
"""

def format_krw(value: float) -> str:
    """
    원화를 한국어 단위로 변환
    예: 86061747000000.0 -> "86.1조 원"
    """
    if value is None:
        return "N/A"
    
    if abs(value) >= 1_000_000_000_000:  # 조
        return f"{value / 1_000_000_000_000:.1f}조 원"
    elif abs(value) >= 100_000_000:  # 억
        return f"{value / 100_000_000:.0f}억 원"
    elif abs(value) >= 10_000:  # 만
        return f"{value / 10_000:.0f}만 원"
    else:
        return f"{value:,.0f} 원"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    소수를 퍼센트로 변환
    예: 0.1414 -> "14.1%"
    """
    if value is None:
        return "N/A"
    
    return f"{value * 100:.{decimal_places}f}%"


def format_slope(value: float, unit: str = "원") -> str:
    """
    기울기를 증감 표현으로 변환
    예: 1270407999999.36 -> "분기당 +1.3조 원"
    """
    if value is None:
        return "N/A"
    
    direction = "+" if value >= 0 else ""
    
    if abs(value) >= 1_000_000_000_000:  # 조
        return f"분기당 {direction}{value / 1_000_000_000_000:.1f}조 {unit}"
    elif abs(value) >= 100_000_000:  # 억
        return f"분기당 {direction}{value / 100_000_000:.0f}억 {unit}"
    else:
        return f"분기당 {direction}{value:,.0f} {unit}"


def format_trend(slope: float) -> str:
    """
    기울기를 추세 표현으로 변환
    예: 12.10 -> "강한 상승 (+12.1)"
         -20.96 -> "하락 (-21.0)"
    """
    if slope is None:
        return "N/A"
    
    if slope > 10:
        return f"강한 상승 (+{slope:.1f})"
    elif slope > 0:
        return f"완만한 상승 (+{slope:.1f})"
    elif slope > -10:
        return f"완만한 하락 ({slope:.1f})"
    else:
        return f"강한 하락 ({slope:.1f})"


def format_ratio(value: float, decimal_places: int = 2) -> str:
    """
    비율을 소수점으로 표현
    예: 2.624 -> "2.62배"
    """
    if value is None:
        return "N/A"
    
    return f"{value:.{decimal_places}f}배"


def preprocess_financial_data(data: dict) -> dict:
    """
    재무 데이터를 LLM 친화적 형식으로 전처리
    """
    if not data or "evidence" not in data:
        return data
    
    evidence = data["evidence"]
    
    # 재무추세 전처리
    if "재무추세" in evidence:
        trends = evidence["재무추세"]
        
        for key in ["매출", "영업이익률", "순이익률", "FCF"]:
            if key in trends and trends[key].get("사용가능"):
                item = trends[key]
                
                # 원본 값 유지하면서 표시용 값 추가
                if "최신값" in item:
                    if key in ["매출", "FCF"]:
                        item["최신값_표시"] = format_krw(item["최신값"])
                    else:
                        item["최신값_표시"] = format_percentage(item["최신값"])
                
                if "기울기" in item:
                    if key in ["매출", "FCF"]:
                        item["기울기_표시"] = format_slope(item["기울기"])
                    else:
                        item["기울기_표시"] = format_slope(item["기울기"], "% 포인트")
    
    # 장기추세 전처리
    if "장기추세" in evidence:
        lt = evidence["장기추세"]
        
        if "현재가" in lt:
            lt["현재가_표시"] = format_krw(lt["현재가"])
        if "200일선" in lt:
            lt["200일선_표시"] = format_krw(lt["200일선"])
        if "300일선" in lt:
            lt["300일선_표시"] = format_krw(lt["300일선"])
        if "200일선_기울기" in lt:
            lt["200일선_추세"] = format_trend(lt["200일선_기울기"])
        if "300일선_기울기" in lt:
            lt["300일선_추세"] = format_trend(lt["300일선_기울기"])
        if "최근5년_MDD" in lt:
            lt["최근5년_MDD_표시"] = format_percentage(lt["최근5년_MDD"])
    
    # 밸류에이션 전처리
    if "밸류에이션" in evidence:
        val = evidence["밸류에이션"]
        
        if "marketCap" in val:
            val["marketCap_표시"] = format_krw(val["marketCap"])
        if "ROE" in val:
            val["ROE_표시"] = format_percentage(val["ROE"])
        if "ROA" in val:
            val["ROA_표시"] = format_percentage(val["ROA"])
        if "currentRatio" in val:
            val["currentRatio_표시"] = format_ratio(val["currentRatio"])
        if "quickRatio" in val:
            val["quickRatio_표시"] = format_ratio(val["quickRatio"])
    
    return data


def preprocess_technical_data(data: dict) -> dict:
    """
    기술적 분석 데이터를 LLM 친화적 형식으로 전처리
    """
    if not data or "evidence" not in data:
        return data
    
    evidence = data["evidence"]
    
    if "지지선" in evidence:
        evidence["지지선_표시"] = format_krw(evidence["지지선"])
    if "저항선" in evidence:
        evidence["저항선_표시"] = format_krw(evidence["저항선"])
    
    return data


def preprocess_short_term_data(data: dict) -> dict:
    """
    단기 전략 데이터를 LLM 친화적 형식으로 전처리
    """
    if not data or "evidence" not in data:
        return data
    
    evidence = data["evidence"]
    
    if "금일피봇" in evidence:
        pivot = evidence["금일피봇"]
        
        if "Pivot" in pivot:
            pivot["Pivot_표시"] = format_krw(pivot["Pivot"])
        if "R1" in pivot:
            pivot["R1_표시"] = format_krw(pivot["R1"])
        if "S1" in pivot:
            pivot["S1_표시"] = format_krw(pivot["S1"])
    
    return data
