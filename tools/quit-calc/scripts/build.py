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


def page(path, title, desc, body, depth):
    up = "../" * depth or "./"
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
  <link rel="canonical" href="{BASE}{path}">
  <link rel="stylesheet" href="{up}style.css">
</head>
<body>
  <header class="top"><a class="home" href="{up}">← 퇴사 계산기</a></header>
  <main class="article card">
    <h1>{title}</h1>
{body.rstrip()}
    <p class="cta"><a href="{up}">퇴직금·실업급여 바로 계산하기 →</a></p>
  </main>
  <footer class="foot"><a href="{up}guide/">안내 글 모음</a> · <a href="{up}privacy.html">개인정보처리방침</a></footer>
</body>
</html>
'''


def write(path, html):
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    urls = ["", "guide/"]
    sections = []
    for group, slugs in GUIDES:
        items = []
        for slug in slugs:
            title, desc, body = read(slug)
            path = f"guide/{slug}.html"
            write(path, page(path, title, desc, body, 1))
            urls.append(path)
            items.append(f'      <li><a href="{slug}.html">{title}</a></li>')
        sections.append(f"    <h2>{group}</h2>\n    <ul>\n" + "\n".join(items) + "\n    </ul>")

    write("guide/index.html", page(
        "guide/", "퇴사 안내 글 모음",
        "퇴직금, 실업급여, 연차수당까지 퇴사 전에 알아야 할 내용을 모았습니다.",
        "    <p>퇴사를 앞두고 많이 묻는 질문을 주제별로 정리했습니다.</p>\n" + "\n".join(sections), 1))

    title, desc, body = read("_privacy")
    write("privacy.html", page("privacy.html", title, desc, body, 0))
    urls.append("privacy.html")

    today = date.today().isoformat()
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
          + "</urlset>\n")
    print(f"built {len(urls)} urls")


if __name__ == "__main__":
    main()
