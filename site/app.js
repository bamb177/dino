const video = document.getElementById("video");
const outCanvas = document.getElementById("outCanvas");
const outImg = document.getElementById("outImg");
const meta = document.getElementById("meta");
const logEl = document.getElementById("log");
const cvStatus = document.getElementById("cvStatus");

const btnStart = document.getElementById("btnStart");
const btnCapture = document.getElementById("btnCapture");
const btnDownload = document.getElementById("btnDownload");

let lastPngDataUrl = null;

function log(msg){
  logEl.textContent = msg;
}

function setStatus(msg){
  cvStatus.textContent = msg;
}

function enableUI(enabled){
  btnStart.disabled = !enabled;
  btnCapture.disabled = !enabled;
  btnDownload.disabled = !enabled;
}

enableUI(false);

// OpenCV runtime init (가장 안정적인 방식)
function waitOpenCV(){
  return new Promise((resolve) => {
    const check = () => {
      if (window.cv && cv.Mat && typeof cv.onRuntimeInitialized === "function") {
        cv.onRuntimeInitialized = () => resolve();
      } else if (window.cv && cv.Mat && cv.getBuildInformation) {
        // 일부 환경에서는 onRuntimeInitialized 없이도 바로 준비됨
        resolve();
      } else {
        setTimeout(check, 50);
      }
    };
    check();
  });
}

async function startCamera(){
  try{
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    video.srcObject = stream;
    meta.textContent = "카메라 시작됨. 템플릿 모서리 마커 4개가 모두 보이게 맞춘 뒤 캡처하세요.";
  } catch (e){
    meta.textContent = "카메라 시작 실패: " + e;
  }
}

function captureFrameToCanvas(maxW = 960){
  if(!video.videoWidth) return null;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  const scale = Math.min(1, maxW / vw);

  const c = document.createElement("canvas");
  c.width = Math.round(vw * scale);
  c.height = Math.round(vh * scale);
  c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
  return c;
}

function orderByCorners(points, W, H){
  // points: [{x,y},...]
  const tl = points.reduce((a,p)=> (p.x+p.y < a.x+a.y ? p : a));
  const br = points.reduce((a,p)=> (p.x+p.y > a.x+a.y ? p : a));
  const tr = points.reduce((a,p)=> (p.x - p.y > a.x - a.y ? p : a));
  const bl = points.reduce((a,p)=> (p.x - p.y < a.x - a.y ? p : a));
  return {tl,tr,br,bl};
}

