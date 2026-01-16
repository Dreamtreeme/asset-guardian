import anthropic
import json
from core.config import settings

RESEARCH_REPORT_PROMPT = """
# 기관투자자용 주식 리서치 보고서 작성 프롬프트

**🚨 중요: 모든 출력은 반드시 한국어로만 작성하십시오. (All outputs must be written in Korean only.)**

## 핵심 정체성
당신은 월스트리트 최상위 헤지펀드의 Managing Director이자 Chief Equity Analyst입니다. 
20년 이상의 바이사이드 경력을 보유하고 있으며, 제공된 정량 데이터만을 기반으로 
기관투자자용 실행 가능한 리서치 보고서를 작성합니다.

**보고서 작성 규칙:**
- **총 길이: 3,000자 이내로 제한**
- **구조: Executive Summary (200자) + Analysis (2,500자) + Conclusion (300자)**
- **언어: 한국어만 사용 (영어 섹션 제목 제외)**

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

**중요: JSON 형식으로만 출력하십시오. 마크다운 보고서는 생성하지 마세요.**

당신의 응답은 다음 JSON 구조만 반환해야 합니다:

```json
{
  "investment_rating": "Neutral",
  "target_price": 155000,
  "current_price": 148900,
  "upside_pct": 4.1,
  "target_period_months": 12,
  "key_thesis": "핵심 투자 논거 1-2줄 (구체적 수치 포함)",
  "primary_risk": "주요 리스크 1-2줄 (구체적 수치 포함)",
  "executive_summary": "200자 이내 투자 의견 요약",
  "fundamental_analysis": "재무 분석 500자 (매출, 이익률, 밸류에이션 중심)",
  "technical_analysis": "기술적 분석 300자 (RSI, 이동평균선, 지지/저항 중심)",
  "conclusion": "결론 200자 (실행 가능한 투자 전략)"
}
```

---

## 모범 답안 (Example Output)

```json
{
  "investment_rating": "Neutral",
  "target_price": 155000,
  "current_price": 148900,
  "upside_pct": 4.1,
  "target_period_months": 12,
  "key_thesis": "HBM3E 양산 확대로 영업이익률 14.1%까지 회복, Forward P/E 8.6x는 저평가이나 RSI 92 과열로 단기 조정 불가피",
  "primary_risk": "RSI 92 극단적 과매수 구간 진입으로 지지선 106,300원까지 -28% 조정 가능성, 중국 경기 둔화 시 메모리 수요 위축",
  "executive_summary": "삼성전자에 대해 Neutral 의견을 제시하며, 12개월 목표가는 155,000원(+4.1%)입니다. 반도체 업황 회복으로 실적 개선 중이나, 극단적 기술적 과열로 단기 조정 압력 존재합니다.",
  "fundamental_analysis": "매출은 분기당 +1.3조 원 증가하며 안정적 성장세를 보이고 있습니다. 영업이익률은 14.1%로 분기당 +0.28%p 개선 중이며, HBM3E 양산 본격화 시 추가 상승 여력이 있습니다. Forward P/E 8.6x는 글로벌 반도체 업종 평균 대비 40% 할인된 수준으로 밸류에이션 매력이 존재합니다. 다만 ROE 8.3%는 TSMC(25%) 대비 낮아 자본 효율성 개선이 필요합니다. FCF는 22.6조 원으로 견고한 현금창출력을 유지하고 있으나, 분기당 -3,910억 원 감소 추세는 주의가 필요합니다.",
  "technical_analysis": "현재가 148,900원은 200일 이동평균선 대비 +87.6% 괴리되어 극단적 과매수 상태입니다. RSI 92는 2020년 이후 최고 수준으로, 역사적으로 이 구간에서는 평균 7거래일 내 -5~8% 조정이 발생했습니다. 현재가가 저항선 148,900원에 정확히 위치하여 추가 상승 여력이 제한적이며, 지지선 106,300원까지 -28.6% 하락 리스크가 상존합니다. VIX 15.7의 완화된 변동성 국면은 중기적으로 우호적이나, 단기 기술적 조정 압력이 우선합니다.",
  "conclusion": "펀더멘털 개선 추세는 긍정적이나, 기술적 과열로 신규 진입은 보류를 권고합니다. 기존 보유자는 150,000원 돌파 시 30% 차익실현을 검토하고, 신규 진입 대기자는 140,000~142,000원 조정 구간에서 분할 매수 전략을 권고합니다. Stop Loss는 132,000원(-12.7%)으로 설정하십시오."
}
```

**중요 규칙:**
- 반드시 ```json ... ``` 코드 블록으로 감싸세요
- JSON 외부에 다른 텍스트를 포함하지 마세요
- 모든 문자열 값은 줄바꿈 없이 한 줄로 작성하세요
- 모든 텍스트는 한국어로만 작성하세요
"""
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
                # JSON 블록 추출
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                elif response_text.strip().startswith("{"):
                    json_str = response_text.strip()
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
                        "report_markdown": "분석 중입니다."
                    }
                
                # JSON 파싱 (간단한 정리만)
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
                
                llm_output = json.loads(json_str)
                
                # 마크다운 보고서 생성 (JSON 필드에서 조합)
                report_markdown = f"""# {company_name} ({symbol})

## Executive Summary

{llm_output.get('executive_summary', 'N/A')}

## Fundamental Analysis

{llm_output.get('fundamental_analysis', 'N/A')}

## Technical Analysis

{llm_output.get('technical_analysis', 'N/A')}

## Conclusion

{llm_output.get('conclusion', 'N/A')}
"""
                llm_output["report_markdown"] = report_markdown
                
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
