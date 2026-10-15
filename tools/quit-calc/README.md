# 퇴사 계산기 (퇴직금·실업급여)

2026년 기준 퇴직금과 실업급여(구직급여)를 계산하는 정적 웹페이지입니다. 빌드 없이 `index.html`을 브라우저로 열면 동작합니다.

- 계산 로직: `calc.js` (기준값은 `RULES_2026`에 모아 둠, 매년 1월 갱신 필요)
- 테스트: `node tools/quit-calc/calc.test.js`
- 광고: `index.html`의 `.ad-slot` 자리를 애드센스 코드로 교체
- 배포: `main`에 합쳐지면 Pages 워크플로가 `site/`와 함께 `/quit-calc/` 경로로 배포 (https://bamb177.github.io/dino/quit-calc/)
- 안내 글: `guide/`, 검색엔진 제출용 `sitemap.xml`
