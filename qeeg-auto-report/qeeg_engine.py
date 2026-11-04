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


REGIONS = [
    ("前頭部", ["Fp1","Fp2","F7","F8"]),
    ("中心部", ["C3","C4"]),
    ("側頭部", ["T3","T4","T5","T6"]),
    ("後頭部", ["O1","O2"]),
]

def _zlabel(z):
    return f"{z:+.2f}"

def _band_finding(results, band):
    high=[(e,results[e]["z"][band]) for e in ELECTRODES if results[e]["z"][band] >= 2.0]
    low=[(e,results[e]["z"][band]) for e in ELECTRODES if results[e]["z"][band] <= -2.0]
    name=JP_BAND[band]
    parts=[]
    if high:
        items="、".join([f"{e}（Z={_zlabel(z)}）" for e,z in high])
        parts.append(f"{items}で正常参照群より2SD以上の高値")
    if low:
        items="、".join([f"{e}（Z={_zlabel(z)}）" for e,z in low])
        parts.append(f"{items}で正常参照群より2SD以上の低値")
    if not parts:
        return f"{name}帯域：|Z|≧2の明らかな定量的偏位を認めません。"
    return f"{name}帯域：" + "、".join(parts) + "を認めます。"

def _region_phrase(electrodes):
    labels=[]
    remaining=set(electrodes)
    for region, members in REGIONS:
        hit=[e for e in members if e in remaining]
        if len(hit) >= 2:
            labels.append(f"{region}（{'・'.join(hit)}）")
            remaining.difference_update(hit)
    labels.extend([e for e in ELECTRODES if e in remaining])
    return "、".join(labels)

def _impression(results, frontal):
    pieces=[]
    for band in ("theta","alpha","beta"):
        high=[e for e in ELECTRODES if results[e]["z"][band] >= 2.0]
        low=[e for e in ELECTRODES if results[e]["z"][band] <= -2.0]
        if high:
            pieces.append(f"{JP_BAND[band]}帯域の{_region_phrase(high)}で相対パワー高値")
        if low:
            pieces.append(f"{JP_BAND[band]}帯域の{_region_phrase(low)}で相対パワー低値")

    if abs(frontal["z_alpha_rel_diff"]) >= 2.0:
        direction="右優位" if frontal["z_alpha_rel_diff"] > 0 else "左優位"
        pieces.append(f"前頭部α相対パワー左右差の偏位（{direction}）")
    if abs(frontal["zbd"]) >= 2.0:
        direction="右高値" if frontal["zbd"] > 0 else "左高値"
        pieces.append(f"前頭部β/θ比左右差の偏位（{direction}）")
    if abs(frontal["zb1"]) >= 2.0:
        pieces.append("左前頭部β/θ比の基準範囲からの偏位")
    if abs(frontal["zb2"]) >= 2.0:
        pieces.append("右前頭部β/θ比の基準範囲からの偏位")

    if not pieces:
        return "今回評価したθ・α・β帯域の相対パワーおよび前頭部左右差・β/θ比について、正常参照群から2SD以上の明らかな定量的偏位を認めません。"
    return "qEEG定量解析では、" + "、".join(pieces) + "を認めます。"


def _arousal_metrics(results):
    mean_rel = {
        band: float(np.mean([results[e]["relative"][band] for e in ELECTRODES]))
        for band in ("alpha","beta","theta")
    }
    eps = 1e-12
    global_metrics = {
        "engagement": mean_rel["beta"] / max(mean_rel["alpha"] + mean_rel["theta"], eps),
        "beta_alpha": mean_rel["beta"] / max(mean_rel["alpha"], eps),
        "beta_theta": mean_rel["beta"] / max(mean_rel["theta"], eps),
    }
    per_electrode = {}
    for e in ELECTRODES:
        r = results[e]["relative"]
        per_electrode[e] = {
            "engagement": r["beta"] / max(r["alpha"] + r["theta"], eps),
            "beta_alpha": r["beta"] / max(r["alpha"], eps),
            "beta_theta": r["beta"] / max(r["theta"], eps),
        }
    region_engagement = {}
    for region, members in REGIONS:
        region_engagement[region] = float(np.mean([per_electrode[e]["engagement"] for e in members]))
    return mean_rel, global_metrics, per_electrode, region_engagement