function findCornerMarkers(rgbaMat){
  // 1) gray
  const gray = new cv.Mat();
  cv.cvtColor(rgbaMat, gray, cv.COLOR_RGBA2GRAY);

  // 2) adaptive threshold (조명 변화 대응)
  const bin = new cv.Mat();
  cv.adaptiveThreshold(gray, bin, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY_INV, 51, 7);

  // 3) contours
  const contours = new cv.MatVector();
  const hierarchy = new cv.Mat();
  cv.findContours(bin, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

  const cands = [];
  for(let i=0;i<contours.size();i++){
    const cnt = contours.get(i);
    const peri = cv.arcLength(cnt, true);
    const approx = new cv.Mat();
    cv.approxPolyDP(cnt, approx, 0.02 * peri, true);

    if(approx.rows === 4){
      const area = cv.contourArea(approx);
      if(area > 2500){ // 해상도 낮춰서 촬영하므로 기준 낮춤
        const rect = cv.boundingRect(approx);
        const ratio = rect.width / rect.height;
        if(ratio > 0.75 && ratio < 1.33){
          const cx = rect.x + rect.width/2;
          const cy = rect.y + rect.height/2;
          cands.push({area, cx, cy});
        }
      }
    }

    approx.delete();
    cnt.delete();
  }

  gray.delete(); bin.delete(); contours.delete(); hierarchy.delete();

  if(cands.length < 4) return null;

  // 큰 것 위주
  cands.sort((a,b)=> b.area - a.area);
  const top = cands.slice(0, 12);

  const W = rgbaMat.cols, H = rgbaMat.rows;
  const targetCorners = [
    {name:"tl", x:0, y:0},
    {name:"tr", x:W, y:0},
    {name:"br", x:W, y:H},
    {name:"bl", x:0, y:H}
  ];

  const chosen = {};
  for(const tc of targetCorners){
    let best = null, bestD = 1e18;
    for(const cand of top){
      const dx = cand.cx - tc.x;
      const dy = cand.cy - tc.y;
      const d = dx*dx + dy*dy;
      if(d < bestD){ bestD = d; best = cand; }
    }
    chosen[tc.name] = best;
  }

  // 중복 선택 방지
  const uniq = new Set([chosen.tl, chosen.tr, chosen.br, chosen.bl]);
  if(uniq.size < 4) return null;

  return [
    chosen.tl.cx, chosen.tl.cy,
    chosen.tr.cx, chosen.tr.cy,
    chosen.br.cx, chosen.br.cy,
    chosen.bl.cx, chosen.bl.cy
  ];
}

function warpToA4(rgbaMat){
  const srcPts = findCornerMarkers(rgbaMat);
  if(!srcPts) return null;

  // 처리용 축소 A4 좌표계 (속도 목적)
  const OUT_W = 1200;
  const OUT_H = 1700;

  // template.js(PAD=140, M=220)를 축소 좌표계에 맞춘 값
  // 대략 비율로 맞춰서 마커 "센터" 위치로 워프함
  const PAD = 70;
  const M = 120;

  const dstPts = [
    PAD + M/2, PAD + M/2,
    OUT_W - PAD - M/2, PAD + M/2,
    OUT_W - PAD - M/2, OUT_H - PAD - M/2,
    PAD + M/2, OUT_H - PAD - M/2
  ];

  const src = cv.matFromArray(4,1,cv.CV_32FC2, srcPts);
  const dst = cv.matFromArray(4,1,cv.CV_32FC2, dstPts);
  const Hm = cv.getPerspectiveTransform(src, dst);

  const warped = new cv.Mat();
  cv.warpPerspective(rgbaMat, warped, Hm, new cv.Size(OUT_W, OUT_H), cv.INTER_LINEAR, cv.BORDER_REPLICATE);

  src.delete(); dst.delete(); Hm.delete();
  return warped;
}

function labInkMask(roiRGBA){
  // LAB 기반 종이색 대비(그림자 대응)
  const lab = new cv.Mat();
  cv.cvtColor(roiRGBA, lab, cv.COLOR_RGBA2Lab);

  const mv = new cv.MatVector();
  cv.split(lab, mv);
  const L = mv.get(0);
  const A = mv.get(1);
  const B = mv.get(2);

  // 종이 후보: 밝고 채도 낮은 픽셀 샘플링(성능 목적, 전체를 순회하긴 하지만 ROI가 작음)
  const Ld = L.data, Ad = A.data, Bd = B.data;
  const paperL = [], paperA = [], paperB = [];
  for(let i=0;i<Ld.length;i++){
    const l = Ld[i], a = Ad[i], b = Bd[i];
    const chroma = Math.hypot(a-128, b-128);
    if(chroma < 12 && l > 155){
      paperL.push(l); paperA.push(a); paperB.push(b);
    }
  }

  function median(arr){
    if(arr.length === 0) return 0;
    const a = arr.slice().sort((x,y)=>x-y);
    return a[Math.floor(a.length/2)];
  }

  const L0 = paperL.length ? median(paperL) : 200;
  const A0 = paperA.length ? median(paperA) : 128;
  const B0 = paperB.length ? median(paperB) : 128;

  const mask = new cv.Mat(lab.rows, lab.cols, cv.CV_8UC1);
  const md = mask.data;

  for(let i=0;i<Ld.length;i++){
    const l = Ld[i], a = Ad[i], b = Bd[i];
    const dist = Math.hypot(a-A0, b-B0) + 0.25*Math.abs(l-L0);
    const ink = (dist > 18) || (l < 70); // 색칠 + 검정선
    md[i] = ink ? 255 : 0;
  }

  // morph
  const k = cv.getStructuringElement(cv.MORPH_ELLIPSE, new cv.Size(5,5));
  cv.morphologyEx(mask, mask, cv.MORPH_OPEN, k);
  cv.morphologyEx(mask, mask, cv.MORPH_CLOSE, k);

  // cleanup
  k.delete();
  lab.delete();
  mv.delete();
  L.delete(); A.delete(); B.delete();

  return mask;
}

function biggestComponent(binMask){
  // binMask: CV_8UC1 0/255
  const labels = new cv.Mat();
  const stats = new cv.Mat();
  const centroids = new cv.Mat();

  const n = cv.connectedComponentsWithStats(binMask, labels, stats, centroids, 8, cv.CV_32S);
  if(n <= 1){
    labels.delete(); stats.delete(); centroids.delete();
    return null;
  }

  let best = 1;
  let bestArea = stats.intAt(1, cv.CC_STAT_AREA);
  for(let i=2;i<n;i++){
    const area = stats.intAt(i, cv.CC_STAT_AREA);
    if(area > bestArea){
      bestArea = area;
      best = i;
    }
  }

  // comp mask: labels == best  (for문 금지: compare 사용)
  const bestMat = new cv.Mat(labels.rows, labels.cols, labels.type(), new cv.Scalar(best));
  const comp = new cv.Mat();
  cv.compare(labels, bestMat, comp, cv.CMP_EQ);
  bestMat.delete();

  const x = stats.intAt(best, cv.CC_STAT_LEFT);
  const y = stats.intAt(best, cv.CC_STAT_TOP);
  const w = stats.intAt(best, cv.CC_STAT_WIDTH);
  const h = stats.intAt(best, cv.CC_STAT_HEIGHT);

  labels.delete(); stats.delete(); centroids.delete();
  return { comp, bbox: {x,y,w,h, area: bestArea} };
}

async function captureAndCutout(){
  try{
    meta.textContent = "";
    log("");
    btnCapture.disabled = true;
    btnDownload.disabled = true;
    lastPngDataUrl = null;

    const frameCanvas = captureFrameToCanvas(960);
    if(!frameCanvas){
      meta.textContent = "카메라가 준비되지 않았습니다.";
      btnCapture.disabled = false;
      return;
    }

    meta.textContent = "처리중... (마커 인식/투시보정)";
    const cap = cv.imread(frameCanvas); // RGBA

    const warped = warpToA4(cap);
    if(!warped){
      meta.textContent = "마커 4개 인식 실패. (모서리 마커 4개가 모두 화면에 보이게 촬영)";
      cap.delete();
      btnCapture.disabled = false;
      return;
    }

    // 템플릿 프레임 내부 ROI로 제한(텍스트/마커 제외)
    const OUT_W = warped.cols, OUT_H = warped.rows;

    // template.js 값에 대응되는 “프레임 내부” 영역(대략)
    const PAD = 70, M = 120, FRAME_PAD = 160;

    const x0 = Math.max(0, PAD + M + FRAME_PAD);
    const y0 = Math.max(0, PAD + FRAME_PAD);
    const x1 = Math.min(OUT_W, OUT_W - PAD - M - FRAME_PAD);
    const y1 = Math.min(OUT_H, OUT_H - PAD - FRAME_PAD);

    const roiRect = new cv.Rect(x0, y0, Math.max(1, x1-x0), Math.max(1, y1-y0));
    const roi = warped.roi(roiRect);

    meta.textContent = "처리중... (색칠/선 추출)";
    let ink = labInkMask(roi);

    // 프레임 라인/잡티 제거용: 가장자리 약간 제거
    const border = 6;
    ink.rowRange(0, border).setTo(new cv.Scalar(0));
    ink.rowRange(ink.rows-border, ink.rows).setTo(new cv.Scalar(0));
    ink.colRange(0, border).setTo(new cv.Scalar(0));
    ink.colRange(ink.cols-border, ink.cols).setTo(new cv.Scalar(0));

    meta.textContent = "처리중... (본체 선택)";
    const compInfo = biggestComponent(ink);
    if(!compInfo){
      meta.textContent = "그림(잉크) 영역을 찾지 못했습니다. (조명/거리/각도 확인)";
      cap.delete(); warped.delete(); roi.delete(); ink.delete();
      btnCapture.disabled = false;
      return;
    }

    let {comp, bbox} = compInfo;

    // 약간 확장
    const pad = 18;
    const cx = Math.max(0, bbox.x - pad);
    const cy = Math.max(0, bbox.y - pad);
    const cw = Math.min(comp.cols - cx, bbox.w + pad*2);
    const ch = Math.min(comp.rows - cy, bbox.h + pad*2);

    const compCrop = comp.roi(new cv.Rect(cx, cy, cw, ch));
    const roiCrop = roi.roi(new cv.Rect(cx, cy, cw, ch)); // RGBA

    // compCrop을 alpha로 사용, mask 밖 RGB는 0으로 정리
    const inv = new cv.Mat();
    cv.bitwise_not(compCrop, inv);

    const mv = new cv.MatVector();
    cv.split(roiCrop, mv);
    const c0 = mv.get(0), c1 = mv.get(1), c2 = mv.get(2); // RGB
    // mask 밖은 0으로
    c0.setTo(new cv.Scalar(0), inv);
    c1.setTo(new cv.Scalar(0), inv);
    c2.setTo(new cv.Scalar(0), inv);

    const alpha = compCrop.clone();

    const mv2 = new cv.MatVector();
    mv2.push_back(c0);
    mv2.push_back(c1);
    mv2.push_back(c2);
    mv2.push_back(alpha);

    const out = new cv.Mat();
    cv.merge(mv2, out);

    // 표시
    outCanvas.width = out.cols;
    outCanvas.height = out.rows;
    cv.imshow(outCanvas, out);

    lastPngDataUrl = outCanvas.toDataURL("image/png");
    outImg.src = lastPngDataUrl;

    meta.textContent = "완료. 결과 PNG 생성됨";
    log(`워프:${warped.cols}x${warped.rows} / ROI:${roi.cols}x${roi.rows} / 컷아웃:${out.cols}x${out.rows}`);

    // cleanup
    cap.delete(); warped.delete(); roi.delete();
    ink.delete(); comp.delete();
    compCrop.delete(); roiCrop.delete();
    inv.delete();
    mv.delete(); mv2.delete();
    c0.delete(); c1.delete(); c2.delete(); alpha.delete();
    out.delete();

    btnDownload.disabled = false;
    btnCapture.disabled = false;

  }catch(e){
    meta.textContent = "오류 발생: " + e;
    log("콘솔(F12)에서 에러 로그를 확인하세요.");
    btnCapture.disabled = false;
  }
}

function downloadPng(){
  if(!lastPngDataUrl){
    meta.textContent = "먼저 캡처해서 PNG를 생성하세요.";
    return;
  }
  const a = document.createElement("a");
  a.href = lastPngDataUrl;
  a.download = "dino_cutout.png";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

btnStart.addEventListener("click", startCamera);
btnCapture.addEventListener("click", captureAndCutout);
btnDownload.addEventListener("click", downloadPng);

// Init
(async function init(){
  setStatus("OpenCV 로딩 대기...");
  await waitOpenCV();
  setStatus("OpenCV 준비 완료. 카메라 시작을 누르세요.");
  enableUI(true);
  // 다운로드는 결과 생성 후 활성화
  btnDownload.disabled = true;
})();
