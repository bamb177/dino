const canvas = document.getElementById("tpl");
const ctx = canvas.getContext("2d");

const sel = document.getElementById("species");
const opacity = document.getElementById("opacity");
const btnPrint = document.getElementById("btnPrint");

// A4 300dpi
const W = 2480, H = 3508;

// marker config (인식 안정 목적: 큼직하게)
const M = 220;          // marker size
const PAD = 140;        // page padding
const FRAME_PAD = 260;  // drawing frame margin from markers

function drawMarker(x, y, s){
  ctx.fillStyle = "#000"; ctx.fillRect(x, y, s, s);
  ctx.fillStyle = "#fff"; ctx.fillRect(x + s*0.18, y + s*0.18, s*0.64, s*0.64);
  ctx.fillStyle = "#000"; ctx.fillRect(x + s*0.34, y + s*0.34, s*0.32, s*0.32);
}

function drawFrame(){
  const fx0 = PAD + M + FRAME_PAD;
  const fy0 = PAD + FRAME_PAD;
  const fx1 = W - PAD - M - FRAME_PAD;
  const fy1 = H - PAD - FRAME_PAD;

  ctx.strokeStyle = "#000";
  ctx.lineWidth = 10;
  ctx.setLineDash([24, 18]);
  ctx.strokeRect(fx0, fy0, fx1-fx0, fy1-fy0);
  ctx.setLineDash([]);

  return { fx0, fy0, fx1, fy1, fw: fx1 - fx0, fh: fy1 - fy0 };
}

function setupPage(titleText){
  // white page
  ctx.fillStyle = "#fff";
  ctx.fillRect(0,0,W,H);

  // title
  ctx.fillStyle = "#111";
  ctx.font = "bold 68px sans-serif";
  ctx.fillText(titleText, PAD, 140);

  ctx.font = "38px sans-serif";
  ctx.fillStyle = "#222";
  ctx.fillText("Do not color the black corner markers.", PAD, 210);

  // corner markers
  drawMarker(PAD, PAD, M);
  drawMarker(W - PAD - M, PAD, M);
  drawMarker(W - PAD - M, H - PAD - M, M);
  drawMarker(PAD, H - PAD - M, M);

  // frame
  const frame = drawFrame();

  // footer
  ctx.fillStyle = "#222";
  ctx.font = "32px sans-serif";
  ctx.fillText("Scan: https://bamb177.github.io/dino/", PAD, H - 110);

  return frame;
}

