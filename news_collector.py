from dataclasses import dataclass
from urllib.parse import quote

import feedparser

KEYWORDS = ["반도체 공정", "TSMC", "HBM"]
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
)


@dataclass(frozen=True)
class NewsArticle:
    title: str
    link: str
    keyword: str
    published: str | None = None


def fetch_news(keywords: list[str] | None = None) -> list[NewsArticle]:
    """구글 뉴스 RSS에서 키워드별 기사 제목·링크를 수집합니다."""
    keywords = keywords or KEYWORDS
    seen_links: set[str] = set()
    articles: list[NewsArticle] = []

    for keyword in keywords:
        url = GOOGLE_NEWS_RSS.format(query=quote(keyword))
        feed = feedparser.parse(url)

        for entry in feed.entries:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not link or not title or link in seen_links:
                continue

            seen_links.add(link)
            published = entry.get("published") or entry.get("updated")
            articles.append(
                NewsArticle(
                    title=title,
                    link=link,
                    keyword=keyword,
                    published=published,
                )
            )

    return articles
