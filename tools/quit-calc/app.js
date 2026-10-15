(function () {
  const won = (n) => Math.round(n).toLocaleString("ko-KR") + "원";
  const num = (v) => Number(String(v || "").replace(/[^\d]/g, "")) || 0;

  // 탭 전환
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-selected", b === btn);
      });
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === btn.dataset.tab));
    });
  });

  // 금액 입력칸 천 단위 쉼표
  document.querySelectorAll('input[inputmode="numeric"]').forEach((el) => {
    el.addEventListener("input", () => {
      const n = num(el.value);
      el.value = n ? n.toLocaleString("ko-KR") : "";
    });
  });

  function show(el, html) {
    el.innerHTML = html;
    el.hidden = false;
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  document.getElementById("sev-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const r = QuitCalc.severance({
      startDate: f.startDate.value,
      lastDate: f.lastDate.value,
      wages3m: num(f.monthly.value) * 3,
      annualBonus: num(f.bonus.value),
      annualLeavePay: num(f.leave.value),
    });
    const out = document.getElementById("sev-result");
    if (r.error) return show(out, `<p class="warn">${r.error}</p>`);
    show(out, `
      <p class="label">예상 퇴직금 (세전)</p>
      <p class="big">${won(r.amount)}</p>
      ${r.eligible ? "" : `<p class="warn">재직 기간이 1년 미만(${r.serviceDays}일)이라 법정 퇴직금 대상이 아닐 수 있습니다.</p>`}
      <table>
        <tr><th>재직 일수</th><td>${r.serviceDays.toLocaleString()}일</td></tr>
        <tr><th>3개월 임금 총액</th><td>${won(r.wageTotal)}</td></tr>
        <tr><th>3개월 일수</th><td>${r.periodDays}일</td></tr>
        <tr><th>1일 평균임금</th><td>${won(r.avgDaily)}</td></tr>
      </table>
      <p class="formula">1일 평균임금 × 30일 × 재직일수 ÷ 365</p>`);
  });

  document.getElementById("ue-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const r = QuitCalc.unemployment({
      monthlyWage: num(f.monthly.value),
      insuredYears: Number(f.years.value),
      age: Number(f.age.value),
      disabled: f.disabled.checked,
      dailyHours: Number(f.hours.value) || 8,
    });
    const note = r.capped === "upper" ? "상한액이 적용되었습니다." : r.capped === "lower" ? "하한액이 적용되었습니다." : "";
    show(document.getElementById("ue-result"), `
      <p class="label">예상 실업급여 총액</p>
      <p class="big">${won(r.total)}</p>
      <table>
        <tr><th>하루 지급액</th><td>${won(r.daily)}</td></tr>
        <tr><th>받는 기간</th><td>${r.days}일</td></tr>
        <tr><th>한 달(30일) 기준</th><td>${won(r.monthly)}</td></tr>
        <tr><th>1일 평균임금</th><td>${won(r.avgDaily)}</td></tr>
      </table>
      ${note ? `<p class="formula">${note}</p>` : ""}`);
  });
})();
