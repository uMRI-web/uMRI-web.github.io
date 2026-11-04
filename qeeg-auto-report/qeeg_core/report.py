from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from docx import Document
from docx.shared import Inches

from .analysis import QEEGResult, ELECTRODES
from .plots import save_topomaps, save_psd_plots

JP_BAND = {"alpha": "アルファ", "beta": "ベータ", "theta": "シータ"}

def _fmt2(x: float) -> str:
    return str(round(float(x), 2))

def _fmt3g(x: float) -> str:
    return f"{float(x):.3g}"

def build_report(result: QEEGResult, output_path: str | Path, input_name: str = "", created_at: datetime | None = None) -> Path:
    output_path = Path(output_path)
    created_at = created_at or datetime.now()

    with TemporaryDirectory(prefix="qeeg_report_") as td:
        tdir = Path(td)
        topomaps = save_topomaps(result, tdir)
        psds = save_psd_plots(result, tdir)

        document = Document()
        document.add_heading("脳波の解析結果")
        document.add_paragraph(" ")
        document.add_paragraph("作成日：" + created_at.strftime("%Y年%m月%d日"))
        document.add_paragraph("ファイル名：" + result.source_filename)
        document.add_paragraph("インプット名：" + input_name)
        document.add_paragraph(" ")

        document.add_heading("脳波トポグラフィー", level=2)
        document.add_paragraph("各時刻、各電極計12箇所における脳波を周波数毎（シータ波・アルファ波・ベータ波として分類）に分析し、脳波トポグラフィーを描画します。")
        document.add_heading("シータ波の分布", level=3)
        document.add_picture(str(topomaps["theta"]), width=Inches(3.5))
        document.add_page_break()

        document.add_heading("アルファ波の分布", level=3)
        document.add_picture(str(topomaps["alpha"]), width=Inches(3.5))
        document.add_heading("ベータ波の分布", level=3)
        document.add_picture(str(topomaps["beta"]), width=Inches(3.5))
        document.add_page_break()

        document.add_heading("Zスコア（標準得点）の算出", level=2)
        document.add_paragraph("正常被験者1297人の脳波データを基準として入力ファイルのZスコアを算出します。")
        document.add_paragraph("Zスコアは、入力データと正常なデータ群の平均値との差を正常なデータ群の標準偏差で除したもので、入力データがどれだけ正常なデータから外れているかを示す指標の一つです。")
        document.add_paragraph("例えば、Z値が+1であるならデータセットの分布から標準偏差1つ分だけ外れている事を示します。")

        for e in ELECTRODES:
            for band in ("alpha", "beta", "theta"):
                z = result.electrodes[e].z[band]
                document.add_paragraph(f"{e}電極の{JP_BAND[band]}波の相対パワースペクトルのZスコアは{_fmt2(z)}です。")
            document.add_paragraph(" ")

        f = result.frontal
        document.add_heading("前頭葉の左右差の分析", level=2)
        document.add_paragraph("前頭葉のアルファ波の左右差やそのZスコア、前頭葉のベータ波とシータ波の比率やそのZスコアが様々な症例と相関性のある事が近年の論文によって示されています。")
        document.add_paragraph("前頭葉のアルファ波左右差の値は" + _fmt3g(f["alpha_abs_diff"]) + "です。")
        document.add_paragraph("前頭葉のアルファ波左右差の相対パワースペクトルのZスコアは" + _fmt3g(f["z_alpha_rel_diff"]) + "です。")
        document.add_paragraph("前頭葉（左）のベータ波/シータ波の比率は" + _fmt3g(f["beta_theta_fp1_left"]) + "です。")
        document.add_paragraph("前頭葉（右）のベータ波/シータ波の比率は" + _fmt3g(f["beta_theta_fp2_right"]) + "です。")
        document.add_paragraph("前頭葉（左）のベータ波/シータ波のZスコアは" + _fmt3g(f["z_beta_theta_fp1_left"]) + "です。")
        document.add_paragraph("前頭葉（右）のベータ波/シータ波のZスコアは" + _fmt3g(f["z_beta_theta_fp2_right"]) + "です。")
        document.add_paragraph("前頭葉のベータ波/シータ波の左右差（右−左）は" + _fmt3g(f["beta_theta_diff_right_minus_left"]) + "です。")
        document.add_paragraph("前頭葉のベータ波/シータ波の左右差（右−左）のZスコアは" + _fmt3g(f["z_beta_theta_diff_right_minus_left"]) + "です。")
        document.add_page_break()

        document.add_heading("パワースペクトル密度の周波数依存性", level=2)
        document.add_paragraph("周波数解析した各電極におけるパワースペクトル密度の周波数依存性を描画します。")
        document.add_paragraph("シータ波帯域が4~8 [Hz]、アルファ波帯域が8~12 [Hz]、ベータ波帯域が12~30 [Hz]となっています。")
        for e in ELECTRODES:
            document.add_picture(str(psds[e]), width=Inches(3.5))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(output_path)
    return output_path
