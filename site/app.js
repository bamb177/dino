const video = document.getElementById("video");
const outCanvas = document.getElementById("outCanvas");
const outCtx = outCanvas.getContext("2d");
const outImg = document.getElementById("outImg");
const meta = document.getElementById("meta");
const cvStatus = document.getElementById("cvStatus");

const btnStart = document.getElementById("btnStart");
const btnCapture = document.getElementById("btnCapture");
const btnDownload = document.getElementById("btnDownload");

let lastPngDataUrl = null;

function setStatus(s){ cvStatus.textContent = s; }

window.onOpenCvReady = function(){
  setStatus("OpenCV 준비 완료. 카메라 시작을 눌러주세요.");
};

// app.js가 로드될 때 이미 OpenCV가 초기화된 경우 즉시 반영
if (window.__opencv_ready) {
  window.onOpenCvReady();
} else {
  setStatus("OpenCV 로딩 중...");
}



function waitForCVReady(){
  return new Promise((resolve) => {
    const timer = setInterval(() => {
      if (window.cv && cv.Mat) {
        clearInterval(timer);
        resolve();
      }
    }, 50);
  });
}

async function startCamera(){
  try{
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    video.srcObject = stream;
    meta.textContent = "카메라 시작됨. 도안을 중앙에 크게 맞추고 캡처하세요.";
  } catch (e){
    meta.textContent = "카메라 시작 실패: " + e;
  }
}

function drawVideoToCanvas(canvas){
  const ctx = canvas.getContext("2d");
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if(!vw || !vh) return false;

  // 성능을 위해 최대 1280으로 다운스케일
  const maxW = 1280;
  const scale = Math.min(1, maxW / vw);
  canvas.width = Math.round(vw * scale);
  canvas.height = Math.round(vh * scale);

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return true;
}

function orderCorners(pts){
  // pts: Array of 4 points {x,y}
  const s = pts.map(p => p.x + p.y);
  const d = pts.map(p => p.x - p.y);
  const tl = pts[s.indexOf(Math.min(...s))];
  const br = pts[s.indexOf(Math.max(...s))];
  const tr = pts[d.indexOf(Math.min(...d))];
  const bl = pts[d.indexOf(Math.max(...d))];
  return [tl, tr, br, bl];
}

function lerp(a,b,t){ return a*(1-t)+b*t; }

function labInkMask(roiRGBA){
  // roiRGBA: cv.Mat (CV_8UC4)
  const lab = new cv.Mat();
  cv.cvtColor(roiRGBA, lab, cv.COLOR_RGBA2Lab);

  const channels = new cv.MatVector();
  cv.split(lab, channels);
  const L = channels.get(0);
  const A = channels.get(1);
  const B = channels.get(2);

  const h = lab.rows, w = lab.cols;
  const Ld = L.data, Ad = A.data, Bd = B.data;

  // 종이 픽셀 후보: 채도 낮고 밝은 영역
  let paperL = [];
  let paperA = [];
  let paperB = [];
  for(let i=0;i<Ld.length;i++){
    const l = Ld[i], a = Ad[i], b = Bd[i];
    const chroma = Math.hypot(a-128, b-128);
    if(chroma < 10 && l > 160){
      paperL.push(l); paperA.push(a); paperB.push(b);
    }
  }
  if(paperL.length < 300){
    paperL = []; paperA = []; paperB = [];
    for(let i=0;i<Ld.length;i++){
      const l = Ld[i], a = Ad[i], b = Bd[i];
      const chroma = Math.hypot(a-128, b-128);
      if(chroma < 14 && l > 140){
        paperL.push(l); paperA.push(a); paperB.push(b);
      }
    }
  }

  function median(arr){
    if(arr.length === 0) return 0;
    const a = arr.slice().sort((x,y)=>x-y);
    return a[Math.floor(a.length/2)];
  }

  const L0 = paperL.length ? median(paperL) : median(Array.from(Ld));
  const A0 = paperA.length ? median(paperA) : median(Array.from(Ad));
  const B0 = paperB.length ? median(paperB) : median(Array.from(Bd));

  // ink = 종이색과의 거리 + 어두운 선
  const mask = new cv.Mat(h, w, cv.CV_8UC1);
  const md = mask.data;
  for(let i=0;i<Ld.length;i++){
    const l = Ld[i], a = Ad[i], b = Bd[i];
    const dist = Math.hypot(a-A0, b-B0) + 0.25*Math.abs(l-L0);
    const ink = (dist > 18) || (l < 75);
    md[i] = ink ? 255 : 0;
  }

  // morphology
  const k = cv.getStructuringElement(cv.MORPH_ELLIPSE, new cv.Size(5,5));
  cv.morphologyEx(mask, mask, cv.MORPH_OPEN, k);
  cv.morphologyEx(mask, mask, cv.MORPH_CLOSE, k);

  // cleanup
  lab.delete(); channels.delete();
  L.delete(); A.delete(); B.delete();
  k.delete();

  return mask;
}

