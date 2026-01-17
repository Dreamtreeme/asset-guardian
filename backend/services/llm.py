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

## 예시 답변 (JSON 형식 - 모범 답안 구조)
```json
{
  "investment_rating": "보유 (HOLD)",
  "current_price": 72500,
  "key_thesis": "1) 최근 분기 영업이익률의 V자 반등을 통한 수익성 회복 확인, 2) 200일 장기 이평선의 우상향 지지력 확보",
  "primary_risk": "RSI 85 수준의 단기 과매수 리스크 및 과거 5년 MDD -40%를 상회하는 높은 심리적 변동성",
  "executive_summary": "동사는 2025년 3분기 실적 성장을 통해 펀더멘털의 질적 개선을 입증했으나, 단기 기술적 과열로 인해 추가 매수보다는 보유 전략이 유리합니다. 재무 안정성이 견조하므로 기술적 조정 시 분할 매수 기회로 활용할 것을 권고합니다.",
  "fundamental_analysis": "매출 추세 차트에서 확인되듯 최근 4분간의 정체를 깨고 매출 15% 반등에 성공했습니다. 특히 영업이익률이 25Q2 저점인 6%에서 14%로 급격히 회복된 점은 효율적인 비용 통제가 이루어지고 있음을 시사합니다.",
  "valuation_analysis": "현재 밸류에이션 게이지상 PEG 0.85는 이익 성장성 대비 주가가 저평가 구간에 진입했음을 보여줍니다. ROE 15%와 유동비율 250% 수준의 건전한 재무 구조가 주가의 하방 경직성을 강력하게 지지하고 있습니다.",
  "technical_analysis": "가격 차트의 200일 이평선이 우상향으로 전환되며 장기 상승 모멘텀을 확보했습니다. 다만 RSI 막대 차트가 80을 상회하는 과매수 신호를 보내고 있어, 이평선 이격도를 좁히는 단기 평균 회귀 과정이 예상됩니다.",
  "risk_analysis": "과거 5년 최대 낙폭(MDD) -45%의 높은 변동성 이력을 고려할 때, 단기 과열 구간에서의 추격 매수는 위험합니다. VaR(5%) 기준 일간 -2.5% 수준의 변동성을 염두에 둔 분산 투자 관점의 접근이 필수적입니다.",
  "conclusion": "실적 회복세와 장기 추세 변곡점이 일치하는 매력적인 구간이나, 단기 과열 리스크를 고려하여 투자의견 '보유(HOLD)'를 유지하며 조정 시 비중 확대를 제안합니다.",
  "report_markdown": "# [종목명] 투자 심층 분석 보고서\n\n## 1. 투자 하이라이트\n...(중략)...\n"
}
```

## 중요 규칙 (안정성 및 전문성)
- 반드시 ```json ... ``` 코드 블록으로 감싸 모든 필드를 채우십시오.
- 이모지 사용 금지, 전문적인 톤 유지.
- 제공되지 않은 외부 데이터 추측 금지.
- **텍스트 포맷팅 제한 (가독성)**:
    - **중요**: 모든 필드 내에서 `**강조**` (Bold) 표시를 절대 사용하지 마십시오.
    - **중요**: 각 분석 필드(`fundamental_analysis` 등) 내에서 `###`와 같은 마크다운 제목 태그를 사용하지 마십시오.
    - **중요**: `(경미한 증가)`와 같은 소괄호`( )` 사용을 최소화하고 풀어서 서술하십시오.
