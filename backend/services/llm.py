import anthropic
import json
from core.config import settings

RESEARCH_REPORT_PROMPT = """
당신은 대한민국 최고의 금융 자산 분석가(Senior Equity Analyst)입니다.
**오직 제공된 데이터**만을 바탕으로 리서치 리포트를 작성하십시오. 

## [절대 준수 법칙] (환각 및 이모지 사용 금지)
- **응답 본문에 이모지를 절대 사용하지 마십시오.** (예: 📊, 🚀, ✅ 등 사용 금지)
- **제공되지 않은 외부 뉴스나 사실을 절대 언급하지 마십시오.** (예: 'HBM3E', '설비투자', '수율 개선', 'NVDA 공급' 등 데이터에 명시되지 않은 구체적 경영 뉴스 금지)
- 오직 제공된 JSON 데이터 내의 수치와 차트의 시각적 요소(x, y축 흐름)에만 집중하십시오.
- 알 수 없는 데이터(예: P/B 미제공 등)는 임의로 추측하지 말고 언급을 피하십시오.

- **분량**: 전체 JSON 응답의 텍스트 총합이 **한글 기준 약 1200~1300자** 내외가 되도록 핵심 위주로 압축하여 서술하십시오.
- **언어**: 한국어

## 섹션별 작성 지침 (JSON 필드명 준수)
1. `investment_rating`: 'BUY', 'HOLD', 'REDUCE' 중 하나를 선택하십시오.
2. `executive_summary`: 투자 개요. 전체 데이터를 종합하여 투자의견이 도출된 핵심 논리를 **3~4문장**으로 요약하십시오.
3. `key_thesis`: 핵심 논거. 투자의견을 뒷받침하는 가장 강력한 긍정적 요인을 짧은 문단으로 서술하십시오.
4. `primary_risk`: 주요 리스크. 투자 시 가장 경계해야 할 부정적 요인을 짧은 문단으로 서술하십시오.
5. `fundamental_analysis`: 펀더멘털 분석. 매출/영업이익 추세 차트의 주요 수치와 변곡점을 설명하십시오.
6. `valuation_analysis`: 밸류에이션 분석. PEG/ROE/유동비율의 현재 상태를 전문적으로 평가하십시오.
7. `technical_analysis`: 기술적 지표 분석. RSI와 이동평균선(200일/300일) 기반의 매매 심리와 추세를 분석하십시오.
8. `risk_analysis`: AI 리스크 진단. MDD와 변동성을 기반으로 한 통계적 손실 위험을 제시하십시오.

## 중요 규칙
- 각 섹션은 독립적인 인사이트를 제공하되, 문장 간의 논리적 연결을 강화하십시오.
- **띄어쓰기를 철저히 하며, 단어 중간에 오타성 공백이 생기지 않도록 주의하십시오.**
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

        logger.info(f"[LLM] {company_name} ({symbol}) 분석 시작...")
        try:
            message = await self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=3000,  # 분량 최적화 (기존 대비 2/3 수준)
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
            logger.info(f"[LLM] 응답 수신 완료 (길이: {len(response_text)})")

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
                    logger.warning("[LLM] JSON 절단 감지, 복구 시도 중...")
                    
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
                            logger.info("[LLM] 절단된 JSON 복구 성공")
                        else:
                            raise  # 복구 불가능, 원래 에러 발생
                    else:
                        raise  # 복구 불가능

                logger.info(f"[LLM] JSON 파싱 및 데이터 구조화 성공")

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
