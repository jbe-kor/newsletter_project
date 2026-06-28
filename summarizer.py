from openai import OpenAI

from config import Settings
from news_collector import NewsArticle

SYSTEM_PROMPT = """당신은 반도체 산업 전문 애널리스트입니다.
주어진 뉴스 기사 목록(제목과 링크)을 바탕으로 오늘의 반도체 동향을 요약합니다.

각 기사 또는 주제별로 반드시 아래 3줄 구조로 작성하세요:
1. 기술적 핵심 팩트
2. 기존 공정 한계와 배경
3. 향후 공급망 영향

한국어로 작성하고, 불필요한 수식어 없이 간결하게 압축하세요.
기사가 여러 건이면 주제별로 구분해 요약하되, 중복 내용은 통합하세요."""


def _format_articles(articles: list[NewsArticle]) -> str:
    lines = []
    for i, article in enumerate(articles, start=1):
        lines.append(f"[{i}] ({article.keyword}) {article.title}")
        lines.append(f"    링크: {article.link}")
        if article.published:
            lines.append(f"    게시: {article.published}")
    return "\n".join(lines)


def summarize_articles(articles: list[NewsArticle], settings: Settings) -> str:
    """수집된 기사를 OpenAI API로 3줄 구조 요약합니다."""
    if not articles:
        return "오늘 수집된 반도체 뉴스가 없습니다."

    client = OpenAI(api_key=settings.openai_api_key)
    user_content = (
        "다음 반도체 관련 뉴스 기사들을 3줄 구조로 요약해 주세요.\n\n"
        f"{_format_articles(articles)}"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
