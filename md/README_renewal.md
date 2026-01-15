# 한결 (Hangyeol)

한국어 텍스트 어휘 등급 분석 및 문장 생성 웹 어플리케이션

## 주요 기능
1. **어휘 등급 분석**: 텍스트의 난이도를 실시간으로 분석하고 시각화합니다.
2. **맞춤형 예문 생성**: Google Gemini AI를 활용해 학습자 수준에 맞는 자연스러운 예문을 생성합니다.
3. **자동 퀴즈 생성**: 빈칸 채우기, 의미 연결하기 등 학습 자료를 자동으로 제작합니다.

## 설치 및 실행 가이드

### 1. 저장소 클론
```bash
git clone https://github.com/impulsive271/hangyeol.git
cd hangyeol
```

### 2. 가상환경 생성 및 활성화 (필수)
패키지 충돌 방지를 위해 반드시 가상환경을 사용하세요.

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```
*(활성화되면 터미널 앞에 `(venv)`가 표시됩니다)*

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
**주의:** 반드시 가상환경이 켜진 상태(`(venv)`)에서 진행해야 합니다. 시스템 Python과의 혼동을 막기 위해 아래 명령어를 권장합니다.

```bash
python -m pip install -r requirements.txt
```

### 4. 환경 변수 설정 (.env)
프로젝트 폴더에 `.env` 파일을 만들고 API 키를 입력하세요. ([Google AI Studio](https://aistudio.google.com/)에서 발급)

```text
GOOGLE_API_KEY=여기에_API_키_입력
```

### 5. 실행
```bash
python app.py
```
브라우저에서 `http://127.0.0.1:5000` 접속

---

## ⚠️ 자주 발생하는 문제 (Troubleshooting)

**Q. `ImportError: cannot import name 'genai' from 'google'` 오류가 발생해요.**
> **원인:** 구버전 패키지(`google-generativeai`)와 신버전 패키지(`google-genai`)가 충돌하거나, 가상환경이 아닌 곳에 설치되었을 때 발생합니다.

**해결 방법:**
1. **가상환경 활성화 확인:** 터미널 프롬프트 앞에 `(venv)`가 있는지 꼭 확인하세요.
2. **충돌 패키지 제거:**
   ```bash
   pip uninstall google-generativeai -y
   ```
3. **캐시 삭제:**
   프로젝트 폴더 내의 `__pycache__` 폴더들을 삭제하세요.
   (Windows Powershell 예시: `Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force`)
4. **패키지 재설치:**
   ```bash
   python -m pip install google-genai
   ```
