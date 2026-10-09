#!/usr/bin/env python3
from pathlib import Path
import csv
import json
import shutil
import urllib.request
import zipfile

import numpy as np
import nibabel as nib
from nibabel.processing import resample_from_to
from skimage.measure import marching_cubes

BASE = Path("/workspace/A2a")
SUBJECT = BASE / "viewer_subject"
T1_PATH = SUBJECT / "subject_T1_synthseg_1mm.nii.gz"
SEG_PATH = SUBJECT / "subject_seg_parc_1mm.nii.gz"
TRACT_SRC_DIR = BASE / "batch_all" / "t1_final"

OUT = SUBJECT / "nougazounoatarashiibennkyoubonnver"
ASSET = OUT / "VIEWER_ASSETS"

RAW = "https://raw.githubusercontent.com/uMRI-web/uMRI-web.github.io/main/tract-viewer"
URLS = {
    "index.html": f"{RAW}/index.html",
    "app.js": f"{RAW}/app.js",
    "styles.css": f"{RAW}/styles.css",
    "tract_roi_map.json": f"{RAW}/VIEWER_ASSETS/metadata/tract_roi_map.json",
}

MIDLINE = {"Forceps_major", "Forceps_minor"}

def require(path: Path):
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")

def save_nifti(data, ref_img, path: Path, dtype):
    hdr = ref_img.header.copy()
    hdr.set_data_dtype(dtype)
    arr = np.asarray(data, dtype=dtype)
    out = nib.Nifti1Image(arr, ref_img.affine, hdr)
    out.set_qform(ref_img.affine, code=1)
    out.set_sform(ref_img.affine, code=1)
    nib.save(out, str(path))

def write_ascii_ply(path: Path, vertices, faces):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")
        for x, y, z in vertices:
            f.write(f"{x:.5f} {y:.5f} {z:.5f}\n")
        for a, b, c in faces:
            f.write(f"3 {int(a)} {int(b)} {int(c)}\n")

def mask_to_mesh(mask, affine, out_path: Path, step_size=1):
    if int(np.count_nonzero(mask)) == 0:
        raise RuntimeError(f"Cannot mesh empty mask: {out_path}")
    verts, faces, _, _ = marching_cubes(
        mask.astype(np.uint8),
        level=0.5,
        step_size=step_size,
        allow_degenerate=False,
    )
    verts_world = nib.affines.apply_affine(affine, verts)
    write_ascii_ply(out_path, verts_world, faces)