def add_arousal_profile(doc, results):
    mean_rel, gm, per_electrode, region_engagement = _arousal_metrics(results)

    doc.add_heading("5. qEEG覚醒度プロフィール（研究的参考指標）", level=3)
    doc.add_paragraph(
        "θ・α・βの3帯域から、覚醒・注意研究で用いられる比率指標を参考値として算出します。"
        "本項目は記録全体の時間平均に基づく記述的プロフィールであり、意識障害・注意障害・低覚醒を診断する指標ではありません。"
    )
    doc.add_paragraph(
        f"12電極平均の相対パワーは、α {mean_rel['alpha']:.2f}、β {mean_rel['beta']:.2f}、θ {mean_rel['theta']:.2f} です。"
    )
    doc.add_paragraph(
        f"Engagement Index［β/(α+θ)］：{gm['engagement']:.2f}"
    )
    doc.add_paragraph(
        f"β/α比：{gm['beta_alpha']:.2f}"
    )
    doc.add_paragraph(
        f"β/θ比：{gm['beta_theta']:.2f}"
    )

    doc.add_paragraph(
        "領域別Engagement Index（本記録内の参考値）："
        + "、".join([f"{region} {region_engagement[region]:.2f}" for region, _ in REGIONS])
        + "。"
    )

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "電極"
    hdr[1].text = "β/(α+θ)"
    hdr[2].text = "β/α"
    hdr[3].text = "β/θ"
    for e in ELECTRODES:
        row = table.add_row().cells
        row[0].text = e
        row[1].text = f"{per_electrode[e]['engagement']:.2f}"
        row[2].text = f"{per_electrode[e]['beta_alpha']:.2f}"
        row[3].text = f"{per_electrode[e]['beta_theta']:.2f}"

    doc.add_paragraph(
        "現時点では本システムに、これら3指標について年齢等を調整した正常参照値や臨床カットオフは設定していません。"
        "したがって数値の高低のみから覚醒度や注意機能の正常・異常を判定せず、眠気、開閉眼、薬剤、覚醒状態、アーチファクト、臨床所見と併せて解釈してください。"
    )

def add_interpretation_report(doc, results, frontal, sf):
    doc.add_page_break()
    doc.add_heading("定量解析所見（自動生成・医師確認前）", level=2)

    doc.add_heading("1. 記録・解析条件", level=3)
    doc.add_paragraph(
        f"日本光電 Neurofax EEG-1290 / EEG-1200 Ver.06-01 からASCII形式で出力された12電極データを解析しました。"
        f"A1は左耳朶、A2は右耳朶を基準電極とし、サンプリング周波数は{sf:g} Hzです。"
        "Welch法（4秒窓）でパワースペクトル密度を算出し、θ 4–8 Hz、α 8–12 Hz、β 12–30 Hzを積分しました。"
        "各帯域パワーをθ+α+βの合計で除した相対パワーについて、正常参照群との比較からZ-scoreを算出しています。"
    )
    doc.add_paragraph(
        "本自動解析は入力された全記録を対象としており、個別の目視によるアーチファクト除去や、開眼・閉眼、覚醒度など記録条件の判定は行っていません。"
    )

    doc.add_heading("2. 主な定量所見", level=3)
    for band in ("theta","alpha","beta"):
        doc.add_paragraph(_band_finding(results, band))

    doc.add_heading("3. 前頭部左右差・比率", level=3)
    za=frontal["z_alpha_rel_diff"]
    if abs(za) >= 2.0:
        direction="右優位" if za > 0 else "左優位"
        doc.add_paragraph(f"前頭部α相対パワー左右差はZ={_zlabel(za)}で、正常参照群から2SD以上の偏位（{direction}）を認めます。")
    else:
        doc.add_paragraph(f"前頭部α相対パワー左右差はZ={_zlabel(za)}で、2SD以上の明らかな偏位を認めません。")

    doc.add_paragraph(
        f"β/θ比は左 {fmt3g(frontal['b1'])}（Z={_zlabel(frontal['zb1'])}）、"
        f"右 {fmt3g(frontal['b2'])}（Z={_zlabel(frontal['zb2'])}）です。"
    )
    zd=frontal["zbd"]
    if abs(zd) >= 2.0:
        direction="右高値" if zd > 0 else "左高値"
        doc.add_paragraph(f"β/θ比の左右差（右−左）はZ={_zlabel(zd)}で、正常参照群から2SD以上の偏位（{direction}）を認めます。")
    else:
        doc.add_paragraph(f"β/θ比の左右差（右−左）はZ={_zlabel(zd)}で、2SD以上の明らかな偏位を認めません。")

    doc.add_heading("4. Impression（まとめ）", level=3)
    doc.add_paragraph(_impression(results, frontal))

    add_arousal_profile(doc, results)

    doc.add_heading("6. Clinical correlation / 注意事項", level=3)
    doc.add_paragraph(
        "本所見は定量脳波解析に基づく記述的所見であり、単独で疾患の診断、病因の推定、治療適応の決定を行うものではありません。"
        "脳波は薬剤、覚醒状態、眼球運動、筋電、体動、電極・環境ノイズ等の影響を受けるため、通常脳波の視察所見、臨床症状、診察所見、他の検査結果と併せて医師が総合的に判断してください。"
    )
    doc.add_paragraph("医師確認：________________________________")

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
    add_interpretation_report(doc,results,frontal,sf)
    doc.save(output_path)
    return output_path
