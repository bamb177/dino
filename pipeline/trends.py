"""요즘 뜨는 키워드 수집.

- Google 트렌드 급상승 RSS (키 불필요)
- YouTube 인기 급상승 동영상 제목 (YT_API_KEY 가 있을 때)
네트워크가 막혀 있거나 실패하면 빈 목록을 돌려주고, 매니저는 캐릭터 테마로 대체합니다.
"""
import os
import xml.etree.ElementTree as ET

import requests

TRENDS_RSS = "https://trends.google.com/trending/rss?geo={geo}"
HT = "{https://trends.google.com/trending/rss}"


def parse_trends_rss(xml_text: str) -> list[dict]:
    items = []
    for item in ET.fromstring(xml_text).iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        traffic = (item.findtext(f"{HT}approx_traffic") or "").strip()
        news = [(n.findtext(f"{HT}news_item_title") or "").strip() for n in item.findall(f"{HT}news_item")]
        items.append({"keyword": title, "source": "google_trends", "traffic": traffic, "news": [n for n in news if n][:2]})
    return items


def google_trends(geo: str = "KR", limit: int = 15) -> list[dict]:
    r = requests.get(TRENDS_RSS.format(geo=geo), timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return parse_trends_rss(r.text)[:limit]


def youtube_popular(geo: str = "KR", limit: int = 15) -> list[dict]:
    key = os.environ.get("YT_API_KEY")
    if not key:
        return []
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet", "chart": "mostPopular", "regionCode": geo, "maxResults": limit, "key": key},
        timeout=20,
    )
    r.raise_for_status()
    return [
        {"keyword": v["snippet"]["title"], "source": "youtube_popular", "traffic": "", "news": []}
        for v in r.json().get("items", [])
    ]


def collect(geo: str = "KR") -> list[dict]:
    out = []
    for fn in (google_trends, youtube_popular):
        try:
            out += fn(geo)
        except Exception as e:  # 네트워크/쿼터 문제는 치명적이지 않음
            print(f"[trends] {fn.__name__} 실패: {e}")
    return out
