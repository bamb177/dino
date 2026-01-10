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
    OUT_W - PAD -_