function biggestComponent(binMask){
  // binMask: CV_8UC1 (0/255)
  const contours = new cv.MatVector();
  const hierarchy = new cv.Mat();
  cv.findContours(binMask, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

  if(contours.size() === 0){
    contours.delete(); hierarchy.delete();
    return null;
  }

  let bestIdx = 0;
  let bestArea = 0;
  for(let i=0;i<contours.size();i++){
    const cnt = contours.get(i);
    const area = cv.contourArea(cnt);
    if(area > bestArea){
      bestArea = area;
      bestIdx = i;
    }
    cnt.delete();
  }

  // best contour 다시 가져오기
  const best = contours.get(bestIdx);
  const rect = cv.boundingRect(best);

  // mask 생성
  const comp = new cv.Mat(binMask.rows, binMask.cols, cv.CV_8UC1);
  comp.setTo(new cv.Scalar(0));
  const color = new cv.Scalar(255);
  cv.drawContours(comp, contours, bestIdx, color, -1); // fill

  best.delete();
  contours.delete(); hierarchy.delete();

  return { comp, bbox: { x: rect.x, y: rect.y, w: rect.width, h: rect.height, area: bestArea } };
}


  // stats: [label, x, y, w, h, area]
  let best = 1;
  let bestArea = stats.intAt(1, cv.CC_STAT_AREA);
  for(let i=2;i<n;i++){
    const area = stats.intAt(i, cv.CC_STAT_AREA);
    if(area > bestArea){ bestArea = area; best = i; }
  }

  // create mask for best label
  const comp = new cv.Mat(binMask.rows, binMask.cols, cv.CV_8UC1);
  for(let y=0;y<labels.rows;y++){
    for(let x=0;x<labels.cols;x++){
      comp.ucharPtr(y,x)[0] = (labels.intAt(y,x) === best) ? 255 : 0;
    }
  }

  const x = stats.intAt(best, cv.CC_STAT_LEFT);
  const y = stats.intAt(best, cv.CC_STAT_TOP);
  const w = stats.intAt(best, cv.CC_STAT_WIDTH);
  const h = stats.intAt(best, cv.CC_STAT_HEIGHT);

  labels.delete(); stats.delete(); centroids.delete();
  return { comp, bbox: {x,y,w,h, area: bestArea} };
}

