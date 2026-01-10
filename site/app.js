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

function log(msg){ logEl.textContent = msg; }
function setStatus(msg){ cvStatus.textContent = msg; }

function enableUI(ok){
  btnStart.disabled = !ok;
  btnCapture.disabled = !ok;
  // 다운로드는 결과 생성 후에만 true
  btnDownload.disabled = true;
}

enableUI(false);

// 전역 에러를 화면에 표시(초보자 디버깅용)
window.addEventListener("error", (e) => {
  meta.textContent = "JS 오류: " + (e?.message || e);
});
window.addEventListener("unhandledrejection", (e) => {
  meta.textContent = "Promise 오류: " + (e?.reason?.message || e?.reason || e);
});

// OpenCV 로딩 대기(정석)
function waitOpenCVReady(){
  return new Promise((resolve, reject) => {
    const t0 = Date.now();

    const tick = () => {
      // 1) cv 자체가 아직 없으면 조금 더 기다림
      if (!window.cv) {
        if (Date.now() - t0 > 15000) {
          reject(new Error("OpenCV(cv) 객체가 생성되지 않았습니다. opencv.js 로딩 실패 가능"));
          return;
        }
        setTimeout(tick, 50);
        return;
      }

      // 2) 이미 초기화 완료면 즉시 통과
      if (cv.Mat) {
        resolve();
        return;
      }

      // 3) 아직이면 onRuntimeInitialized에 resolve를 걸어둠
      // (여기서 '함수인지' 검사하지 않습니다. 속성 할당 방식이 정상입니다.)
      cv.onRuntimeInitialized = () => resolve();

      // 4) 혹시 콜백이 안 오는 환경 대비: 일정 시간 후 Mat 생기면 통과
      const fallback = () => {
        if (cv.Mat) { resolve(); return; }
        if (Date.now() - t0 > 15000) {
          reject(new Error("OpenCV 초기화 시간이 초과되었습니다. (onRuntimeInitialized 미호출)"));
          return;
        }
        setTimeout(fallback, 80);
      };
      fallback();
    };

    tick();
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
  }catch(e){
    meta.textContent = "카메라 시작 실패: " + (e?.message || e);
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

// 마커 4개 찾기(간단/안정 우선)
function findCornerMarkers(rgbaMat){
  const gray = new cv.Mat();
  cv.cvtColor(rgbaMat, gray, cv.COLOR_RGBA2GRAY);

  const bin = new cv.Mat();
  cv.adaptiveThreshold(gray, bin, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY_INV, 51, 7);

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
      if(area > 2500){
        const rect = cv.boundingRect(approx);
        const ratio = rect.width / rect.height;
        if(ratio > 0.75 && ratio < 1.33){
          cands.push({
            area,
            cx: rect.x + rect.width/2,
            cy: rect.y + rect.height/2
          });
        }
      }
    }
    approx.delete();
    cnt.delete();
  }

  gray.delete(); bin.delete(); contours.delete(); hierarchy.delete();

  if(cands.length < 4) return null;

  cands.sort((a,b)=> b.area - a.area);
  const top = cands.slice(0, 12);

  const W = rgbaMat.cols, H = rgbaMat.rows;
  const targets = [
    {name:"tl", x:0, y:0},
    {name:"tr", x:W, y:0},
    {name:"br", x:W, y:H},
    {name:"bl", x:0, y:H}
  ];

  const chosen = {};
  for(const t of targets){
    let best=null, bestD=1e18;
    for(const c of top){
      const dx = c.cx - t.x;
      const dy = c.cy - t.y;
      const d = dx*dx + dy*dy;
      if(d < bestD){ bestD=d; best=c; }
    }
    chosen[t.name]=best;
  }

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

  const OUT_W = 1200;
  const OUT_H = 1700;

  // template.js(큰 마커) 기준 축소 좌표
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
  const lab = new cv.Mat();
  cv.cvtColor(roiRGBA, lab, cv.COLOR_RGBA2Lab);

  const mv = new cv.MatVector();
  cv.split(lab, mv);
  const L = mv.get(0);
  const A = mv.get(1);
  const B = mv.get(2);

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
    const s = arr.slice().sort((x,y)=>x-y);
    return s[Math.floor(s.length/2)];
  }
  const L0 = paperL.length ? median(paperL) : 200;
  const A0 = paperA.length ? median(paperA) : 128;
  const B0 = paperB.length ? median(paperB) : 128;

  const mask = new cv.Mat(lab.rows, lab.cols, cv.CV_8UC1);
  const md = mask.data;

  for(let i=0;i<Ld.length;i++){
    const l = Ld[i], a = Ad[i], b = Bd[i];
    const dist = Math.hypot(a-A0, b-B0) + 0.25*Math.abs(l-L0);
    const ink = (dist > 18) || (l < 70);
    md[i] = ink ? 255 : 0;
  }

  const k = cv.getStructuringElement(cv.MORPH_ELLIPSE, new cv.Size(5,5));
  cv.morphologyEx(mask, mask, cv.MORPH_OPEN, k);
  cv.morphologyEx(mask, mask, cv.MORPH_CLOSE, k);

  k.delete();
  lab.delete();
  mv.delete();
  L.delete(); A.delete(); B.delete();

  return mask;
}

