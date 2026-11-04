from __future__ import annotations
import re, os
from datetime import datetime
import numpy as np
from scipy import signal
from scipy.integrate import simpson
from scipy.interpolate import griddata
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import Normalize
from docx import Document
from docx.shared import Inches

ELECTRODES = ["Fp1","Fp2","C3","C4","O1","O2","T3","T4","F7","F8","T5","T6"]
BANDS = {"theta":(4.0,8.0),"alpha":(8.0,12.0),"beta":(12.0,30.0)}
JP_BAND = {"alpha":"アルファ","beta":"ベータ","theta":"シータ"}

NORMS = {
"Fp1": {"alpha": (0.2537241354124555, 0.1143863921071352), "beta": (0.3847046820198212, 0.1569605655107956), "theta": (0.3615539708156466, 0.1426843735841984)},
"Fp2": {"alpha": (0.2541717762487292, 0.1118139999010146), "beta": (0.3833098027869746, 0.1533069988593477), "theta": (0.3625121296847581, 0.1406453148521751)},
"C3": {"alpha": (0.2931844678359529, 0.1255000104172534), "beta": (0.3958472611033509, 0.1591633895191253), "theta": (0.3109468490266418, 0.147342737891664)},
"C4": {"alpha": (0.2945569042329437, 0.1206528357545111), "beta": (0.3996677499589876, 0.1565801726181291), "theta": (0.3057778147353301, 0.1452585984930902)},
"O1": {"alpha": (0.4034704403196188, 0.1714926587967885), "beta": (0.2967908883001297, 0.1362964074986625), "theta": (0.2997440497054312, 0.1472471999728787)},
"O2": {"alpha": (0.4117737484673411, 0.1746765787654276), "beta": (0.2915948793999294, 0.1352953292783408), "theta": (0.2966147353340241, 0.1487479326041815)},
"T3": {"alpha": (0.2811894513723094, 0.1161146770284523), "beta": (0.4076800929593639, 0.1624632289614618), "theta": (0.311089753243223, 0.1428875686591597)},
"T4": {"alpha": (0.291953691980695, 0.1173948699392359), "beta": (0.393442637363224, 0.155488924941337), "theta": (0.3146206570742583, 0.1383156059856409)},
"F7": {"alpha": (0.278944790561544, 0.1166997874477375), "beta": (0.3822419265057545, 0.1515640858226808), "theta": (0.3388162101944497, 0.137152746644922)},
"F8": {"alpha": (0.2765230902280553, 0.1112775062731066), "beta": (0.384173930699741, 0.1461960850996703), "theta": (0.3392904310033377, 0.1334459547441513)},
"T5": {"alpha": (0.3613932900246228, 0.1547529495412748), "beta": (0.3293537718403816, 0.148341266488295), "theta": (0.3092765597956239, 0.1456655679176559)},
"T6": {"alpha": (0.379228111263995, 0.159721222473676), "beta": (0.3146227651731904, 0.1406162575431702), "theta": (0.3061671645537065, 0.1440432497260828)}
}
FRONTAL = {
"alpha_rel_diff": (0.005642670753681726, 0.11630655268367981),
"beta_theta_fp1": (1.5825569063193847, 2.1543143494326022),
"beta_theta_fp2": (1.5909449831566282, 3.2237316700187293),
"beta_theta_diff": (0.008384242169726068, 1.7684331334725822)
}
CH_POS = {
"Fp1":(1.5,4.2),"Fp2":(2.5,4.2),"C3":(0.95,2.0),"C4":(3.05,2.0),
"O1":(1.5,0.0),"O2":(2.5,0.0),"T3":(-0.1,2.0),"T4":(4.1,2.0),
"F7":(0.1,3.0),"F8":(3.9,3.0),"T5":(0.4,0.4),"T6":(3.6,0.4)
}

def zscore(x, mean, sd):
    return (x-mean)/sd

def parse_m00(path):
    with open(path,"r",encoding="utf-8",errors="replace") as f:
        header=f.readline().strip()
        columns=f.readline().strip().split()
    m=re.search(r"SamplingInterval\[ms\]=([0-9.]+)",header)
    sf=1000.0/float(m.group(1)) if m else 500.0
    required=["Fp1-A1","Fp2-A2","F7-A1","F8-A2","C3-A1","C4-A2","T3-A1","T4-A2","T5-A1","T6-A2","O1-A1","O2-A2"]
    missing=[c for c in required if c not in columns]
    if missing:
        raise ValueError("必要なEEG列がありません: "+", ".join(missing))
    usecols=[columns.index(c) for c in required]
    data=np.loadtxt(path,skiprows=2,usecols=usecols,dtype=float)
    if data.ndim==1:
        data=data[None,:]
    data=data[np.all(np.isfinite(data),axis=1)]
    if len(data)==0:
        raise ValueError("有効なEEGデータがありません")
    raw_names=["Fp1","Fp2","F7","F8","C3","C4","T3","T4","T5","T6","O1","O2"]
    idx={n:i for i,n in enumerate(raw_names)}
    return {e:data[:,idx[e]] for e in ELECTRODES}, sf

