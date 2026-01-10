const canvas = document.getElementById("tpl");
const ctx = canvas.getContext("2d");
const btnPrint = document.getElementById("btnPrint");

// A4 300dpi: 2480 x 3508
const W = 2480, H = 3508;

// marker config (큰 마커일수록 인식 안정)
const M = 220;
const PAD = 140;
const FRAME_PAD = 260;

function drawMarker(x, y, s){
  // nested squares for robust contour detection
  ctx.fillStyle = "#000"; ctx.fillRect(x, y, s, s);
  ctx.fillStyle = "#fff"; ctx.fillRect(x + s*0.18, y + s*0.18, s*0.64, s*0.64);
  ctx.fillStyle = "#000"; ctx.fillRect(x + s*0.34, y + s*0.34, s*0.32, s*0.32);
}

function draw(){
  ctx.fillStyle = "#fff";
  ctx.fillRect(0,0,W,H);

  // Title
  ctx.fillStyle = "#111";
  ctx.font = "bold 68px sans-serif";
  ctx.fillText("DINO DRAWING TEMPLATE", PAD, 140);

  ctx.font = "38px sans-serif";
  ctx.fillText("Do not color the black corner markers.", PAD, 210);

  // corner markers
  drawMarker(PAD, PAD, M);
  drawMarker(W - PAD - M, PAD, M);
  drawMarker(W - PAD - M, H - PAD - M, M);
  drawMarker(PAD, H - PAD - M, M);

  // drawing frame
  const fx0 = PAD + M + FRAME_PAD;
  const fy0 = PAD + FRAME_PAD;
  const fx1 = W - PAD - M - FRAME_PAD;
  const fy1 = H - PAD - FRAME_PAD;

  ctx.strokeStyle = "#000";
  ctx.lineWidth = 10;
  ctx.setLineDash([24, 18]);
  ctx.strokeRect(fx0, fy0, fx1-fx0, fy1-fy0);
  ctx.setLineDash([]);

  // footer
  ctx.fillStyle = "#222";
  ctx.font = "32px sans-serif";
  ctx.fillText("Scan: https://bamb177.github.io/dino/", PAD, H - 110);
}

btnPrint.addEventListener("click", () => window.print());
draw();