"""

import logging
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_report(self, analysis_data: dict) -> dict:
        symbol = analysis_data.get("symbol")
        company_name = analysis_data.get("company_name", symbol)
        data_context = json.dumps(analysis_data, indent=2, ensure_ascii=False)

        logger.info(f"🚀 [LLM] {company_name} ({symbol}) 분석 시작...")
        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-5",  # Opus → Sonnet으로 변경 (속도 개선)
                max_tokens=8192,  # 4096 -> 8192로 확장하여 긴 보고서 절단 방지
                system=RESEARCH_REPORT_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"다음 수집된 데이터를 바탕으로 {company_name} ({symbol}) 종목에 대한 기관투자자용 리서치 보고서를 작성하십시오. 절대로 응답이 중간에 끊어지지 않도록 JSON 형식을 엄격히 준수하십시오.\n\n[데이터]\n{data_context}"
                    }
                ]
            )
            response_text = message.content[0].text
            logger.info(f"✅ [LLM] 응답 수신 완료 (길이: {len(response_text)})")

            # JSON 파싱
            try:
                # 가장 바깥쪽의 { } 블록을 찾음
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx+1].strip()
                else:
                    json_str = response_text
                
                # 파싱 시도
                try:
                    llm_output = json.loads(json_str)
                except json.JSONDecodeError:
                    # 절단된 JSON 복구 시도: 마지막 완전한 필드까지만 파싱
                    logger.warning("⚠️ [LLM] JSON 절단 감지, 복구 시도 중...")
                    
                    # 마지막 완전한 "key": "value" 쌍 이후로 자르기
                    last_quote = json_str.rfind('"')
                    if last_quote > 0:
                        # 마지막 따옴표 이전의 마지막 콤마 또는 중괄호 찾기
                        search_area = json_str[:last_quote]
                        last_comma = search_area.rfind(',')
                        
                        if last_comma > 0:
                            # 마지막 콤마까지 자르고 닫는 중괄호 추가
                            recovered_json = json_str[:last_comma] + '}'
                            llm_output = json.loads(recovered_json)
                            logger.info("✅ [LLM] 절단된 JSON 복구 성공")
                        else:
                            raise  # 복구 불가능, 원래 에러 발생
                    else:
                        raise  # 복구 불가능

                logger.info(f"✨ [LLM] JSON 파싱 및 데이터 구조화 성공")

                # 문자열 필드 정리
                for key in ['key_thesis', 'primary_risk']:
                    if key in llm_output and isinstance(llm_output[key], str):
                        llm_output[key] = llm_output[key].replace('\n', ' ').strip()
                
                # 마크다운 보고서가 불충분할 경우에만 보조적으로 생성
                if "report_markdown" not in llm_output or len(llm_output.get("report_markdown", "")) < 100:
                    report_markdown = f"""# {company_name} ({symbol})

## 투자 요약

{llm_output.get('executive_summary', 'N/A')}

## 펀더멘털 분석

{llm_output.get('fundamental_analysis', 'N/A')}

## 밸류에이션 분석

{llm_output.get('valuation_analysis', 'N/A')}

## 기술적 분석

{llm_output.get('technical_analysis', 'N/A')}

## 리스크 분석

{llm_output.get('risk_analysis', 'N/A')}

## 결론 및 전략

{llm_output.get('conclusion', 'N/A')}
"""
                    llm_output["report_markdown"] = report_markdown

                # 디버그 정보 추가
                llm_output["_debug"] = {
                    "full_prompt": f"System: {RESEARCH_REPORT_PROMPT}\n\nUser: {company_name} ({symbol}) 데이터 분석 요청",
                    "raw_data_sent": analysis_data,
                    "raw_response": response_text
                }
                
                # 성공 플래그 추가
                llm_output["is_success"] = True

                return llm_output
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 파싱 에러: {e}")
                logger.error(f"📄 원본 응답 텍스트: {response_text}")
            
        except Exception as e:
            logger.error(f"❌ LLM 호출 중 예외 발생: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()

        
        # 기본 응답 (파싱 실패 또는 예외 발생 시)
        return {
            "investment_rating": "보유 (HOLD)",
            "current_price": 0,
            "key_thesis": "데이터 분석 중",
            "primary_risk": "불확실성",
            "report_markdown": "보고서 생성 중 오류가 발생했습니다.",
            "is_success": False
        }

llm_service = LLMService()