def analyze(path):
    sigs,sf=parse_m00(path)
    out={}
    for e in ELECTRODES:
        freqs,psd=signal.welch(sigs[e],sf,nperseg=int(4*sf))
        dx=float(freqs[1]-freqs[0])
        absolute={}
        for band,(lo,hi) in BANDS.items():
            mask=(freqs>=lo)&(freqs<=hi)
            absolute[band]=float(simpson(psd[mask],dx=dx))
        total=sum(absolute.values())
        relative={b:absolute[b]/total for b in ("alpha","beta","theta")}
        zs={b:zscore(relative[b],*NORMS[e][b]) for b in ("alpha","beta","theta")}
        out[e]={"freqs":freqs,"psd":psd,"absolute":absolute,"relative":relative,"z":zs}
    fp1,fp2=out["Fp1"],out["Fp2"]
    alpha_abs_diff=float(np.log(fp2["absolute"]["alpha"])-np.log(fp1["absolute"]["alpha"]))
    alpha_rel_diff=float(np.log(fp2["relative"]["alpha"])-np.log(fp1["relative"]["alpha"]))
    b1=fp1["absolute"]["beta"]/fp1["absolute"]["theta"]
    b2=fp2["absolute"]["beta"]/fp2["absolute"]["theta"]
    bd=b2-b1
    frontal={
      "alpha_abs_diff":alpha_abs_diff,
      "z_alpha_rel_diff":zscore(alpha_rel_diff,*FRONTAL["alpha_rel_diff"]),
      "b1":b1,"b2":b2,
      "zb1":zscore(b1,*FRONTAL["beta_theta_fp1"]),
      "zb2":zscore(b2,*FRONTAL["beta_theta_fp2"]),
      "bd":bd,
      "zbd":zscore(bd,*FRONTAL["beta_theta_diff"])
    }
    return out,frontal,sf

def save_topomap(results,band,path):
    n=300
    center=(2.0,2.0)
    radius=2.0
    x=np.array([CH_POS[e][0] for e in ELECTRODES])
    y=np.array([CH_POS[e][1] for e in ELECTRODES])
    vals=np.array([results[e]["z"][band] for e in ELECTRODES])
    xi=np.linspace(-2,6,n)
    yi=np.linspace(-2,6,n)
    xx,yy=np.meshgrid(xi,yi)
    zi=griddata((x,y),vals,(xx,yy),method="cubic")
    zi[np.sqrt((xx-center[0])**2+(yy-center[1])**2)>radius]=np.nan
    fig,ax=plt.subplots(figsize=(10,8))
    dist=ax.contourf(xi,yi,zi,60,cmap="bwr",norm=Normalize(vmin=-2.5,vmax=2.5))
    ax.contour(xi,yi,zi,15,linewidths=.5,colors="grey")
    fig.colorbar(dist,ax=ax,format="%.1f")
    ax.scatter(x,y,marker="o",c="b",s=15,zorder=3)
    ax.add_patch(patches.Circle(center,radius,edgecolor="k",facecolor="none",zorder=4))
    ax.add_patch(patches.Ellipse((0,2),.4,1,edgecolor="k",facecolor="w"))
    ax.add_patch(patches.Ellipse((4,2),.4,1,edgecolor="k",facecolor="w"))
    ax.add_patch(patches.Polygon([[1.6,3.6],[2,4.3],[2.4,3.6]],edgecolor="k",facecolor="w"))
    for s in ax.spines.values():
        s.set_linewidth(0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-.5,4.5)
    ax.set_ylim(-.5,4.5)
    ax.set_title(band+"_topomap")
    fig.savefig(path,dpi=100,bbox_inches="tight")
    plt.close(fig)

def save_psd(results,e,path):
    r=results[e]
    fig,ax=plt.subplots()
    ax.plot(r["freqs"],r["psd"])
    ax.ticklabel_format(style="plain",axis="y",useOffset=False)
    ax.set_title("EEG-"+e)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Power Spectral Density [V^2/Hz]")
    ax.set_xlim(4,30)
    fig.savefig(path,dpi=100,bbox_inches="tight")
    plt.close(fig)

