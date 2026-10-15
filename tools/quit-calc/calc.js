// 퇴직금·실업급여 계산 로직 (2026년 기준). 브라우저와 Node 양쪽에서 사용.
(function (root) {
  const RULES_2026 = {
    minWage: 10320,          // 2026 최저시급
    benefitUpper: 68100,     // 구직급여 1일 상한액 (2026.1.1~)
    benefitRate: 0.6,        // 평균임금의 60%
    lowerRate: 0.8,          // 하한: 최저임금의 80% x 소정근로시간
  };

  const DAY = 24 * 60 * 60 * 1000;

  function parseDate(s) {
    const [y, m, d] = s.split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  }

  function addMonths(t, n) {
    const d = new Date(t);
    const y = d.getUTCFullYear(), m = d.getUTCMonth() + n, day = d.getUTCDate();
    const last = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    return Date.UTC(y, m, Math.min(day, last));
  }

  // 퇴직금: 마지막 근무일 기준. 퇴직일 = 마지막 근무일 다음 날.
  function severance({ startDate, lastDate, wages3m, annualBonus = 0, annualLeavePay = 0 }) {
    const start = parseDate(startDate);
    const last = parseDate(lastDate);
    if (last < start) return { error: "퇴사일이 입사일보다 빠릅니다." };
    const retire = last + DAY;
    const serviceDays = Math.round((retire - start) / DAY);
    const periodDays = Math.round((retire - addMonths(retire, -3)) / DAY);
    const wageTotal = wages3m + (annualBonus * 3) / 12 + (annualLeavePay * 3) / 12;
    const avgDaily = wageTotal / periodDays;
    const amount = (avgDaily * 30 * serviceDays) / 365;
    return {
      eligible: serviceDays >= 365,
      serviceDays,
      periodDays,
      wageTotal,
      avgDaily,
      amount: Math.floor(amount),
    };
  }

  // 소정급여일수 (고용보험법 별표1)
  function benefitDays(insuredYears, age50OrDisabled) {
    const young = [120, 150, 180, 210, 240];
    const older = [120, 180, 210, 240, 270];
    const idx = insuredYears < 1 ? 0 : insuredYears < 3 ? 1 : insuredYears < 5 ? 2 : insuredYears < 10 ? 3 : 4;
    return (age50OrDisabled ? older : young)[idx];
  }

  // 실업급여(구직급여): 퇴직 전 3개월 평균임금 기준.
  function unemployment({ monthlyWage, insuredYears, age, disabled = false, dailyHours = 8, rules = RULES_2026 }) {
    const avgDaily = (monthlyWage * 3) / 91;
    const lower = rules.minWage * rules.lowerRate * Math.min(dailyHours, 8);
    const raw = avgDaily * rules.benefitRate;
    let daily = Math.min(Math.max(raw, lower), rules.benefitUpper);
    daily = Math.floor(daily);
    const days = benefitDays(insuredYears, age >= 50 || disabled);
    return {
      avgDaily,
      raw,
      lower: Math.floor(lower),
      upper: rules.benefitUpper,
      capped: raw > rules.benefitUpper ? "upper" : raw < lower ? "lower" : null,
      daily,
      days,
      total: daily * days,
      monthly: daily * 30,
    };
  }

  const api = { RULES_2026, severance, unemployment, benefitDays };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.QuitCalc = api;
})(this);
