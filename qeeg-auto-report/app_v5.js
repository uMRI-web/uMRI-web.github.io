const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const statusEl = document.getElementById("status");
const runBtn = document.getElementById("run");
const fileEl = document.getElementById("file");
const inputNameEl = document.getElementById("inputName");
const outputFormatEl = document.getElementById("outputFormat");
const drop = document.getElementById("drop");
let pyodide = null;
let engineReady = false;

function setStatus(msg, type="") {
  statusEl.textContent = msg;
  statusEl.className = "status" + (type ? " " + type : "");
}
function refreshButton(){ runBtn.disabled = !(engineReady && fileEl.files && fileEl.files[0]); }

async function boot(){
  try{
    setStatus("解析エンジンを読み込んでいます…\n1/3 Python環境を準備中");
    pyodide = await loadPyodide({indexURL: PYODIDE_BASE});

    setStatus("解析エンジンを読み込んでいます…\n2/3 NumPy / SciPy / Matplotlibを準備中");
    await pyodide.loadPackage(["numpy","scipy","matplotlib","micropip","lxml"]);

    setStatus("解析エンジンを読み込んでいます…\n3/3 Word生成機能を準備中");
    await pyodide.runPythonAsync(`import micropip
await micropip.install("python-docx==1.2.0")`);

    const resp = await fetch("./qeeg_engine.py?v=20261118-4", {cache:"no-store"});
    if(!resp.ok) throw new Error("解析コードを取得できませんでした");
    const code = await resp.text();
    await pyodide.runPythonAsync(code);

    engineReady = true;
    setStatus("準備完了。m00ファイルを選択してください。", "ok");
    refreshButton();
  }catch(err){
    console.error(err);
    setStatus("解析エンジンの準備に失敗しました。\n" + (err?.message || err), "err");
  }
}

fileEl.addEventListener("change", ()=>{
  const f=fileEl.files[0];
  if(f && !inputNameEl.value) inputNameEl.value=f.name.replace(/\.m00$/i,"");
  refreshButton();
});
["dragenter","dragover"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add("drag")}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove("drag")}));
drop.addEventListener("drop", e=>{
  const files=e.dataTransfer.files;
  if(files && files[0]){
    const dt=new DataTransfer(); dt.items.add(files[0]); fileEl.files=dt.files;
    fileEl.dispatchEvent(new Event("change"));
  }
});

runBtn.addEventListener("click", async ()=>{
  const file=fileEl.files[0];
  if(!file || !engineReady) return;
  runBtn.disabled=true;
  try{
    setStatus("m00をブラウザ内に読み込んでいます…");
    const data = new Uint8Array(await file.arrayBuffer());
    try{ pyodide.FS.unlink("/tmp/input.m00"); }catch(_e){}
    try{ pyodide.FS.unlink("/tmp/output.docx"); }catch(_e){}
    pyodide.FS.writeFile("/tmp/input.m00", data);

    const inputName = inputNameEl.value || file.name.replace(/\.m00$/i,"");
    pyodide.globals.set("_input_name", inputName);
    pyodide.globals.set("_source_filename", file.name);
    const format = outputFormatEl.value;
    const stem = file.name.replace(/\.m00$/i,"");

    setStatus("解析中…\nPSD・Z-score・トポグラフィー・Wordを作成しています。");
    await pyodide.runPythonAsync('generate_report("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.docx")');
    const docxBytes = pyodide.FS.readFile("/tmp/output.docx");
    const docxBlob = new Blob([docxBytes], {type:"application/vnd.openxmlformats-officedocument.wordprocessingml.document"});

    if(format === "docx"){
      downloadBlob(docxBlob, stem+"_脳波解析結果.docx");
      setStatus("完了しました。Wordファイルを保存しました。","ok");
      return;
    }

    setStatus("PDFを作成しています…\nWordをブラウザ内で表示してPDF化しています。");
    const pdfBlob = await docxBlobToStablePdf(docxBlob);

    if(format === "pdf"){
      downloadBlob(pdfBlob, stem+"_脳波解析結果.pdf");
      setStatus("完了しました。PDFファイルを保存しました。","ok");
    }else{
      downloadBlob(docxBlob, stem+"_脳波解析結果.docx");
      await new Promise(r=>setTimeout(r,700));
      downloadBlob(pdfBlob, stem+"_脳波解析結果.pdf");
      setStatus("完了しました。WordとPDFを2ファイル別々に保存しました。\nブラウザから複数ダウンロードの確認が出た場合は許可してください。","ok");
    }
  }catch(err){
    console.error(err);
    setStatus("解析に失敗しました。\n" + (err?.message || err), "err");
  }finally{
    refreshButton();
  }
});

function downloadBlob(blob, filename){
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href=url;
  a.download=filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),3000);
}

async function docxBlobToStablePdf(docxBlob){
  const missing=[];
  if(!window.JSZip) missing.push("JSZip");
  if(!window.docx) missing.push("docx-preview");
  if(!window.html2canvas) missing.push("html2canvas");
  if(!window.jspdf || !window.jspdf.jsPDF) missing.push("jsPDF");
  if(missing.length){
    throw new Error("PDF変換ライブラリの読み込みに失敗しました: " + missing.join(", ") + "。ページを再読み込みしてください。");
  }
  const host=document.getElementById("pdfRenderHost");
  host.innerHTML="";
  await window.docx.renderAsync(docxBlob, host, null, {
    className:"docx",
    inWrapper:true,
    ignoreWidth:false,
    ignoreHeight:false,
    ignoreFonts:false,
    breakPages:true,
    renderHeaders:true,
    renderFooters:true,
    renderFootnotes:true,
    useBase64URL:true
  });

  // Wait for embedded images and browser fonts to finish rendering.
  const imgs=[...host.querySelectorAll("img")];
  await Promise.all(imgs.map(img=>img.complete ? Promise.resolve() : new Promise(resolve=>{
    img.onload=resolve; img.onerror=resolve;
  })));
  if(document.fonts?.ready) await document.fonts.ready;
  await new Promise(r=>setTimeout(r,250));

  const pages=[...host.querySelectorAll("section.docx")];
  if(!pages.length) throw new Error("PDF用のWordページを描画できませんでした。");

  const {jsPDF}=window.jspdf;
  const pdf=new jsPDF({orientation:"portrait",unit:"mm",format:"a4",compress:true});
  const pageW=210, pageH=297;
  for(let i=0;i<pages.length;i++){
    const canvas=await window.html2canvas(pages[i],{
      scale:1.8,
      backgroundColor:"#ffffff",
      useCORS:true,
      logging:false
    });
    const imgData=canvas.toDataURL("image/jpeg",0.92);
    const ratio=Math.min(pageW/canvas.width,pageH/canvas.height);
    const w=canvas.width*ratio;
    const h=canvas.height*ratio;
    if(i>0) pdf.addPage("a4","portrait");
    pdf.addImage(imgData,"JPEG",(pageW-w)/2,(pageH-h)/2,w,h,undefined,"FAST");
  }
  host.innerHTML="";
  return pdf.output("blob");
}

console.log("PDF libs", {
  JSZip: !!window.JSZip,
  docx: !!window.docx,
  html2canvas: !!window.html2canvas,
  jspdf: !!(window.jspdf && window.jspdf.jsPDF)
});
boot();