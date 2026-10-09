脳画像の新しい勉強本 ver. — 個人T1 Tract × Segment Viewer

Base T1:
  VIEWER_ASSETS/base/subject_T1_synthseg_1mm.nii.gz

White-matter guidance:
  A2a FA-informed atlas deformation
  Standard JHU tract probability maps -> subject FA -> subject T1
  Resampled here onto the SynthSeg 1-mm subject grid.

ROI:
  SynthSeg parcellation from the same subject T1.
  CORE/LANDMARK relationships reuse the educational mapping from the existing uMRI tract viewer.

Important:
  Tract maps are educational guidance maps, not individual ground-truth tractography.
  CORE/LANDMARK relations are teaching aids, not exact tract termination ground truth.

Target public path:
  /tract-viewer/nougazounoatarashiibennkyoubonnver/
