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

function cloneSectionWithChildren(source, children){
  const page=source.cloneNode(false);
  for(const child of children) page.appendChild(child.cloneNode(true));
  return page;
}

function findChildIndexByText(children, marker){
  return children.findIndex(el => (el.textContent || "").replace(/\s+/g,"").includes(marker.replace(/\s+/g,"")));
}

function splitTableRows(table, keepRowIndexes){
  const clone=table.cloneNode(true);
  const rows=[...clone.querySelectorAll("tr")];
  rows.forEach((row,idx)=>{
    if(!keepRowIndexes.includes(idx)) row.remove();
  });
  return clone;
}

function paginateDocxPreviewLikeWord(host){
  const sections=[...host.querySelectorAll("section.docx")];
  if(sections.length < 5) return sections;

  const pages=[];

  // Word page 1-2: explicit page breaks already match.
  pages.push(sections[0].cloneNode(true));
  pages.push(sections[1].cloneNode(true));

  // Word pages 3-5: split the long Z-score section at the same visible points.
  {
    const src=sections[2];
    const kids=[...src.children];
    const i1=findChildIndexByText(kids,"O1電極のベータ波");
    const i2=findChildIndexByText(kids,"T5電極のベータ波");
    if(i1>=0 && i2>i1){
      pages.push(cloneSectionWithChildren(src,kids.slice(0,i1+1)));
      pages.push(cloneSectionWithChildren(src,kids.slice(i1+1,i2+1)));
      pages.push(cloneSectionWithChildren(src,kids.slice(i2+1)));
    }else{
      pages.push(src.cloneNode(true));
    }
  }

  // Word pages 6-10: 12 PSD figures are laid out as 2 / 3 / 3 / 3 / 1.
  {
    const src=sections[3];
    const kids=[...src.children];
    const imgIdx=kids.map((el,i)=>el.querySelector("img")?i:-1).filter(i=>i>=0);
    if(imgIdx.length>=12){
      const starts=[0,imgIdx[2],imgIdx[5],imgIdx[8],imgIdx[11]];
      const ends=[imgIdx[2],imgIdx[5],imgIdx[8],imgIdx[11],kids.length];
      for(let k=0;k<5;k++){
        pages.push(cloneSectionWithChildren(src,kids.slice(starts[k],ends[k])));
      }
    }else{
      pages.push(src.cloneNode(true));
    }
  }

  // Word pages 11-12: split the first arousal table after its first data row.
  {
    const src=sections[4];
    const kids=[...src.children];
    const tableIdx=kids.findIndex(el => el.tagName==="TABLE" || el.querySelector("table"));
    if(tableIdx>=0){
      const tableEl=kids[tableIdx].tagName==="TABLE" ? kids[tableIdx] : kids[tableIdx].querySelector("table");
      const rows=[...tableEl.querySelectorAll("tr")];
      if(rows.length>=4){
        const p11=src.cloneNode(false);
        for(const child of kids.slice(0,tableIdx)) p11.appendChild(child.cloneNode(true));

        let table11Wrap;
        if(kids[tableIdx].tagName==="TABLE"){
          table11Wrap=splitTableRows(tableEl,[0,1]);
        }else{
          table11Wrap=kids[tableIdx].cloneNode(true);
          const t=table11Wrap.querySelector("table");
          const rr=[...t.querySelectorAll("tr")];
          rr.forEach((r,idx)=>{ if(![0,1].includes(idx)) r.remove(); });
        }
        p11.appendChild(table11Wrap);
        pages.push(p11);

        const p12=src.cloneNode(false);
        let table12Wrap;
        if(kids[tableIdx].tagName==="TABLE"){
          table12Wrap=splitTableRows(tableEl,[2,3]);
        }else{
          table12Wrap=kids[tableIdx].cloneNode(true);
          const t=table12Wrap.querySelector("table");
          const rr=[...t.querySelectorAll("tr")];
          rr.forEach((r,idx)=>{ if(![2,3].includes(idx)) r.remove(); });
        }
        p12.appendChild(table12Wrap);
        for(const child of kids.slice(tableIdx+1)) p12.appendChild(child.cloneNode(true));
        pages.push(p12);
      }else{
        pages.push(src.cloneNode(true));
      }
    }else{
      pages.push(src.cloneNode(true));
    }
  }

  return pages;
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

  const imgs=[...host.querySelectorAll("img")];
  await Promise.all(imgs.map(img=>img.complete ? Promise.resolve() : new Promise(resolve=>{
    img.onload=resolve; img.onerror=resolve;
  })));
  if(document.fonts?.ready) await document.fonts.ready;
  await new Promise(r=>setTimeout(r,250));

  const pages=paginateDocxPreviewLikeWord(host);
  if(!pages.length) throw new Error("PDF用のWordページを描画できませんでした。");

  // Replace docx-preview's 5 long sections by 12 Word-like pages for rendering.
  host.innerHTML="";
  for(const page of pages){
    page.style.margin="0";
    page.style.boxShadow="none";
    page.style.breakAfter="page";
    host.appendChild(page);
  }
  await new Promise(r=>setTimeout(r,120));

  const {jsPDF}=window.jspdf;
  const pdf=new jsPDF({orientation:"portrait",unit:"mm",format:"letter",compress:true});
  const pageW=215.9, pageH=279.4; // same paper size as the generated Word document

  for(let i=0;i<pages.length;i++){
    const canvas=await window.html2canvas(pages[i],{
      scale:2.0,
      backgroundColor:"#ffffff",
      useCORS:true,
      logging:false,
      windowWidth:pages[i].scrollWidth,
      windowHeight:pages[i].scrollHeight
    });
    const imgData=canvas.toDataURL("image/png");
    if(i>0) pdf.addPage("letter","portrait");

    // Keep the rendered Word page aspect ratio and fill the Letter page.
    const ratio=Math.min(pageW/canvas.width,pageH/canvas.height);
    const w=canvas.width*ratio;
    const h=canvas.height*ratio;
    pdf.addImage(imgData,"PNG",(pageW-w)/2,(pageH-h)/2,w,h,undefined,"FAST");
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