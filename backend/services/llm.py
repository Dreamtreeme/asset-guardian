import anthropic
import json
from core.config import settings

RESEARCH_REPORT_PROMPT = """
당신은 대한민국 최고의 금융 자산 분석가(Senior Equity Analyst)입니다.
제공된 종목 데이터를 바탕으로 전문적이고 신뢰도 높은 리서치 보고서를 작성하십시오.

## 핵심 요구사항
- **톤 앤 매너**: 극도의 절제미, 정량적 기반, 수식어 배제 (예: '강력한', '명확히', '충실히' 등 사용 금지)
- **언어**: 한국어 (투자의견은 매수/보유/비중축소 명시)
- **중복 엄금**: 모든 필드에서 동일한 수치를 반복 언급하지 마십시오.
- **간결성**: 수치 나열보다는 그 수치가 의미하는 '결론'만 한 문장으로 서술하십시오.

## 섹션별 작성 가이드 (JSON 각 필드)
1. `executive_summary`: 전체 분석의 최종 결론. **최대 3문장**으로 제한하며, 개별 분석 내용을 요약하지 말고 '최종 투자 판단'만 서술하십시오.
2. `fundamental_analysis`: 실적 추세와 수익성 방향성. 수치 나열 대신 '성장성 여부'만 서술하십시오.
3. `valuation_analysis`: 주가 매력도와 재무 건전성. PEG와 안정성 지표 기반의 가치 판단만 서술하십시오.
4. `technical_analysis`: RSI 및 이평선이 시사하는 현재의 '매매 위치'와 '단기 방향성'만 서술하십시오.
5. `risk_analysis`: 현재 가장 경계해야 할 핵심 리스크 1가지만 서술하십시오.

## 예시 답변 (JSON 형식)
```json
{
  "investment_rating": "보유 (HOLD)",
  "current_price": 72500,
  "key_thesis": "영업이익률 반등에 따른 수익성 회복 및 200일 이평선의 지지력 확인",
  "primary_risk": "RSI 85 수준의 단기 과매수 리스크 및 높은 변동성",
  "executive_summary": "수익성 회복세는 뚜렷하나 기술적 과중 구간에 진입했습니다. 신규 매수보다는 조정 시 비중 확대를 권고하는 보유 관점이 적절합니다.",
  "fundamental_analysis": "매출 반등과 영업이익률의 V자 회복으로 실적 턴어라운드 국면에 진입한 것으로 분석됩니다.",
  "valuation_analysis": "PEG 0.85로 성장성 대비 주가 매력은 높으나 부채비율 감소 여부에 대한 모니터링이 필요합니다.",
  "technical_analysis": "200일선 지지로 장기 상승 동력은 유효하나, 과매수 신호로 인한 단기 평균 회귀 가능성이 높습니다.",
  "risk_analysis": "과거 5년 MDD -45% 전례를 고려할 때 하락장 전환 시의 높은 변동성을 경계해야 합니다."
}
```

## 중요 규칙
- 반드시 ```json ... ``` 코드 블록으로 감싸십시오.
- 띄어쓰기를 정확히 하며, 단어 사이에 불필요한 공백을 넣지 마십시오.
- **`conclusion`, `report_markdown` 필드는 절대 생성하지 마십시오.** (중복 방지)
- **수식어를 배제하고 건조한 사실 위주로 작성하십시오.**
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
                model="claude-sonnet-4-5",
                max_tokens=2048,  
                temperature=0.3,    
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
                
                # 마크다운 리포트는 이제 프론트엔드에서 조립하므로 백엔드에서는 생성하지 않음
                if "report_markdown" in llm_output:
                    del llm_output["report_markdown"]
                if "conclusion" in llm_output:
                    del llm_output["conclusion"]

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
            "investment_rating": "데이터 분석 제한",
            "current_price": 0,
            "key_thesis": "데이터 수집 부족 또는 분석 오류",
            "primary_risk": "리스크 산출 불가",
            "is_success": False
        }

llm_service = LLMService()
