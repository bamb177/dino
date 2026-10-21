"""content/*.html 조각으로 안내 글 페이지, 글 모음, sitemap.xml을 만든다.

사용법: python3 tools/quit-calc/scripts/build.py
글을 추가하면 content/에 파일을 넣고 GUIDES 목록에 slug를 추가한 뒤 다시 실행한다.
"""
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://bamb177.github.io/dino/quit-calc/"

# 글 모음에 보이는 순서와 묶음
GUIDES = [
    ("퇴직금", ["severance-how", "severance-tax", "severance-unpaid", "severance-interim"]),
    ("실업급여", ["unemployment-voluntary", "unemployment-contract-end", "unemployment-part-time"]),
    ("연차", ["annual-leave-pay"]),
]


def read(slug):
    s = open(os.path.join(ROOT, "content", slug + ".html"), encoding="utf-8").read()
    title = re.search(r"<!-- title: (.*?) -->", s).group(1)
    desc = re.search(r"<!-- description: (.*?) -->", s).group(1)
    body = re.sub(r"<!-- (title|description): .*? -->\n", "", s)
    return title, desc, body


FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
# 계산기 첫 화면에 보여 줄 글
FEATURED = ["severance-how", "unemployment-voluntary", "annual-leave-pay", "severance-unpaid"]


def guide_card(href, tag, title):
    return (f'        <a class="guide-card" href="{href}"><span class="tag tag-{tag}">{tag}</span>'
            f'<span class="t">{title}</span><span class="arrow">›</span></a>')


def page(path, title, desc, body, depth, tag=None, lead=None, related=""):
    up = "../" * depth or "./"
    head_tag = f'<span class="tag tag-{tag}">{tag}</span>\n      ' if tag else ""
    lead_html = f"<p>{lead}</p>" if lead else ""
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | 퇴사 계산기</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="article">
  <meta name="theme-color" content="#1b64da">
  <link rel="canonical" href="{BASE}{path}">
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
  <link rel="stylesheet" href="{FONT}">
  <link rel="stylesheet" href="{up}style.css">
</head>
<body>
  <nav class="nav">
    <div class="wrap">
      <a class="brand" href="{up}"><span class="brand-mark">퇴</span>퇴사 계산기</a>
      <a class="nav-link" href="{up}guide/">안내 글</a>
    </div>
  </nav>
  <main class="wrap">
    <header class="article-head">
      {head_tag}<h1>{title}</h1>
      {lead_html}
    </header>
    <article class="card article">
{body.rstrip()}
    </article>
    <a class="cta-card" href="{up}"><b>내 퇴직금·실업급여 계산하기 →</b><span>2026년 기준으로 1분 만에 확인해 보세요</span></a>
{related}  </main>
  <footer class="foot"><a href="{up}guide/">안내 글</a><a href="{up}privacy.html">개인정보처리방침</a></footer>
</body>
</html>
'''


def write(path, html):
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    urls = ["", "guide/"]
    meta = {}
    for group, slugs in GUIDES:
        for slug in slugs:
            meta[slug] = (group,) + read(slug)

    sections = []
    for group, slugs in GUIDES:
        cards = []
        for slug in slugs:
            _, title, desc, body = meta[slug]
            others = [s for g, ss in GUIDES for s in ss if s != slug]
            same = [s for s in slugs if s != slug]
            pick = (same + [s for s in others if s not in same])[:3]
            related = ('    <section class="section">\n      <h2 class="section-title">함께 읽으면 좋은 글</h2>\n'
                       '      <div class="guides">\n'
                       + "\n".join(guide_card(f"{s}.html", meta[s][0], meta[s][1]) for s in pick)
                       + "\n      </div>\n    </section>\n")
            path = f"guide/{slug}.html"
            write(path, page(path, title, desc, body, 1, tag=group, related=related))
            urls.append(path)
            cards.append(guide_card(f"{slug}.html", group, title))
        sections.append(f'    <h2 class="section-title">{group}</h2>\n    <div class="guides">\n'
                        + "\n".join(cards) + "\n    </div>")

    # 글 모음은 본문 카드 없이 주제별 카드 목록만 보여 준다
    listing = page("guide/", "퇴사 안내 글 모음",
                   "퇴직금, 실업급여, 연차수당까지 퇴사 전에 알아야 할 내용을 모았습니다.",
                   "", 1, lead="퇴사를 앞두고 많이 묻는 질문을 주제별로 정리했어요.")
    listing = listing.replace('    <article class="card article">\n\n    </article>\n', "\n".join(sections) + "\n")
    write("guide/index.html", listing)

    title, desc, body = read("_privacy")
    write("privacy.html", page("privacy.html", title, desc, body, 0))
    urls.append("privacy.html")

    # 계산기 첫 화면의 추천 글 카드
    idx_path = os.path.join(ROOT, "index.html")
    idx = open(idx_path, encoding="utf-8").read()
    cards = "\n".join(guide_card(f"guide/{s}.html", meta[s][0], meta[s][1]) for s in FEATURED)
    idx = re.sub(r"<!-- guides:start -->.*?<!-- guides:end -->",
                 lambda m: f"<!-- guides:start -->\n{cards}\n<!-- guides:end -->", idx, flags=re.S)
    write("index.html", idx)

    today = date.today().isoformat()
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
          + "</urlset>\n")
    print(f"built {len(urls)} urls")


if __name__ == "__main__":
    main()
