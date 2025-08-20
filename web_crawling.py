import os
import time
import math
from typing import Optional

# trafilatura
import trafilatura
from trafilatura import fetch_url, extract
from trafilatura.settings import use_config

# 진행바
from tqdm import tqdm

# ====== OpenAI 클라이언트 준비 ======
# 최신 SDK 우선 시도 후, 구버전으로 자동 폴백
def _get_openai_client():
    try:
        from openai import OpenAI  # >=1.0.0
        return ("new", OpenAI())
    except Exception:
        import openai  # <=0.28.x
        return ("legacy", openai)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")

client_type, client = _get_openai_client()
if client_type == "legacy":
    client.api_key = OPENAI_API_KEY  # type: ignore
else:
    # 최신 SDK는 환경변수로 자동 인식. 필요시 아래처럼 지정 가능
    # client = OpenAI(api_key=OPENAI_API_KEY)
    pass

# ====== 분석할 URL 목록 ======
urls = [
    "https://news.naver.com/section/105",
    "https://news.naver.com/section/104",
]

# ====== trafilatura 설정 ======
# 타임아웃 및 허용길이 등 기본 설정 보강
cfg = use_config()
cfg.set("DEFAULT", "timeout", "10")
cfg.set("DEFAULT", "min_extracted_size", "200")

# ====== GPT 호출 래퍼 ======
def gpt_chat_completion(prompt: str, text: str, max_chars: int = 6000, temperature: float = 0.3,
                        model_new: str = "gpt-4o-mini", model_legacy: str = "gpt-4",
                        max_retries: int = 5, base_delay: float = 1.5) -> str:
    try:
        content = text if len(text) <= max_chars else text[:max_chars]
        # 지수적 백오프
        for attempt in range(max_retries):
            try:
                if client_type == "new":
                    # OpenAI >=1.0.0
                    resp = client.chat.completions.create(  # type: ignore[attr-defined]
                        model=model_new,
                        messages=[
                            {"role": "system", "content": "간결하고 정확하게 한국어로 답변하세요."},
                            {"role": "user", "content": f"{prompt}\n\n{text}"}
                        ],
                        temperature=temperature,
                    )
                    return resp.choices[0].message.content or ""
                else:
                    # OpenAI <=0.28.x
                    resp = client.ChatCompletion.create(  # type: ignore[attr-defined]
                        model=model_legacy,
                        messages=[
                            {"role": "system", "content": "간결하고 정확하게 한국어로 답변하세요."},
                            {"role": "user", "content": f"{prompt}\n\n{text}"}
                        ],
                        temperature=temperature,
                    )
                    return resp.choices[0].message["content"] or ""
            except Exception as e:
                # 레이트리밋 또는 일시적 네트워크 오류 시 재시도
                is_last = attempt == max_retries - 1
                if is_last:
                    return f"[ERROR] GPT 호출 실패: {e}"
                sleep_s = base_delay * math.pow(2, attempt)
                time.sleep(sleep_s)
        return "[ERROR] GPT 호출 실패: 재시도 초과"
    except Exception as e:
        return f"[ERROR] GPT 래퍼 오류: {e}"

# ====== 본문 추출 유틸 ======
def extract_main_text(url: str, min_len: int = 500) -> Optional[str]:
    try:
        downloaded = fetch_url(url, config=cfg)
        if not downloaded:
            return None
        text = extract(downloaded, config=cfg, include_comments=False, include_formatting=False)
        if not text:
            return None
        text = text.strip()
        if len(text) < min_len:
            return None
        return text
    except Exception:
        return None

# ====== 보고서 생성 ======
report_lines = []
report_lines.append("# 자동 분석 보고서")
report_lines.append("")

for url in tqdm(urls, desc="Processing"):
    report_lines.append(f"## URL: {url}")
    report_lines.append("")
    try:
        main_text = extract_main_text(url)
        if not main_text:
            report_lines.append("본문 추출 실패 또는 너무 짧음")
            report_lines.append("---")
            continue

        # 1. 요약
        summary = gpt_chat_completion("다음 글의 핵심 내용을 요약해줘", main_text)
        report_lines.append("### 요약")
        report_lines.append(summary if summary else "(빈 응답)")
        report_lines.append("")

        # 2. 키워드와 인사이트
        insight = gpt_chat_completion("이 글에서 중요한 키워드 5개와 그 설명을 알려줘", main_text)
        report_lines.append("### 주요 키워드와 인사이트")
        report_lines.append(insight if insight else "(빈 응답)")
        report_lines.append("")
    except Exception as e:
        report_lines.append(f"에러 발생: {e}")
    report_lines.append("---")

    # API 속도 제한 완화용 딜레이
    time.sleep(2)

# ====== 보고서 저장 ======
output_path = "weekly_web_report.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print(f"보고서 생성 완료: {output_path}")
