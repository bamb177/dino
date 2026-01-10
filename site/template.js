const canvas = document.getElementById("tpl");
const ctx = canvas.getContext("2d");
const sel = document.getElementById("species");
const btnPrint = document.getElementById("btnPrint");

// A4 300dpi: 2480 x 3508
const W = 2480, H = 3508;

// marker config
const M = 220;          // marker size
const PAD = 140;        // page padding
const FRAME_PAD = 260;  // drawing frame margin from markers

function drawMarker(x, y, s){
  // high-contrast nested squares for contour-based detection
  ctx.fillStyle = "#000"; ctx.fillRect(x, y, s, s);
  ctx.fillStyle = "#fff"; ctx.fillRect(x + s*0.18, y + s*0.18, s*0.64, s*0.64);
  ctx.fillStyle = "#000"; ctx.fillRect(x + s*0.34, y + s*0.34, s*0.32, s*0.32);
}

function draw(){
  const species = sel.value;

  // background
  ctx.fillStyle = "#fff";
  ctx.fillRect(0,0,W,H);

  // title
  ctx.fillStyle = "#222";
  ctx.font = "bold 64px sans-serif";
  const title = species === "ptera" ? "PTERANODON" : species === "trex" ? "TYRANNOSAURUS" : "FREE DRAWING";
  ctx.fillText("DINO TEMPLATE - " + title, PAD, 140);

  ctx.font = "38px sans-serif";
  ctx.fillText("Do not color the black corner markers.", PAD, 210);

  // corner markers (TL, TR, BR, BL)
  drawMarker(PAD, PAD, M);
  drawMarker(W - PAD - M, PAD, M);
  drawMarker(W - PAD - M, H - PAD - M, M);
  drawMarker(PAD, H - PAD - M, M);

  // drawing frame (inside area)
  const fx0 = PAD + M + FRAME_PAD;
  const fy0 = PAD + FRAME_PAD;
  const fx1 = W - PAD - M - FRAME_PAD;
  const fy1 = H - PAD - FRAME_PAD;

  ctx.strokeStyle = "#000";
  ctx.lineWidth = 10;
  ctx.setLineDash([24, 18]);
  ctx.strokeRect(fx0, fy0, fx1-fx0, fy1-fy0);
  ctx.setLineDash([]);

  // small footer
  ctx.fillStyle = "#333";
  ctx.font = "32px sans-serif";
  ctx.fillText("Scan URL: https://bamb177.github.io/dino/", PAD, H - 120);
  ctx.fillText("Template ID: " + species, PAD, H - 75);
}

sel.addEventListener("change", draw);
btnPrint.addEventListener("click", () => window.print());

draw();
