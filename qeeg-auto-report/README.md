# qEEG Auto Report (uMRI)

日本光電 Neurofax EEG-1200 / EEG-1290 から ASCII エクスポートした .m00 を読み込み、既存 qEEG 解析レポートと同じ構成の Word (.docx) を生成する試作版です。

## 現在の機能

- .m00 直接読み込み（500 Hz）
- 12電極: Fp1/Fp2/C3/C4/O1/O2/T3/T4/F7/F8/T5/T6
- Welch PSD (nperseg=2000, 4秒窓)
- theta 4-8 Hz / alpha 8-12 Hz / beta 12-30 Hz
- Simpson積分による帯域パワー
- theta+alpha+beta 合計で正規化した相対パワー
- 既存レポート互換 Z-score
- 前頭部 alpha 左右差、beta/theta 比、左右差と Z-score
- バグ修正版 qEEG トポグラフィー
- 12電極 PSD 図
- Word レポート出力

## 修正点

1. Fp1=左、Fp2=右として左右表記を修正。
2. トポグラフィーで alpha/beta/theta 各帯域の正しい Z-score を使用。

## 検証

94例の既存 .m00 + レポートペアで検証し、12電極×3帯域の3,384個のZ-score表示値と前頭部4種×94例のZ-score表示値が100%一致する集約基準値を使用しています。正常1297例の個票データは含みません。

## 重要

研究・検証用です。診断を自動確定する用途ではありません。患者データをGitHubへアップロードしないでください。

## 将来予定

Windows単体EXE、複数ファイル一括処理、読影レポート、医師修正保存、教師データ化。


## Browser version output formats

The GitHub Pages browser-local app supports:
- Word (.docx)
- PDF (.pdf; text remains selectable/searchable, figures embedded as images)
- Word + PDF together as a ZIP

All three formats are generated locally in the user's browser; the .m00 file is not uploaded to a server.
