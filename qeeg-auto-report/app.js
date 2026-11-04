const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const statusEl = document.getElementById("status");
const runBtn = document.getElementById("run");
const fileEl = document.getElementById("file");
const inputNameEl = document.getElementById("inputName");
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
    await pyodide.runPythonAsync('import micropip\nawait micropip.install("python-docx==1.2.0")');
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
    try{ pyodide.FS.unlink("/tmp/input.m00"); }catch(_e){}
    try{ pyodide.FS.unlink("/tmp/output.docx"); }catch(_e){}
    pyodide.FS.writeFile("/tmp/input.m00", data);
    pyodide.globals.set("_input_name", inputNameEl.value || file.name.replace(/\.m00$/i,""));
    pyodide.globals.set("_source_filename", file.name);
    setStatus("解析中…\nPSD・Z-score・トポグラフィー・Wordを作成しています。");
    await pyodide.runPythonAsync('generate_report("/tmp/input.m00", _input_name, _source_filename, "/tmp/output.docx")');
    const out = pyodide.FS.readFile("/tmp/output.docx");
    const blob = new Blob([out], {type:"application/vnd.openxmlformats-officedocument.wordprocessingml.document"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stem=file.name.replace(/\.m00$/i,"");
    a.href=url; a.download=stem+"_脳波解析結果.docx"; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),2000);
    setStatus("完了しました。Wordファイルを保存しました。", "ok");
  }catch(err){
    console.error(err);
    setStatus("解析に失敗しました。\n" + err.message, "err");
  }finally{
    refreshButton();
  }
});

boot();