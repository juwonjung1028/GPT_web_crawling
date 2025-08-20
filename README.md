# GPT_web_crawling
GPT API를 사용하여, 웹 크롤링해주는 프로그램. 요약 보고서 형태로 출력

## 빠른실행방법
1. PowerShell에서 가상환경 만들기
 > py -3 -m venv .venv  
 .\.venv\Scripts\Activate.ps1

2. 패키지 설치
 > python -m pip install --upgrade pip  
 pip install openai trafilatura tqdm

3. OpenAI 키 설정
 > PowerShell 세션에만 적용  
 $env:OPENAI_API_KEY = "여기에_실제_API_키"

 > 영구 등록 후 새 터미널에서 사용  
 setx OPENAI_API_KEY "여기에_실제_API_키"

4. 스크립트 점검
- web_crawling.py 안의 urls 리스트를 실제 기사 주소로 바꿉니다.

5. 실행
 > python web_crawling.py

