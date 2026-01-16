import anthropic
import json
from core.config import settings

RESEARCH_REPORT_PROMPT = """
# 기관투자자용 주식 리서치 보고서 작성 프롬프트 (최종판)

## 핵심 정체성
당신은 월스트리트 최상위 헤지펀드의 Managing Director이자 Chief Equity Analyst입니다. 
20년 이상의 바이사이드 경력을 보유하고 있으며, 제공된 정량 데이터만을 기반으로 
기관투자자용 실행 가능한 리서치 보고서를 작성합니다.

## 중요: 데이터 구조 이해

당신에게 제공되는 데이터는 다음 3개 섹션으로 구성됩니다:

### 1. long_term (장기 펀더멘털)
```json
{
  "evidence": {
    "재무추세": {
      "매출": {
        "사용가능": true/false,
        "최신값": 86061747000000.0,  // 최근 분기 매출액
        "기울기": 1270407999999.36,   // 분기당 평균 증감량
        "최근개선비율": 0.4,           // 최근 8분기 중 전분기 대비 개선된 비율
        "분기수": 5                    // 데이터 포인트 수
      },
      "영업이익률": { ... },
      "순이익률": { ... },
      "FCF": { ... },
      "부채_자본": { ... }
    },
    "장기추세": {
      "현재가": 148900.0,
      "200일선": 79347.75,
      "300일선": 71348.17,
      "200일선_기울기": 12.10,        // 양수=상승추세, 음수=하락추세
      "300일선_기울기": -20.96,
      "최근5년_MDD": -0.45           // 최대낙폭 (음수값, -0.45 = -45%)
    },
    "밸류에이션": {
      "trailingPE": null,            // null이면 "데이터 없음"
      "forwardPE": 8.57,
      "priceToBook": null,
      "trailingPEG": 1.15,
      "marketCap": 995557782847488,
      "ROE": 0.12,                   // 자기자본이익률 (있는 경우)
      "ROA": 0.08,                   // 총자산이익률 (있는 경우)
      "currentRatio": 2.1,           // 유동비율 (있는 경우)
      "quickRatio": 1.5              // 당좌비율 (있는 경우)
    },
    "판정": "✅ 개선" / "❌ 악화" / "⚠️ 혼합"
  },
  "outlook": "장기 우호" / "장기 중립" / "장기 비우호"
}
```

### 2. mid_term (중기 기술적 분석)
```json
{
  "evidence": {
    "국면": "완화",                    // VIX 기반 시장 국면
    "VIX": 15.48,                     // 변동성 지수
    "지지선": 106300.0,
    "저항선": 148900.0,
    "익절_손절비": 2.5,               // (저항-현재)/(현재-지지), null 가능
    "RSI": 92.0                       // 14일 RSI
  },
  "outlook": "중기 우호" / "중기 중립" / "중기 비우호"
}
```

### 3. short_term (단기 전술)
```json
{
  "evidence": {
    "전일": {
      "거래량배수": 1.22,             // 20일 평균 대비 배수
      "갭": 0.0097,                   // 시가갭 (0.0097 = +0.97%)
      "캔들바디": 0.0248              // 종가-시가 (0.0248 = +2.48%)
    },
    "금일피봇": {
      "Pivot": 147566.67,
      "R1": 150833.33,                // 1차 저항
      "S1": 145633.33                 // 1차 지지
    },
    "RSI": 92.0
  },
  "outlook": "단기 중립"
}
```

---

## 보고서 작성 구조

### Section 1: Executive Summary (3-4줄)

**필수 포함 요소:**
1. 투자의견: **Overweight** / **Neutral** / **Underweight**
2. 목표가: "현재가 ₩XXX → 목표가 ₩YYY (+ZZ%, N개월)"
3. 핵심 논거 1개 (가장 강력한 수치 근거)
4. 리스크 요약 1줄

**보고서 길이:** 최대 500단어 이내로 간결하게 작성

---

## 출력 형식 (필수)

당신의 응답은 **두 부분**으로 구성됩니다:

**1단계: JSON 메타데이터 블록**
```json
{
  "investment_rating": "Overweight",
  "target_price": 92000,
  "current_price": 76800,
  "upside_pct": 19.8,
  "target_period_months": 12,
  "key_thesis": "핵심 투자 논거 1줄 (줄바꿈 금지)",
  "primary_risk": "주요 리스크 1줄 (줄바꿈 금지)"
}
```

**2단계: 마크다운 보고서**
JSON 블록 다음 줄부터 상세 리서치 보고서를 마크다운 형식으로 작성하세요.
줄바꿈, 표, 특수문자 등을 자유롭게 사용할 수 있습니다.

**중요:**
- JSON 블록은 반드시 ```json ... ``` 코드 블록으로 감싸세요
- JSON에는 report_markdown 필드를 포함하지 마세요
- 마크다운 보고서는 JSON 블록 바로 다음 줄부터 시작하세요
"""

