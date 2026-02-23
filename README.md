# 한결

**한국어** | [English](./README.en.md)

한국어 텍스트 어휘 등급 분석 및 문장 생성 웹 어플리케이션

## 주요 기능

1. **어휘 등급 분석**
   - 입력된 한국어 문장이나 텍스트의 어휘 등급을 실시간으로 분석합니다.
   - 초급, 중급, 고급 등 어휘 난이도 분포를 시각적으로 보여줍니다.

2. **맞춤형 예문 생성**
   - 특정 등급(예: 초급, 중급)과 키워드를 기반으로 학습자 수준에 맞는 예문을 생성합니다.
   - Google Gemini AI를 활용하여 자연스러운 문장을 제공합니다.

3. **자동 퀴즈 생성**
   - 제시된 지문을 바탕으로 빈칸 채우기, 의미 연결하기 등 다양한 유형의 문제를 자동으로 생성합니다.
   - 교재 개발자나 교사가 학습 자료를 제작하는 시간을 단축시켜 줍니다.


## 사전 준비 사항

- Python 3.8 이상
- Google Gemini API Key (생성 기능을 위해 필요)

> **⚠️ 주의 (API Key 미설정 시)**
> Google API Key가 없어도 프로그램 실행 및 기본적인 '어휘 등급 분석' 기능은 정상 작동합니다.
> 단, 아래 AI 의존 기능은 사용할 수 없습니다:
> - 어휘 등급 분석 중 동음이의어 문맥 기반 판별 (기본값으로 처리됨)
> - 맞춤형 예문 생성
> - 자동 퀴즈 생성

## 설치 및 실행

저장소를 클론하고 애플리케이션을 실행하기까지의 과정입니다.

### 1. 저장소 클론

```bash
git clone https://github.com/impulsive271/hangyeol.git
cd hangyeol
```

### 2. 가상환경 설정 (권장)

```bash
# macOS/Linux
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

프로젝트 루트 경로에 `.env` 파일을 생성하고 다음 내용을 추가해야 합니다.
`GOOGLE_API_KEY`는 [Google AI Studio](https://aistudio.google.com/)에서 발급받을 수 있습니다.

```bash
# .env 파일 생성
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

또는 `.env` 파일을 직접 만들어서 아래와 같이 작성하세요:
```
GOOGLE_API_KEY=사용자의_API_KEY_입력
```

### 5. 애플리케이션 실행

```bash
python app.py
```

### 6. 접속

브라우저를 열고 다음 주소로 접속합니다:
http://127.0.0.1:5000

## 인용 방법

[![DOI](https://img.shields.io/badge/DOI-10.16933/sfle.2026.40.1.49-blue.svg)](https://doi.org/10.16933/sfle.2026.40.1.49)

- 김태현, 유현조. (2026). 어휘 등급 기반 한국어 텍스트 분석과 생성을 위한 웹 애플리케이션 개발의 실제. *외국어교육연구*, *40*(1), 49–80. https://doi.org/10.16933/sfle.2026.40.1.49

```bibtex
@article{kim2026hangyeol,
  title     = {어휘 등급 기반 한국어 텍스트 분석과 생성을 위한 웹 애플리케이션 개발의 실제},
  author    = {김태현 and 유현조},
  journal   = {외국어교육연구},
  volume    = {40},
  number    = {1},
  pages     = {49--80},
  year      = {2026},
  doi       = {10.16933/sfle.2026.40.1.49}
}
```


