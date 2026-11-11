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
    setStatus("解析エンジンを読み込んでいます…\n1/4 Python環境を準備中");
    pyodide = await loadPyodide({indexURL: PYODIDE_BASE});
    setStatus("解析エンジンを読み込んでいます…\n2/4 NumPy / SciPy / Matplotlibを準備中");
    await pyodide.loadPackage(["numpy","scipy","matplotlib","micropip","lxml"]);
    setStatus("解析エンジンを読み込んでいます…\n3/4 Word / PDF生成機能を準備中");
    await pyodide.runPythonAsync(`import micropip\nawait micropip.install(["python-docx==1.2.0","fpdf2==2.8.4"])`);
    setStatus("解析エンジンを読み込んでいます…\n4/4 日本語PDFフォントを準備中");
    const fontResp = await fetch("https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf");
    if(!fontResp.ok) throw new Error("日本語PDFフォントを取得できませんでした");
    const fontBytes = new Uint8Array(await fontResp.arrayBuffer());
    pyodide.FS.writeFile("/tmp/NotoSansJP.ttf", fontBytes);
    const resp = await fetch("./qeeg_engine.py", {cache:"no-store"});
    if(!resp.ok) throw new Error("解析コードを取得できませんでした");
    const code = await resp.text();
    await pyodide.runPythonAsync(code);
    engineReady = true;
    setStatus("準備完了。m00ファイルを選択してください。", "ok");
    refreshButton();
  }catch(err){
    console.error(err);
    setStatus("解析エンジンの準備に失敗しました。\n" + err.message, "err");
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
    const paths=["/tmp/input.m00","/tmp/output.docx","/tmp/output.pdf","/tmp/output_bundle.zip"];
    for(const p of paths){ try{ pyodide.FS.unlink(p); }catch(_e){} }
    pyodide.FS.writeFile("/tmp/input.m00", data);

    const inputName = inputNameEl.value || file.name.replace(/\.m00$/i,"");
    pyodide.globals.set("_input_name", inputName);
    pyodide.globals.set("_source_filename", file.name);
    const format = outputFormatEl.value;

    setStatus("解析中…\nPSD・Z-score・トポグラフィー・レポートを作成しています。");

    if(format === "docx"){
      await pyodide.runPythonAsync('generate_report("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.docx")');
      downloadBytes(pyodide.FS.readFile("/tmp/output.docx"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file.name.replace(/\.m00$/i,"")+"_脳波解析結果.docx");
      setStatus("完了しました。Wordファイルを保存しました。","ok");
    }else if(format === "pdf"){
      await pyodide.runPythonAsync('generate_pdf("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.pdf", "/tmp/NotoSansJP.ttf")');
      downloadBytes(pyodide.FS.readFile("/tmp/output.pdf"),
        "application/pdf",
        file.name.replace(/\.m00$/i,"")+"_脳波解析結果.pdf");
      setStatus("完了しました。PDFファイルを保存しました。","ok");
    }else{
      await pyodide.runPythonAsync(`
generate_report("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.docx")
generate_pdf("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.pdf", "/tmp/NotoSansJP.ttf")
import zipfile
with zipfile.ZipFile("/tmp/output_bundle.zip","w",zipfile.ZIP_DEFLATED) as z:
    z.write("/tmp/output.docx", arcname="report.docx")
    z.write("/tmp/output.pdf", arcname="report.pdf")
`);
      downloadBytes(pyodide.FS.readFile("/tmp/output_bundle.zip"),
        "application/zip",
        file.name.replace(/\.m00$/i,"")+"_脳波解析結果_Word+PDF.zip");
      setStatus("完了しました。Word＋PDFのZIPを保存しました。","ok");
    }
  }catch(err){
    console.error(err);
    setStatus("解析に失敗しました。\n" + (err?.message || err), "err");
  }finally{
    refreshButton();
  }
});

function downloadBytes(bytes, mime, filename){
  const blob = new Blob([bytes], {type:mime});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href=url;
  a.download=filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
}

boot();