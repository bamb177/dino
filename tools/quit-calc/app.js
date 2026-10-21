(function () {
  const fmt = (n) => Math.round(n).toLocaleString("ko-KR");
  const won = (n) => fmt(n) + "원";
  const num = (v) => Number(String(v || "").replace(/[^\d]/g, "")) || 0;
  const seg = document.querySelector(".seg");
  const out = document.getElementById("result");

  function selectTab(id) {
    seg.dataset.active = id;
    seg.querySelectorAll(".seg-btn").forEach((b) => {
      const on = b.dataset.tab === id;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on);
    });
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === id));
    out.hidden = true;
  }
  seg.querySelectorAll(".seg-btn").forEach((b) => b.addEventListener("click", () => selectTab(b.dataset.tab)));

  // 금액 입력칸 천 단위 쉼표
  document.querySelectorAll('input[inputmode="numeric"]').forEach((el) => {
    el.addEventListener("input", () => {
      const n = num(el.value);
      el.value = n ? n.toLocaleString("ko-KR") : "";
    });
  });

  // 결과 금액이 0에서 올라가는 효과
  function countUp(el, target) {
    const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { el.textContent = fmt(target); return; }
    const start = performance.now(), dur = 700;
    (function tick(t) {
      const p = Math.min(1, (t - start) / dur);
      el.textContent = fmt(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    })(start);
  }

  function show({ label, amount, badges = [], rows, note, next }) {
    out.innerHTML = `
      <p class="label">${label}</p>
      <p class="big"><span class="n">0</span><span class="won">원</span></p>
      <div class="badges">${badges.map(([cls, t]) => `<span class="badge ${cls}">${t}</span>`).join("")}</div>
      <dl class="rows">${rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>
      ${note ? `<p class="formula">${note}</p>` : ""}
      ${next ? `<button type="button" class="next" data-go="${next[0]}">${next[1]}<span>→</span></button>` : ""}`;
    out.hidden = false;
    countUp(out.querySelector(".n"), amount);
    const btn = out.querySelector(".next");
    if (btn) btn.addEventListener("click", () => {
      selectTab(btn.dataset.go);
      document.querySelector(".calc").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    out.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  document.getElementById("sev").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const r = QuitCalc.severance({
      startDate: f.startDate.value,
      lastDate: f.lastDate.value,
      wages3m: num(f.monthly.value) * 3,
      annualBonus: num(f.bonus.value),
      annualLeavePay: num(f.leave.value),
    });
    if (r.error) {
      out.innerHTML = `<p class="label">날짜를 확인해 주세요</p><p class="formula">${r.error}</p>`;
      out.hidden = false;
      return;
    }
    const years = (r.serviceDays / 365).toFixed(1);
    show({
      label: "예상 퇴직금 (세전)",
      amount: r.amount,
      badges: r.eligible
        ? [["ok", "퇴직금 대상"], ["", `근속 약 ${years}년`]]
        : [["warn", "1년 미만 근무"], ["", `${r.serviceDays}일 근무`]],
      rows: [
        ["재직 일수", `${fmt(r.serviceDays)}일`],
        ["3개월 임금 총액", won(r.wageTotal)],
        ["3개월 일수", `${r.periodDays}일`],
        ["1일 평균임금", won(r.avgDaily)],
      ],
      note: r.eligible
        ? "1일 평균임금 × 30일 × 재직일수 ÷ 365"
        : "1년 미만 근무는 법정 퇴직금 대상이 아닐 수 있어요. 위 금액은 참고용입니다.",
      next: ["ue", "실업급여도 계산해 보기"],
    });
  });

  document.getElementById("ue").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const r = QuitCalc.unemployment({
      monthlyWage: num(f.monthly.value),
      insuredYears: Number(f.years.value),
      age: Number(f.age.value),
      disabled: f.disabled.checked,
      dailyHours: Number(f.hours.value) || 8,
    });
    const badges = [["ok", `${r.days}일 동안`]];
    if (r.capped === "upper") badges.push(["", "상한액 적용"]);
    if (r.capped === "lower") badges.push(["", "하한액 적용"]);
    show({
      label: "예상 실업급여 총액",
      amount: r.total,
      badges,
      rows: [
        ["하루 지급액", won(r.daily)],
        ["한 달(30일) 기준", won(r.monthly)],
        ["받는 기간", `${r.days}일`],
        ["1일 평균임금", won(r.avgDaily)],
      ],
      note: "비자발적 퇴사이고 고용보험 180일 이상일 때 받을 수 있어요.",
      next: ["sev", "퇴직금도 계산해 보기"],
    });
  });
})();