async function captureAndCutout(){
  try{
    if(!video.videoWidth){
      meta.textContent = "카메라가 준비되지 않았습니다.";
      return;
        }catch(e){
        meta.textContent = "에러: " + (e && e.message ? e.message : e);
      }
    }
    }

    meta.textContent = "처리 중... (캡처)";
    // 아래 기존 코드 계속…

    const capCanvas = document.createElement("canvas");
    if(!drawVideoToCanvas(capCanvas)){
      meta.textContent = "캡처 실패";
      return;
    }
  
    // 캡처 이미지를 OpenCV로
    const cap = cv.imread(capCanvas); // RGBA
    const H = cap.rows, W = cap.cols;
  
  // (QR 대신) 4코너 마커로 A4 좌표계로 워프
  const warped = warpToA4(cap);
  if(!warped){
    meta.textContent = "마커 4개를 찾지 못했습니다. (템플릿 모서리 마커가 화면에 모두 들어오게 촬영)";
    cap.delete();
    return;
  }


  // 2) ROI (QR/로고를 피하는 영역)
  const WH = warped.cols, HH = warped.rows;
  const x0 = Math.floor(WH * 0.15), y0 = Math.floor(HH * 0.10);
  const x1 = Math.floor(WH * 0.92), y1 = Math.floor(HH * 0.80);
  const roiRect = new cv.Rect(x0, y0, x1-x0, y1-y0);
  const roi = warped.roi(roiRect);

  // 3) 잉크 마스크
  let ink = labInkMask(roi);

  // QR쪽 잡티 제거(ROI 좌상단 일부 무시)
  const rh = ink.rows, rw = ink.cols;
  const rx = Math.floor(rw * 0.25), ry = Math.floor(rh * 0.35);
  const cutRect = new cv.Rect(0,0,rx,ry);
  ink.roi(cutRect).setTo(new cv.Scalar(0));

  // 4) 가장 큰 컴포넌트 선택
  const compInfo = biggestComponent(ink);
  if(!compInfo){
    meta.textContent = "공룡 영역을 찾지 못했습니다. (조명/거리/각도 확인)";
    cap.delete(); warped.delete(); roi.delete(); ink.delete();
    return;
  }

  // 5) bbox 기준 crop + alpha 적용
  const {comp, bbox} = compInfo;

  // 약간 확장
  const pad = 30;
  const cx = Math.max(0, bbox.x - pad);
  const cy = Math.max(0, bbox.y - pad);
  const cw = Math.min(comp.cols - cx, bbox.w + pad*2);
  const ch = Math.min(comp.rows - cy, bbox.h + pad*2);

  const compCrop = comp.roi(new cv.Rect(cx, cy, cw, ch));
  const roiCrop = roi.roi(new cv.Rect(cx, cy, cw, ch));

   // 결과 RGBA: 배경은 투명, 공룡만 남기기(빠른 방식)
  const out = new cv.Mat(roiCrop.rows, roiCrop.cols, cv.CV_8UC4);
  out.setTo(new cv.Scalar(0,0,0,0));       // 완전 투명으로 초기화
  roiCrop.copyTo(out, compCrop);           // 마스크 영역만 복사 (RGB + A)
  
  // alpha 채널을 compCrop으로 고정(더 확실)
  const ch = new cv.MatVector();
  cv.split(out, ch);
  ch.set(3, compCrop.clone());             // alpha = mask
  cv.merge(ch, out);
  ch.get(0).delete(); ch.get(1).delete(); ch.get(2).delete(); ch.get(3).delete();
  ch.delete();
  

  // 6) 화면에 표시
  outCanvas.width = out.cols;
  outCanvas.height = out.rows;
  cv.imshow(outCanvas, out);

  lastPngDataUrl = outCanvas.toDataURL("image/png");
  outImg.src = lastPngDataUrl;

  meta.textContent = "완료. 결과 PNG 생성됨";

  // cleanup
  cap.delete(); warped.delete(); roi.delete();
  ink.delete(); comp.delete(); compCrop.delete(); roiCrop.delete();
  out.delete();
}

function findCornerMarkers(rgbaMat){
  const gray = new cv.Mat();
  cv.cvtColor(rgbaMat, gray, cv.COLOR_RGBA2GRAY);

  const bin = new cv.Mat();
  cv.adaptiveThreshold(gray, bin, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY_INV, 51, 7);

  const contours = new cv.MatVector();
  const hierarchy = new cv.Mat();
  cv.findContours(bin, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

  const candidates = [];
  for(let i=0;i<contours.size();i++){
    const cnt = contours.get(i);
    const peri = cv.arcLength(cnt, true);
    const approx = new cv.Mat();
    cv.approxPolyDP(cnt, approx, 0.02 * peri, true);

    if(approx.rows === 4){
      const area = cv.contourArea(approx);
      if(area > 5000){
        const rect = cv.boundingRect(approx);
        const ratio = rect.width / rect.height;
        if(ratio > 0.75 && ratio < 1.33){
          const cx = rect.x + rect.width/2;
          const cy = rect.y + rect.height/2;
          candidates.push({ area, rect, cx, cy });
        }
      }
    }

    approx.delete();
    cnt.delete();
  }

  gray.delete(); bin.delete(); contours.delete(); hierarchy.delete();

  if(candidates.length < 4) return null;

  candidates.sort((a,b)=> b.area - a.area);
  const top = candidates.slice(0, 10);

  const W = rgbaMat.cols, H = rgbaMat.rows;
  const corners = [
    {name:"tl", x:0, y:0},
    {name:"tr", x:W, y:0},
    {name:"br", x:W, y:H},
    {name:"bl", x:0, y:H}
  ];

  const chosen = {};
  for(const c of corners){
    let best = null, bestD = 1e18;
    for(const cand of top){
      const dx = cand.cx - c.x;
      const dy = cand.cy - c.y;
      const d = dx*dx + dy*dy;
      if(d < bestD){
        bestD = d; best = cand;
      }
    }
    chosen[c.name] = best;
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

  // 처리용 캔버스 사이즈(성능용). 템플릿은 A4지만, 여기서는 축소 좌표계로 워프합니다.
  const OUT_W = 1600, OUT_H = 2260;

  // template.js의 마커(패딩/사이즈)와 "비율상" 대응되도록 고정 값 사용
  // (완전 정밀 매칭은 2단계에서 더 다듬습니다)
  const PAD = 90, M = 140;

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