function biggestComponent(binMask){
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
    if(area > bestArea){ bestArea=area; best=i; }
  }

  const bestMat = new cv.Mat(labels.rows, labels.cols, labels.type(), new cv.Scalar(best));
  const comp = new cv.Mat();
  cv.compare(labels, bestMat, comp, cv.CMP_EQ);
  bestMat.delete();

  const x = stats.intAt(best, cv.CC_STAT_LEFT);
  const y = stats.intAt(best, cv.CC_STAT_TOP);
  const w = stats.intAt(best, cv.CC_STAT_WIDTH);
  const h = stats.intAt(best, cv.CC_STAT_HEIGHT);

  labels.delete(); stats.delete(); centroids.delete();
  return { comp, bbox:{x,y,w,h,area:bestArea} };
}

async function captureAndCutout(){
  try{
    btnCapture.disabled = true;
    btnDownload.disabled = true;
    lastPngDataUrl = null;
    meta.textContent = "";

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

    // 프레임 내부 ROI로 제한(마커/텍스트 영향 최소화)
    const OUT_W = warped.cols, OUT_H = warped.rows;
    const PAD = 70, M = 120, FRAME_PAD = 160;

    const x0 = Math.max(0, PAD + M + FRAME_PAD);
    const y0 = Math.max(0, PAD + FRAME_PAD);
    const x1 = Math.min(OUT_W, OUT_W - PAD - M - FRAME_PAD);
    const y1 = Math.min(OUT_H, OUT_H - PAD - FRAME_PAD);

    const roiRect = new cv.Rect(x0, y0, Math.max(1, x1-x0), Math.max(1, y1-y0));
    const roi = warped.roi(roiRect);

    meta.textContent = "처리중... (색칠/선 추출)";
    const ink = labInkMask(roi);

    meta.textContent = "처리중... (본체 선택)";
    const compInfo = biggestComponent(ink);
    if(!compInfo){
      meta.textContent = "그림 영역을 찾지 못했습니다. (조명/거리/각도 확인)";
      cap.delete(); warped.delete(); roi.delete(); ink.delete();
      btnCapture.disabled = false;
      return;
    }

    const { comp, bbox } = compInfo;

    const pad2 = 18;
    const cx = Math.max(0, bbox.x - pad2);
    const cy = Math.max(0, bbox.y - pad2);
    const cw = Math.min(comp.cols - cx, bbox.w + pad2*2);
    const ch = Math.min(comp.rows - cy, bbox.h + pad2*2);

    const compCrop = comp.roi(new cv.Rect(cx, cy, cw, ch));
    const roiCrop = roi.roi(new cv.Rect(cx, cy, cw, ch)); // RGBA

    const inv = new cv.Mat();
    cv.bitwise_not(compCrop, inv);

    const mv = new cv.MatVector();
    cv.split(roiCrop, mv);
    const c0 = mv.get(0), c1 = mv.get(1), c2 = mv.get(2);
    c0.setTo(new cv.Scalar(0), inv);
    c1.setTo(new cv.Scalar(0), inv);
    c2.setTo(new cv.Scalar(0), inv);

    const alpha = compCrop.clone();
    const mv2 = new cv.MatVector();
    mv2.push_back(c0); mv2.push_back(c1); mv2.push_back(c2); mv2.push_back(alpha);

    const out = new cv.Mat();
    cv.merge(mv2, out);

    outCanvas.width = out.cols;
    outCanvas.height = out.rows;
    cv.imshow(outCanvas, out);

    lastPngDataUrl = outCanvas.toDataURL("image/png");
    outImg.src = lastPngDataUrl;

    meta.textContent = "완료. 결과 PNG 생성됨";
    log(`cap:${cap.cols}x${cap.rows} / warped:${warped.cols}x${warped.rows} / out:${out.cols}x${out.rows}`);

    // cleanup
    cap.delete(); warped.delete(); roi.delete(); ink.delete();
    comp.delete(); compCrop.delete(); roiCrop.delete();
    inv.delete();
    mv.delete(); mv2.delete();
    c0.delete(); c1.delete(); c2.delete(); alpha.delete();
    out.delete();

    btnDownload.disabled = false;
    btnCapture.disabled = false;

  }catch(e){
    meta.textContent = "오류 발생: " + (e?.message || e);
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
  try{
    setStatus("OpenCV 준비 대기...");
    await waitOpenCVReady();
    setStatus("OpenCV 준비 완료");
    enableUI(true);
    meta.textContent = "준비됨. 카메라 시작을 누르세요.";
  }catch(e){
    setStatus("OpenCV 로딩 실패");
    meta.textContent = (e?.message || e);
  }
})();
