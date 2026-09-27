# uMRI Tract × Segment Viewer

GitHub Pages 上で、標準脳 T1、白質路 probability map、関連する CORE / LANDMARK ROI、3D glass brain を同時表示する教育用 viewer です。

## Public URL

`https://umri-web.github.io/tract-viewer/`

## Expected layout

```text
tract-viewer/
├─ index.html
├─ app.js
├─ styles.css
├─ README.md
└─ VIEWER_ASSETS/
   ├─ base/
   ├─ segmentation/
   ├─ tracts/
   ├─ meshes/
   └─ metadata/
```

The viewer reads `VIEWER_ASSETS/metadata/tract_roi_map.json` directly.

## Viewer behavior

- T1: `VIEWER_ASSETS/base/MNI152_T1_1mm.nii.gz`
- 2D tract overlay: `VIEWER_ASSETS/tracts/prob/`
- 3D tract mesh: `VIEWER_ASSETS/meshes/tract/`
- 2D ROI masks: `VIEWER_ASSETS/segmentation/roi_masks/`
- 3D ROI meshes: `VIEWER_ASSETS/meshes/roi/`
- glass brain: `VIEWER_ASSETS/meshes/base/MNI_glassbrain_shell.ply`
- tract ↔ ROI mapping: `VIEWER_ASSETS/metadata/tract_roi_map.json`

CORE / LANDMARK は教育用の表示関係であり、厳密な tract termination atlas を意味しません。

## Deferred EDU ROI

以下は後日追加予定です。

- corona radiata
- posterior limb of internal capsule
- cerebral peduncle
- pontine CST zone
- medullary pyramid
- 手描きの「だいたいこのへん」ROI / ランドマーク

## NiiVue

CDNから `@niivue/niivue@0.69.0` を固定バージョンで読み込みます。