class LLMService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_report(self, analysis_data: dict) -> dict:
        symbol = analysis_data.get("symbol")
        company_name = analysis_data.get("company_name", symbol)
        data_context = json.dumps(analysis_data, indent=2, ensure_ascii=False)

        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-5",  # Opus → Sonnet으로 변경 (속도 개선)
                max_tokens=4096,  # 8192 → 4096으로 감소 (간결한 보고서)
                system=RESEARCH_REPORT_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"다음 수집된 데이터를 바탕으로 {company_name} ({symbol}) 종목에 대한 기관투자자용 리서치 보고서를 작성하십시오.\n\n[데이터]\n{data_context}"
                    }
                ]
            )
            response_text = message.content[0].text
            print(f"\n{'='*50}\n[DEBUG] LLM RESPONSE RECEIVED ({len(response_text)} chars)\n{response_text}\n{'='*50}")
            
            # JSON 파싱 시도
            try:
                # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    
                    # 마크다운 보고서 추출 (JSON 블록 이후의 모든 텍스트)
                    markdown_start = json_end + 3  # ``` 이후
                    report_markdown = response_text[markdown_start:].strip()
                    
                elif response_text.strip().startswith("{"):
                    json_str = response_text.strip()
                    report_markdown = ""
                else:
                    # JSON 형식이 아니면 기본 구조 반환
                    return {
                        "investment_rating": "Neutral",
                        "target_price": 0,
                        "current_price": 0,
                        "upside_pct": 0,
                        "target_period_months": 12,
                        "key_thesis": "데이터 분석 중",
                        "primary_risk": "불확실성",
                        "report_markdown": response_text
                    }
                
                # JSON 파싱 (이제 report_markdown 필드 없음, 간단한 정리만)
                import re
                json_str = re.sub(
                    r'("key_thesis"\s*:\s*")(.*?)(")',
                    lambda m: m.group(1) + m.group(2).replace('\n', ' ').strip() + m.group(3),
                    json_str,
                    flags=re.DOTALL
                )
                json_str = re.sub(
                    r'("primary_risk"\s*:\s*")(.*?)(")',
                    lambda m: m.group(1) + m.group(2).replace('\n', ' ').strip() + m.group(3),
                    json_str,
                    flags=re.DOTALL
                )
                
                print(f"[DEBUG] Extracted JSON string (first 300 chars): {json_str[:300]}")
                print(f"[DEBUG] Extracted markdown (first 200 chars): {report_markdown[:200] if report_markdown else 'EMPTY'}")
                
                llm_output = json.loads(json_str)
                llm_output["report_markdown"] = report_markdown  # 마크다운 추가
                
                print(f"[DEBUG] LLM JSON PARSED: {llm_output.get('investment_rating')}, Target: {llm_output.get('target_price')}")
                print(f"[DEBUG] Report length: {len(report_markdown)} chars")
                print(f"[DEBUG] Final llm_output keys: {list(llm_output.keys())}")
                return llm_output
                
            except json.JSONDecodeError as e:
                print(f"[WARNING] JSON 파싱 실패: {e}")
                print(f"[DEBUG] 문제의 JSON 문자열 (first 1000 chars): {json_str[:1000] if 'json_str' in locals() else 'N/A'}")
                return {
                    "investment_rating": "Neutral",
                    "target_price": 0,
                    "current_price": 0,
                    "upside_pct": 0,
                    "target_period_months": 12,
                    "key_thesis": "JSON 파싱 실패",
                    "primary_risk": "데이터 오류",
                    "report_markdown": response_text
                }
                
        except Exception as e:
            return {
                "investment_rating": "Neutral",
                "target_price": 0,
                "current_price": 0,
                "upside_pct": 0,
                "target_period_months": 12,
                "key_thesis": f"보고서 생성 오류: {str(e)}",
                "primary_risk": "시스템 오류",
                "report_markdown": f"보고서 생성 중 오류 발생: {str(e)}"
            }

llm_service = LLMService()