def main():
    for p in [T1_PATH, SEG_PATH, TRACT_SRC_DIR]:
        require(p)

    if OUT.exists():
        shutil.rmtree(OUT)

    dirs = [
        ASSET / "base",
        ASSET / "segmentation" / "master",
        ASSET / "segmentation" / "roi_masks",
        ASSET / "tracts" / "prob",
        ASSET / "tracts" / "mask_thr5",
        ASSET / "meshes" / "base",
        ASSET / "meshes" / "roi",
        ASSET / "meshes" / "tract",
        ASSET / "metadata",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print("[1/7] Downloading current viewer text template...")
    index_html = fetch_text(URLS["index.html"])
    app_js = fetch_text(URLS["app.js"])
    styles_css = fetch_text(URLS["styles.css"])
    roi_map = json.loads(fetch_text(URLS["tract_roi_map.json"]))

    index_html = index_html.replace(
        "<title>uMRI Tract × Segment Viewer</title>",
        "<title>脳画像の新しい勉強本 ver. — uMRI Tract Viewer</title>",
    )
    index_html = index_html.replace(
        "<h1>Tract × Segment Viewer</h1>",
        "<h1>脳画像の新しい勉強本 ver.</h1>",
    )
    index_html = index_html.replace(
        "<p>標準脳上で白質路と関連領域を同時表示</p>",
        "<p>個人T1上でFA-informed白質路と関連領域を同時表示</p>",
    )
    index_html = index_html.replace(
        "標準脳atlas上の概略表示です。CORE / LANDMARK は「このtractを理解するために一緒に見る領域」で、厳密な線維終末を意味しません。",
        "個人T1上の教育用表示です。白質路はFA-informed atlas deformationによるガイドであり、個人の真のtractographyを意味しません。CORE / LANDMARK は「このtractを理解するために一緒に見る領域」で、厳密な線維終末を意味しません。",
    )

    old_mid_prob = "$" + "{tract}_prob_MNI.nii.gz"
    new_mid_prob = "$" + "{tract}_prob_subject.nii.gz"
    old_side_prob = "$" + "{tract}_$" + "{side}_prob_MNI.nii.gz"
    new_side_prob = "$" + "{tract}_$" + "{side}_prob_subject.nii.gz"
    old_mid_mesh = "$" + "{tract}_thr5_MNI.ply"
    new_mid_mesh = "$" + "{tract}_thr5_subject.ply"
    old_side_mesh = "$" + "{tract}_$" + "{side}_thr5_MNI.ply"
    new_side_mesh = "$" + "{tract}_$" + "{side}_thr5_subject.ply"

    app_js = app_js.replace("MNI152_T1_1mm.nii.gz", "subject_T1_synthseg_1mm.nii.gz")
    app_js = app_js.replace(old_mid_prob, new_mid_prob)
    app_js = app_js.replace(old_side_prob, new_side_prob)
    app_js = app_js.replace(old_mid_mesh, new_mid_mesh)
    app_js = app_js.replace(old_side_mesh, new_side_mesh)
    app_js = app_js.replace("MNI_glassbrain_shell.ply", "subject_glassbrain_shell.ply")

    roi_map.setdefault("_meta", {})
    roi_map["_meta"]["purpose"] = "Subject-specific educational viewer using FA-informed atlas deformation."
    roi_map["_meta"]["warning"] = (
        "Tract maps are educational FA-informed atlas-deformation guides, not individual ground-truth tractography. "
        "CORE/LANDMARK relations are teaching aids, not exact tract termination ground truth."
    )
    roi_map["_meta"]["master_segmentation"] = "segmentation/master/subject_seg_parc_1mm.nii.gz"

    (OUT / "index.html").write_text(index_html, encoding="utf-8")
    (OUT / "app.js").write_text(app_js, encoding="utf-8")
    (OUT / "styles.css").write_text(styles_css, encoding="utf-8")
    (ASSET / "metadata" / "tract_roi_map.json").write_text(
        json.dumps(roi_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[2/7] Preparing subject T1 and master segmentation...")
    t1_img = nib.load(str(T1_PATH))
    seg_img = nib.load(str(SEG_PATH))
    seg_data = np.asarray(seg_img.dataobj)

    shutil.copy2(T1_PATH, ASSET / "base" / "subject_T1_synthseg_1mm.nii.gz")
    shutil.copy2(SEG_PATH, ASSET / "segmentation" / "master" / "subject_seg_parc_1mm.nii.gz")

    print("[3/7] Extracting exact CORE/LANDMARK ROI masks used by the current viewer...")
    unique_rois = {}
    for tract, tract_obj in roi_map.items():
        if tract.startswith("_"):
            continue
        for side in ("L", "R"):
            side_obj = tract_obj.get(side, {})
            for role in ("core", "landmark"):
                for item in side_obj.get(role, []):
                    unique_rois[item["mask_file"]] = {
                        "label_id": int(item["label_id"]),
                        "name": item["name"],
                    }

    roi_manifest = []
    for rel, item in sorted(unique_rois.items()):
        label = item["label_id"]
        mask = seg_data == label
        vox = int(mask.sum())
        if vox == 0:
            raise RuntimeError(f"ROI label {label} ({item['name']}) is empty in subject segmentation.")
        dst = ASSET / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        save_nifti(mask, seg_img, dst, np.uint8)

        ply_name = dst.name.replace(".nii.gz", ".ply")
        ply_path = ASSET / "meshes" / "roi" / ply_name
        mask_to_mesh(mask, seg_img.affine, ply_path, step_size=1)

        roi_manifest.append([label, item["name"], rel, vox])

    print(f"    ROI masks/meshes: {len(roi_manifest)}")

    print("[4/7] Resampling the 20 A2a tract probability maps onto the SynthSeg 1-mm subject grid...")
    tract_rows = []
    tract_keys = [k for k in roi_map.keys() if not k.startswith("_")]
    target = (t1_img.shape[:3], t1_img.affine)

    for tract in tract_keys:
        sides = ["M"] if tract in MIDLINE else ["L", "R"]
        for side in sides:
            if side == "M":
                src = TRACT_SRC_DIR / f"{tract}_prob_T1final.nii.gz"
                prob_name = f"{tract}_prob_subject.nii.gz"
                mask_name = f"{tract}_thr5_subject.nii.gz"
                mesh_name = f"{tract}_thr5_subject.ply"
            else:
                src = TRACT_SRC_DIR / f"{tract}_{side}_prob_T1final.nii.gz"
                prob_name = f"{tract}_{side}_prob_subject.nii.gz"
                mask_name = f"{tract}_{side}_thr5_subject.nii.gz"
                mesh_name = f"{tract}_{side}_thr5_subject.ply"

            require(src)
            src_img = nib.load(str(src))
            rs = resample_from_to(src_img, target, order=1)
            prob = np.asarray(rs.dataobj, dtype=np.float32)

            prob_path = ASSET / "tracts" / "prob" / prob_name
            save_nifti(prob, t1_img, prob_path, np.float32)

            mask = prob >= 5.0
            mask_path = ASSET / "tracts" / "mask_thr5" / mask_name
            save_nifti(mask, t1_img, mask_path, np.uint8)

            mesh_path = ASSET / "meshes" / "tract" / mesh_name
            mask_to_mesh(mask, t1_img.affine, mesh_path, step_size=1)

            tract_rows.append([
                tract, side, str(src), prob_name, mask_name,
                int(mask.sum()), float(np.nanmin(prob)), float(np.nanmax(prob))
            ])
            print(f"    {tract} {side}: vox={int(mask.sum())}")

    print("[5/7] Creating subject glass-brain mesh...")
    brain_mask = seg_data > 0
    mask_to_mesh(
        brain_mask,
        seg_img.affine,
        ASSET / "meshes" / "base" / "subject_glassbrain_shell.ply",
        step_size=2,
    )

    print("[6/7] Writing manifests and README...")
    with (ASSET / "metadata" / "subject_roi_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label_id", "name", "mask_file", "voxel_count"])
        w.writerows(roi_manifest)

    with (ASSET / "metadata" / "subject_tract_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "tract", "side", "source_T1final", "prob_subject", "thr5_subject",
            "thr5_voxel_count", "prob_min", "prob_max"
        ])
        w.writerows(tract_rows)

    readme = """脳画像の新しい勉強本 ver. — 個人T1 Tract × Segment Viewer

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
"""
    (OUT / "README_SUBJECT_VIEWER.txt").write_text(readme, encoding="utf-8")

    print("[7/7] Creating ready-to-upload ZIP...")
    zip_path = SUBJECT / "nougazounoatarashiibennkyoubonnver_READY.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in OUT.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(OUT.parent))

    manifest = {
        "output_folder": str(OUT),
        "zip": str(zip_path),
        "roi_count": len(roi_manifest),
        "tract_map_count": len(tract_rows),
        "target_url": "https://umri-web.github.io/tract-viewer/nougazounoatarashiibennkyoubonnver/",
    }
    (SUBJECT / "SUBJECT_VIEWER_BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("============================================================")
    print("SUBJECT VIEWER BUILD COMPLETE")
    print(f"Folder: {OUT}")
    print(f"ZIP:    {zip_path}")
    print(f"ROI:    {len(roi_manifest)}")
    print(f"Tracts: {len(tract_rows)}")
    print("============================================================")

if __name__ == "__main__":
    main()
