# 📈 Asset Analyzer (투자 자산 분석 시스템)

Asset Analyzer는 인공지능(LLM)과 정밀한 금융 엔진을 결합하여 주식 데이터를 실시간으로 분석하고 전문적인 투자 리포트를 생성하는 대시보드 시스템입니다.

## 🔗 서비스 접속 링크
**[Asset Analyzer 바로가기 (Demo)](https://asset-analyzer.duckdns.org)**

---

## 🚀 핵심 기능

1.  **AI 투자 분석 리포트**: LLM을 활용하여 기업의 투자 포인트, 리스크, 종합 의견을 생성합니다.
2.  **펀더멘털 추세 분석**: 매출액, 영업이익률 등 주요 재무 지표를 시각화하여 기업의 성장성을 확인합니다.
3.  **정밀 밸류에이션**: PEG Ratio, ROE, 유동비율 등을 통해 주가의 적정 가치를 다각도로 평가합니다.
4.  **기술적 분석 (Technical Analysis)**: RSI, 장기 이동평균선(200일, 300일)을 통해 매매 타이밍을 분석합니다.
5.  **리스크 진단**: 최대 낙폭(MDD), VaR(Value at Risk), 변동성 지표를 통해 투자 위험도를 측정합니다.

---

## 🛠 Tech Stack

### Backend
- **FastAPI**: 고성능 비동기 API 서버
- **PostgreSQL**: 데이터 및 분석 캐시 저장소
- **yfinance**: 실시간 금융 데이터 수집
- **Ollama / LLM**: AI 리서치 및 리포트 생성 엔진

### Frontend
- **Streamlit**: 대화형 데이터 대시보드
- **Plotly**: 전문적인 인터랙티브 금융 차트

### Infrastructure
- **Docker & Docker Compose**: 컨테이너 기반 마이크로서비스 아키텍처
- **Nginx**: 리버스 프록시 및 보안 설정

---

## ⚙️ 설치 및 실행 방법

### 1. Docker를 사용한 원클릭 실행 (권장)
Docker와 Docker Compose가 설치되어 있다면 모든 환경을 한 번에 구축할 수 있습니다.

```bash
# 레포지토리 클론
git clone [repository-url]
cd asset-analyzer

# 환경 변수 설정 (.env 파일 생성 및 API 키 등 입력)
cp .env.example .env 

# 컨테이너 빌드 및 실행
docker-compose up --build
```
- **Frontend**: `http://localhost:80`
- **Backend API**: `http://localhost:8000`

### 2. 로컬 개발 환경 설정

#### Backend 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### Frontend 실행
```bash
cd frontend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## 📂 프로젝트 구조

```text
asset-analyzer/
├── backend/            # FastAPI 서버 및 분석 엔진
│   ├── api/            # API 엔드포인트
│   ├── core/           # 설정 및 구성
│   ├── db/             # 데이터베이스 모델 및 세션
│   ├── services/       # 데이터 수집 및 분석 핵심 로직
│   └── models/         # Pydantic 스키마
├── frontend/           # Streamlit 대시보드
├── nginx/              # Nginx 설정 파일
├── docker-compose.yml  # 컨테이너 오케스트레이션
└── README.md           # 프로젝트 문서
```

---


