// node tools/quit-calc/calc.test.js
const assert = require("assert");
const { severance, unemployment, benefitDays } = require("./calc.js");

// 2023-01-01 입사, 2025-12-31 마지막 근무, 월 300만원
const s = severance({ startDate: "2023-01-01", lastDate: "2025-12-31", wages3m: 9_000_000 });
assert.strictEqual(s.serviceDays, 1096);
assert.strictEqual(s.periodDays, 92); // 2025-10-01 ~ 2025-12-31
assert.strictEqual(s.amount, Math.floor((9_000_000 / 92) * 30 * 1096 / 365));
assert.ok(s.eligible);

assert.ok(!severance({ startDate: "2025-06-01", lastDate: "2026-03-31", wages3m: 6e6 }).eligible);
assert.ok(severance({ startDate: "2026-02-01", lastDate: "2026-01-01", wages3m: 1 }).error);

// 월 300만원 → 60%가 상·하한 사이
const u = unemployment({ monthlyWage: 3_000_000, insuredYears: 1, age: 42 });
assert.strictEqual(u.daily, 66048); // 9e6/91*0.6 = 59,340 → 하한 66,048
assert.strictEqual(u.days, 150);

// 고소득 → 상한
const hi = unemployment({ monthlyWage: 6_000_000, insuredYears: 10, age: 55 });
assert.strictEqual(hi.daily, 68100);
assert.strictEqual(hi.days, 270);
assert.strictEqual(hi.capped, "upper");

// 단시간 근로자 하한은 근로시간에 비례
const pt = unemployment({ monthlyWage: 1_000_000, insuredYears: 0, age: 30, dailyHours: 4 });
assert.strictEqual(pt.daily, Math.floor(10320 * 0.8 * 4));

assert.strictEqual(benefitDays(4, false), 180);
assert.strictEqual(benefitDays(4, true), 210);
console.log("ok");