function trexGuide(frame, alpha){
  // frame 내부에 티라노사우루스 “예시 윤곽선”을 연한 회색으로 그립니다.
  // 실사 도안이 아니라 “아이용 스케치”라 단순화된 실루엣입니다.

  const { fx0, fy0, fw, fh } = frame;

  // 좌표 변환 헬퍼: (0~1) -> frame pixel
  const X = (t) => fx0 + t * fw;
  const Y = (t) => fy0 + t * fh;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = "#777";      // 연한 회색
  ctx.lineWidth = 10;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // --- 몸통/등/꼬리 ---
  ctx.beginPath();
  ctx.moveTo(X(0.20), Y(0.68));                // 배쪽 시작
  ctx.bezierCurveTo(X(0.30), Y(0.58), X(0.44), Y(0.55), X(0.52), Y(0.56)); // 배->가슴
  ctx.bezierCurveTo(X(0.58), Y(0.57), X(0.64), Y(0.61), X(0.67), Y(0.63)); // 몸통
  ctx.bezierCurveTo(X(0.74), Y(0.68), X(0.80), Y(0.73), X(0.90), Y(0.76)); // 꼬리로
  ctx.bezierCurveTo(X(0.80), Y(0.78), X(0.70), Y(0.78), X(0.62), Y(0.77)); // 꼬리 하단
  ctx.bezierCurveTo(X(0.52), Y(0.76), X(0.40), Y(0.73), X(0.28), Y(0.72)); // 배쪽
  ctx.bezierCurveTo(X(0.24), Y(0.71), X(0.21), Y(0.70), X(0.20), Y(0.68));
  ctx.stroke();

  // --- 머리/턱 ---
  ctx.beginPath();
  ctx.moveTo(X(0.52), Y(0.56));                // 목 윗부분
  ctx.bezierCurveTo(X(0.50), Y(0.50), X(0.48), Y(0.46), X(0.46), Y(0.43)); // 목 -> 머리 뒤
  ctx.bezierCurveTo(X(0.42), Y(0.38), X(0.36), Y(0.37), X(0.33), Y(0.40)); // 머리 윗선
  ctx.bezierCurveTo(X(0.31), Y(0.42), X(0.30), Y(0.45), X(0.31), Y(0.47)); // 주둥이
  ctx.bezierCurveTo(X(0.33), Y(0.50), X(0.37), Y(0.51), X(0.42), Y(0.50)); // 윗턱 끝->뒤로
  ctx.bezierCurveTo(X(0.44), Y(0.52), X(0.47), Y(0.55), X(0.52), Y(0.56));
  ctx.stroke();

  // --- 아래턱 라인(입 벌리기 쉬운 가이드) ---
  ctx.beginPath();
  ctx.moveTo(X(0.31), Y(0.47));
  ctx.bezierCurveTo(X(0.34), Y(0.54), X(0.41), Y(0.56), X(0.47), Y(0.54));
  ctx.stroke();

  // --- 팔(작게) ---
  ctx.beginPath();
  ctx.moveTo(X(0.50), Y(0.60));
  ctx.bezierCurveTo(X(0.46), Y(0.62), X(0.44), Y(0.64), X(0.45), Y(0.66));
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(X(0.49), Y(0.62));
  ctx.bezierCurveTo(X(0.45), Y(0.65), X(0.43), Y(0.67), X(0.44), Y(0.69));
  ctx.stroke();

  // --- 다리 2개 ---
  // 앞다리(가까운 다리)
  ctx.beginPath();
  ctx.moveTo(X(0.56), Y(0.75));
  ctx.bezierCurveTo(X(0.56), Y(0.83), X(0.54), Y(0.88), X(0.52), Y(0.92));
  ctx.bezierCurveTo(X(0.55), Y(0.92), X(0.58), Y(0.92), X(0.60), Y(0.91)); // 발
  ctx.stroke();

  // 뒷다리(먼 다리)
  ctx.beginPath();
  ctx.moveTo(X(0.46), Y(0.74));
  ctx.bezierCurveTo(X(0.46), Y(0.81), X(0.44), Y(0.86), X(0.42), Y(0.90));
  ctx.bezierCurveTo(X(0.45), Y(0.90), X(0.48), Y(0.90), X(0.50), Y(0.89));
  ctx.stroke();

  // --- 눈(점) ---
  ctx.globalAlpha = Math.min(1, alpha + 0.15);
  ctx.fillStyle = "#666";
  ctx.beginPath();
  ctx.arc(X(0.36), Y(0.43), 12, 0, Math.PI*2);
  ctx.fill();

  ctx.restore();

  // 안내 문구(프레임 안, 아주 연하게)
  ctx.save();
  ctx.globalAlpha = Math.min(1, alpha + 0.10);
  ctx.fillStyle = "#666";
  ctx.font = "bold 40px sans-serif";
  ctx.fillText("T-REX (example outline)", fx0 + 20, frame.fy0 + 70);
  ctx.restore();
}

function draw(){
  const kind = sel.value;
  const a = Number(opacity.value) / 100;

  const frame = setupPage(
    kind === "trex" ? "DINO TEMPLATE - TYRANNOSAURUS (EXAMPLE)" : "DINO TEMPLATE - FREE DRAWING"
  );

  if(kind === "trex"){
    trexGuide(frame, a);
  }
}

sel.addEventListener("change", draw);
opacity.addEventListener("input", draw);
btnPrint.addEventListener("click", () => window.print());

draw();
