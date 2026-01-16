# 프론트엔드 실행 가이드

생성된 프론트엔드 코드를 확인하는 두 가지 방법을 안내해 드립니다.

## 1. 로컬 환경에서 실행 (권장)

Python이 설치되어 있다면 다음 명령어로 즉시 실행할 수 있습니다.

```bash
# 1. frontend 디렉토리로 이동
cd frontend

# 2. 가상환경 생성 (권한 오류 발생 시 아래 '팁' 참고)
python -m venv venv

# 3. 가상환경 활성화 (사용 중인 터미널에 맞춰 선택)
source venv/Scripts/activate


# 4. 필요한 라이브러리 설치
pip install -r requirements.txt

# 5. Streamlit 앱 실행
streamlit run app.py
```

> [!TIP]
> **`Permission denied` 오류가 발생한다면?**
> 1. 터미널(CMD 또는 Git Bash)을 **관리자 권한**으로 실행해 보세요.
> 2. 만약 기존에 만든 `venv` 폴더가 있다면 삭제(`rm -rf venv`) 후 다시 시도해 보세요.
> 3. 만약 여전히 안 된다면, 가상환경 없이 바로 `pip install -r requirements.txt`를 실행해도 무방합니다 (단, 전역 환경에 설치됨).

---

## 2. Docker를 사용하여 실행

Docker가 설치되어 있다면 환경 구축 없이 컨테이너로 실행할 수 있습니다.

```bash
# 1. 이미지 빌드
docker build -t asset-analyzer-fe ./frontend

# 2. 컨테이너 실행
docker run -p 8501:8501 asset-analyzer-fe
```
**참고**: 컨테이너 실행 후 동일하게 `http://localhost:8501`에서 확인 가능합니다.
