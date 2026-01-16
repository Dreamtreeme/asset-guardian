import anthropic
import json
from core.config import settings

RESEARCH_REPORT_PROMPT = """
당신은 대한민국 최고의 금융 자산 분석가(Senior Equity Analyst)입니다.
제공된 종목 데이터를 바탕으로 전문적이고 신뢰도 높은 리서치 보고서를 작성하십시오.

## 핵심 요구사항
- **톤 앤 매너**: 보수적, 정량적, 논리적 (추측 배제)
- **언어**: 텍스트는 모두 **한국어**로 작성 (투자의견은 매수/보유/비중축소 명기)
- **대상**: 신중한 기관 투자자 및 고액 자산가

## 데이터 분석 기준
- **재무**: 매출 성장세, 영업이익률 추이, PEG Ratio(<1 저평가), ROE(수익성), 유동성
- **기술**: RSI(70상회 과열/30하회 과매도), 200일·300일 이동평균선 기반 장기 추세
- **리스크**: 최대 낙폭(MDD), 연간 변동성(Volatility), VaR(5%) 기반 리스크 관리 권고

## 예시 답변 (JSON 형식)
```json
{
  "investment_rating": "매수 (BUY)",
  "current_price": 148900,
  "key_thesis": "1) 분기 매출 및 영업이익률의 견조한 회복세 지속, 2) 장기 이평선 상향 돌파를 통한 추세 전환 확인",
  "primary_risk": "RSI 92 수준의 극단적 기술적 과열 및 과거 5년 MDD -45%를 고려한 변동성 리스크",
  "executive_summary": "동사는 최근 펀더멘털 개선세가 뚜렷하며 장기 상승 추세 진입을 시도하고 있습니다. 다만 기술적 지표상의 과열 시그널이 관찰되므로 분할 매수 관점의 접근을 권고합니다.",
  "fundamental_analysis": "최근 매출액이 전분기 대비 1.5% 성장하며 질적 성장을 지속하고 있습니다. 영업이익률 또한 14%대를 회복하며 효율적인 비용 관리가 이루어지고 있는 것으로 분석됩니다.",
  "valuation_analysis": "현재 PEG 1.15는 성장성 대비 균형 잡힌 주가 수준을 의미하며, ROE 및 유동비율 역시 업계 평균 이상의 건전성을 유지하고 있습니다.",
  "technical_analysis": "가격이 200일 및 300일 이동평균선을 우상향 돌파하며 장기적인 추세 역전이 나타나고 있습니다. 단, RSI 90 초과는 단기 조정을 암시하는 과매수 구간입니다.",
  "conclusion": "안정적인 펀더멘털과 장기 추세의 결합으로 매수(BUY) 의견을 유지하되, 단기 과열로 인한 변동성 관리를 위해 철저한 분할 매수 전략이 필요합니다.",
  "report_markdown": "# 리서치 보고서... (상세 내용)"
}
```

**중요 규칙:**
- 반드시 ```json ... ``` 코드 블록으로 감싸세요.
- 모든 필드는 반드시 채워져야 하며, 한국어로만 작성하세요.
- **수치적 목표가(Target Price)나 정확한 상승여력(Upside %)을 제시하지 마십시오.** (데이터 부재로 인한 허위 정보 방지)
- **`report_markdown` 필드는 단순히 개별 섹션을 합친 것이 아니라, 모든 분석(재무, 밸류에이션, 기술적 분석)을 종합하여 인사이트를 도출하는 하나의 완성된 전문 보고서여야 합니다.** (데이터 간의 상관관계를 분석에 포함하세요)
- **모든 출력에서 이모지(Emoji)나 픽토그램을 사용하지 마십시오.** (전문 리서치 보고서의 톤 유지)
- 제공된 데이터에 기반한 분석만 작성하세요 (추측 금지).
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

            
            # JSON 파싱
            try:
                # JSON 추출
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                else:
                    json_str = response_text
                
                # 파싱 및 정리
                llm_output = json.loads(json_str)

                
                # 문자열 필드 정리
                for key in ['key_thesis', 'primary_risk']:
                    if key in llm_output and isinstance(llm_output[key], str):
                        llm_output[key] = llm_output[key].replace('\n', ' ').strip()
                
                # 마크다운 보고서가 불충분할 경우에만 보조적으로 생성
                if "report_markdown" not in llm_output or len(llm_output["report_markdown"]) < 100:
                    report_markdown = f"""# {company_name} ({symbol})

## 투자 요약

{llm_output.get('executive_summary', 'N/A')}

## 펀더멘털 분석

{llm_output.get('fundamental_analysis', 'N/A')}

## 밸류에이션 분석

{llm_output.get('valuation_analysis', 'N/A')}

## 기술적 분석

{llm_output.get('technical_analysis', 'N/A')}

## 결론 및 전략

{llm_output.get('conclusion', 'N/A')}
"""
                    llm_output["report_markdown"] = report_markdown
                

                return llm_output
                
            except json.JSONDecodeError as e:
                pass
            
        except Exception as e:
            pass

        
        # 기본 응답 (파싱 실패 또는 예외 발생 시)

        return {
            "investment_rating": "보유 (HOLD)",
            "current_price": 0,
            "key_thesis": "데이터 분석 중",
            "primary_risk": "불확실성",
            "report_markdown": "보고서 생성 중 오류가 발생했습니다."
        }

llm_service = LLMService()
