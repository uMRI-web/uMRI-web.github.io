const statusEl=document.getElementById("status");
const fileEl=document.getElementById("file");
const runBtn=document.getElementById("run");
const resultsEl=document.getElementById("results");
let pyodide=null, ready=false;

function status(msg,type=""){
  statusEl.textContent=msg;
  statusEl.className="status"+(type?" "+type:"");
}

async function boot(){
  try{
    status("解析エンジンを準備中…\n1/3 Python");
    pyodide=await loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.29.5/full/"});
    status("解析エンジンを準備中…\n2/3 NumPy / SciPy");
    await pyodide.loadPackage(["numpy","scipy"]);
    status("解析エンジンを準備中…\n3/3 MIMエンジン");
    const r=await fetch("./mim_engine.py?v=20261118-1",{cache:"no-store"});
    if(!r.ok)throw new Error("MIMエンジンを取得できません");
    await pyodide.runPythonAsync(await r.text());
    const test=JSON.parse(await pyodide.runPythonAsync("self_test_json()"));
    if(!test.pass)throw new Error("MIM自己テストに失敗しました");
    ready=true;
    runBtn.disabled=!fileEl.files[0];
    status("準備完了。m00ファイルを選択してください。","ok");
  }catch(e){
    console.error(e);
    status("準備に失敗しました。\n"+(e.message||e),"err");
  }
}

fileEl.addEventListener("change",()=>{runBtn.disabled=!(ready&&fileEl.files[0]);});

runBtn.addEventListener("click",async()=>{
  const f=fileEl.files[0];
  if(!f||!ready)return;
  runBtn.disabled=true;
  try{
    status("解析中…\n双極導出 → 1–45 Hz → 250 Hz → 2秒epoch → MIM");
    const bytes=new Uint8Array(await f.arrayBuffer());
    try{pyodide.FS.unlink("/tmp/input.m00")}catch(_e){}
    pyodide.FS.writeFile("/tmp/input.m00",bytes);
    const raw=await pyodide.runPythonAsync('analyze_m00_json("/tmp/input.m00")');
    render(JSON.parse(raw));
    status("解析完了。","ok");
  }catch(e){
    console.error(e);
    status("解析に失敗しました。\n"+(e.message||e),"err");
  }finally{
    runBtn.disabled=false;
  }
});

function render(r){
  resultsEl.hidden=false;
  document.getElementById("meta").innerHTML=
    '<p>入力: <b>'+esc(r.source)+'</b><br>'+
    '元サンプリング: '+r.original_sfreq.toFixed(1)+' Hz / 使用区間: '+
    r.used_start_sec.toFixed(0)+'–'+r.used_end_sec.toFixed(0)+' 秒<br>'+
    '解析epoch: '+r.epochs_kept+'/'+r.epochs_total+'（除外 '+r.epochs_rejected+'）</p>';

  const body=document.getElementById("mimRows");
  body.innerHTML="";
  for(const b of ["theta","alpha","beta"]){
    const x=r.mim[b];
    body.insertAdjacentHTML("beforeend",
      '<tr><td>'+b+'</td><td>'+x.raw.toFixed(5)+'</td><td>'+x.normalized.toFixed(5)+'</td></tr>');
  }

  document.getElementById("emats").innerHTML=
    '<p><b>既存EMATS学習済みモデルへ直接入力：</b>不可</p>'+
    '<p>一致: '+r.emats.matched_channels+'/19 ch（'+r.emats.match_percent.toFixed(1)+'%）<br>'+
    '不足: '+r.emats.missing_channels.join(", ")+'</p>'+
    '<p><b>再学習ルート：</b>'+esc(r.emats.retrain_route)+'</p>';
}

function esc(s){
  return String(s).replace(/[&<>"']/g,c=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}
boot();