def fmt2(x):
    return str(round(float(x),2))

def fmt3g(x):
    return f"{float(x):.3g}"

def generate_report(input_path,input_name,source_filename,output_path):
    results,frontal,sf=analyze(input_path)
    work="/tmp/qeeg_assets"
    os.makedirs(work,exist_ok=True)
    tops={}
    for band in ("theta","alpha","beta"):
        p=f"{work}/{band}.png"
        save_topomap(results,band,p)
        tops[band]=p
    psds={}
    for e in ELECTRODES:
        p=f"{work}/psd_{e}.png"
        save_psd(results,e,p)
        psds[e]=p

    doc=Document()
    doc.add_heading("脳波の解析結果")
    doc.add_paragraph(" ")
    doc.add_paragraph("作成日："+datetime.now().strftime("%Y年%m月%d日"))
    doc.add_paragraph("ファイル名："+source_filename)
    doc.add_paragraph("インプット名："+input_name)
    doc.add_paragraph(" ")
    doc.add_heading("脳波トポグラフィー",level=2)
    doc.add_paragraph("各時刻、各電極計12箇所における脳波を周波数毎（シータ波・アルファ波・ベータ波として分類）に分析し、脳波トポグラフィーを描画します。")
    doc.add_heading("シータ波の分布",level=3)
    doc.add_picture(tops["theta"],width=Inches(3.5))
    doc.add_page_break()
    doc.add_heading("アルファ波の分布",level=3)
    doc.add_picture(tops["alpha"],width=Inches(3.5))
    doc.add_heading("ベータ波の分布",level=3)
    doc.add_picture(tops["beta"],width=Inches(3.5))
    doc.add_page_break()
    doc.add_heading("Zスコア（標準得点）の算出",level=2)
    doc.add_paragraph("正常被験者1297人の脳波データを基準として入力ファイルのZスコアを算出します。")
    doc.add_paragraph("Zスコアは、入力データと正常なデータ群の平均値との差を正常なデータ群の標準偏差で除したもので、入力データがどれだけ正常なデータから外れているかを示す指標の一つです。")
    doc.add_paragraph("例えば、Z値が+1であるならデータセットの分布から標準偏差1つ分だけ外れている事を示します。")
    for e in ELECTRODES:
        for band in ("alpha","beta","theta"):
            doc.add_paragraph(f"{e}電極の{JP_BAND[band]}波の相対パワースペクトルのZスコアは{fmt2(results[e]['z'][band])}です。")
        doc.add_paragraph(" ")
    f=frontal
    doc.add_heading("前頭葉の左右差の分析",level=2)
    doc.add_paragraph("前頭葉のアルファ波の左右差やそのZスコア、前頭葉のベータ波とシータ波の比率やそのZスコアが様々な症例と相関性のある事が近年の論文によって示されています。")
    doc.add_paragraph("前頭葉のアルファ波左右差の値は"+fmt3g(f["alpha_abs_diff"])+"です。")
    doc.add_paragraph("前頭葉のアルファ波左右差の相対パワースペクトルのZスコアは"+fmt3g(f["z_alpha_rel_diff"])+"です。")
    doc.add_paragraph("前頭葉（左）のベータ波/シータ波の比率は"+fmt3g(f["b1"])+"です。")
    doc.add_paragraph("前頭葉（右）のベータ波/シータ波の比率は"+fmt3g(f["b2"])+"です。")
    doc.add_paragraph("前頭葉（左）のベータ波/シータ波のZスコアは"+fmt3g(f["zb1"])+"です。")
    doc.add_paragraph("前頭葉（右）のベータ波/シータ波のZスコアは"+fmt3g(f["zb2"])+"です。")
    doc.add_paragraph("前頭葉のベータ波/シータ波の左右差（右−左）は"+fmt3g(f["bd"])+"です。")
    doc.add_paragraph("前頭葉のベータ波/シータ波の左右差（右−左）のZスコアは"+fmt3g(f["zbd"])+"です。")
    doc.add_page_break()
    doc.add_heading("パワースペクトル密度の周波数依存性",level=2)
    doc.add_paragraph("周波数解析した各電極におけるパワースペクトル密度の周波数依存性を描画します。")
    doc.add_paragraph("シータ波帯域が4~8 [Hz]、アルファ波帯域が8~12 [Hz]、ベータ波帯域が12~30 [Hz]となっています。")
    for e in ELECTRODES:
        doc.add_picture(psds[e],width=Inches(3.5))
    doc.save(output_path)
    return output_path
