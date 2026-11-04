# Architecture

信号処理、Word生成、読影支援、UIを分離し、検証済みqEEG計算を壊さず拡張する。

- qeeg_core/parser.py: Neurofax .m00 入力
- qeeg_core/analysis.py: PSD / band power / relative power / Z-score
- qeeg_core/norms.py: 集約正常基準値
- qeeg_core/plots.py: topomap / PSD figure
- qeeg_core/report.py: legacy-compatible Word report
- qeeg_core/interpretation.py: 将来の読影レポート層
- app.py: ローカルWeb UI
- cli.py: 検証・バッチ用CLI

## Windowsアプリ化

最終版は127.0.0.1だけにbindするローカルUIをPyInstallerでEXE化する。院内PCではダブルクリック起動にする。

## 読影レポート拡張

信号処理結果を構造化し、ルールベースの記述的所見、医師編集UI、修正前後保存を追加する。十分な教師データ蓄積後にLightGBM/XGBoost等も検討する。
