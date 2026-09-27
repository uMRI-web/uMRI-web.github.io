import { Niivue } from 'https://cdn.jsdelivr.net/npm/@niivue/niivue@0.69.0/+esm'

// -----------------------------------------------------------------------------
// Paths
// Keep VIEWER_ASSETS as a sibling directory inside this tract-viewer folder.
// Example: tract-viewer/VIEWER_ASSETS/base/MNI152_T1_1mm.nii.gz
// -----------------------------------------------------------------------------
const ASSET = './VIEWER_ASSETS'

const TRACT_LABELS = {
  CST: 'CST / 錐体路',
  ATR: 'ATR / 前視床放線',
  SLF: 'SLF / 上縦束',
  SLF_temporal: 'SLF temporal part',
  IFOF: 'IFOF / 下前頭後頭束',
  ILF: 'ILF / 下縦束',
  Uncinate: 'Uncinate / 鉤状束',
  Cingulum_cg: 'Cingulum (cingulate gyrus)',
  Cingulum_hipp: 'Cingulum (hippocampal part)',
  Forceps_major: 'Forceps major',
  Forceps_minor: 'Forceps minor',
}

const MIDLINE_TRACTS = new Set(['Forceps_major', 'Forceps_minor'])

const $ = (id) => document.getElementById(id)
const ui = {
  tract: $('tractSelect'),
  sideRow: $('sideRow'),
  sideButtons: [...document.querySelectorAll('[data-side]')],
  showTract: $('showTract'),
  showCore: $('showCore'),
  showLandmark: $('showLandmark'),
  showGlass: $('showGlass'),
  tractOpacity: $('tractOpacity'),
  roiOpacity: $('roiOpacity'),
  glassOpacity: $('glassOpacity'),
  tractOpacityOut: $('tractOpacityOut'),
  roiOpacityOut: $('roiOpacityOut'),
  glassOpacityOut: $('glassOpacityOut'),
  roiList: $('roiList'),
  status: $('status'),
  location: $('location'),
  loading: $('loading'),
  reset: $('resetView'),
}

let map = null
let currentSide = 'B'
let nv = null
let loadSerial = 0

function colorMap(R, G, B) {
  return { R: [0, R, R], G: [0, G, G], B: [0, B, B], A: [0, 0, 255], I: [0, 1, 255] }
}

function initViewer() {
  nv = new Niivue({
    backColor: [0.015, 0.02, 0.025, 1],
    crosshairColor: [0.2, 0.55, 1.0, 0.8],
    crosshairWidth: 1,
    show3Dcrosshair: true,
    isColorbar: false,
    meshThicknessOn2D: 0,
    onLocationChange: (data) => {
      if (data?.string) ui.location.textContent = data.string
    },
  })
  return nv.attachTo('gl').then(() => {
    nv.addColormap('tractL', colorMap(92, 120, 255))
    nv.addColormap('tractR', colorMap(70, 218, 126))
    nv.addColormap('coreROI', colorMap(255, 170, 76))
    nv.addColormap('landmarkROI', colorMap(80, 220, 235))

    nv.setCustomLayout([
      { sliceType: nv.sliceTypeAxial, position: [0.00, 0.00, 0.50, 0.50] },
      { sliceType: nv.sliceTypeSagittal, position: [0.50, 0.00, 0.50, 0.50] },
      { sliceType: nv.sliceTypeRender, position: [0.00, 0.50, 0.50, 0.50] },
      { sliceType: nv.sliceTypeCoronal, position: [0.50, 0.50, 0.50, 0.50] },
    ])
    nv.setMultiplanarPadPixels?.(2)
    nv.setAlphaClipDark?.(false)
  })
}

function niiToMesh(maskFile) {
  const name = maskFile.split('/').pop().replace(/\.nii\.gz$/i, '.ply')
  return `${ASSET}/meshes/roi/${name}`
}

function tractProbPath(tract, side) {
  if (MIDLINE_TRACTS.has(tract)) return `${ASSET}/tracts/prob/${tract}_prob_MNI.nii.gz`
  return `${ASSET}/tracts/prob/${tract}_${side}_prob_MNI.nii.gz`
}

function tractMeshPath(tract, side) {
  if (MIDLINE_TRACTS.has(tract)) return `${ASSET}/meshes/tract/${tract}_thr5_MNI.ply`
  return `${ASSET}/meshes/tract/${tract}_${side}_thr5_MNI.ply`
}

function sidesToUse(tract) {
  if (MIDLINE_TRACTS.has(tract)) return ['M']
  if (currentSide === 'B') return ['L', 'R']
  return [currentSide]
}

function uniqueRois(tract, role) {
  const sides = MIDLINE_TRACTS.has(tract) ? ['L', 'R'] : (currentSide === 'B' ? ['L', 'R'] : [currentSide])
  const seen = new Set()
  const out = []
  for (const side of sides) {
    const items = map?.[tract]?.[side]?.[role] || []
    for (const item of items) {
      const k = item.mask_file || `${item.label_id}`
      if (seen.has(k)) continue
      seen.add(k)
      out.push(item)
    }
  }
  return out
}

function prettyName(name) {
  return name
    .replace(/^ctx-[lr]h-/, '')
    .replace(/^Left-/, 'L ')
    .replace(/^Right-/, 'R ')
    .replaceAll('-', ' ')
}

function renderRoiList(tract) {
  const core = uniqueRois(tract, 'core')
  const lm = uniqueRois(tract, 'landmark')
  const group = (title, arr, cls) => {
    if (!arr.length) return ''
    return `<div class="roi-group-title">${title}</div>` + arr.map(x =>
      `<div class="roi-chip ${cls}"><span class="roi-dot"></span><span>${prettyName(x.name)}</span></div>`
    ).join('')
  }
  ui.roiList.innerHTML = group('CORE', core, 'core') + group('LANDMARK', lm, 'landmark') || '<span class="mini-label">関連ROIなし</span>'
}

function updateSideUI(tract) {
  const midline = MIDLINE_TRACTS.has(tract)
  ui.sideButtons.forEach(btn => {
    btn.disabled = midline
    btn.classList.toggle('active', !midline && btn.dataset.side === currentSide)
  })
  ui.sideRow.style.opacity = midline ? '0.45' : '1'
}

function volumeForRoi(item, role, opacity) {
  return {
    url: `${ASSET}/${item.mask_file}`,
    colormap: role === 'core' ? 'coreROI' : 'landmarkROI',
    opacity,
    cal_min: 0.5,
    cal_max: 1.0,
    visible: true,
  }
}

function meshForRoi(item, role, opacity) {
  const rgba255 = role === 'core' ? [255, 170, 76, 255] : [80, 220, 235, 255]
  return {
    url: niiToMesh(item.mask_file),
    rgba255,
    opacity: Math.min(1, opacity + 0.15),
    visible: true,
  }
}

async function loadSelection() {
  const serial = ++loadSerial
  const tract = ui.tract.value
  if (!tract) return

  ui.loading.classList.remove('hidden')
  ui.status.textContent = `${TRACT_LABELS[tract] || tract} を読み込み中…`
  renderRoiList(tract)
  updateSideUI(tract)

  const tractOpacity = Number(ui.tractOpacity.value)
  const roiOpacity = Number(ui.roiOpacity.value)
  const glassOpacity = Number(ui.glassOpacity.value)

  const volumes = [{
    url: `${ASSET}/base/MNI152_T1_1mm.nii.gz`,
    colormap: 'gray',
    opacity: 1,
    visible: true,
  }]

  if (ui.showTract.checked) {
    for (const side of sidesToUse(tract)) {
      const cmap = side === 'R' ? 'tractR' : 'tractL'
      volumes.push({
        url: tractProbPath(tract, side),
        colormap: cmap,
        opacity: tractOpacity,
        cal_min: 5,
        cal_max: 100,
        visible: true,
      })
    }
  }

  const core = ui.showCore.checked ? uniqueRois(tract, 'core') : []
  const lm = ui.showLandmark.checked ? uniqueRois(tract, 'landmark') : []
  core.forEach(x => volumes.push(volumeForRoi(x, 'core', roiOpacity)))
  lm.forEach(x => volumes.push(volumeForRoi(x, 'landmark', roiOpacity)))

  const meshes = []
  if (ui.showGlass.checked) {
    meshes.push({
      url: `${ASSET}/meshes/base/MNI_glassbrain_shell.ply`,
      rgba255: [225, 230, 235, 255],
      opacity: glassOpacity,
      visible: true,
    })
  }

  if (ui.showTract.checked) {
    for (const side of sidesToUse(tract)) {
      const rgba255 = side === 'R' ? [70, 218, 126, 255] : [92, 120, 255, 255]
      meshes.push({
        url: tractMeshPath(tract, side),
        rgba255,
        opacity: Math.min(1, tractOpacity + 0.15),
        visible: true,
      })
    }
  }
  core.forEach(x => meshes.push(meshForRoi(x, 'core', roiOpacity)))
  lm.forEach(x => meshes.push(meshForRoi(x, 'landmark', roiOpacity)))

  try {
    const crosshair = nv.scene?.crosshairPos ? [...nv.scene.crosshairPos] : null
    await nv.loadVolumes(volumes)
    if (serial !== loadSerial) return
    await nv.loadMeshes(meshes)
    if (serial !== loadSerial) return
    nv.setAlphaClipDark?.(false)
    nv.setGamma?.(1.25)
    if (crosshair && nv.scene) nv.scene.crosshairPos = crosshair
    nv.drawScene?.()
    ui.status.textContent = `${TRACT_LABELS[tract] || tract} — ${currentSide === 'B' ? 'bilateral' : currentSide}`
  } catch (err) {
    console.error(err)
    ui.status.textContent = `読み込みエラー: ${err?.message || err}`
  } finally {
    if (serial === loadSerial) ui.loading.classList.add('hidden')
  }
}

function wireControls() {
  ui.tract.addEventListener('change', loadSelection)
  ui.sideButtons.forEach(btn => btn.addEventListener('click', () => {
    if (btn.disabled) return
    currentSide = btn.dataset.side
    ui.sideButtons.forEach(x => x.classList.toggle('active', x === btn))
    loadSelection()
  }))

  ;[ui.showTract, ui.showCore, ui.showLandmark, ui.showGlass].forEach(x => x.addEventListener('change', loadSelection))

  const sliders = [
    [ui.tractOpacity, ui.tractOpacityOut],
    [ui.roiOpacity, ui.roiOpacityOut],
    [ui.glassOpacity, ui.glassOpacityOut],
  ]
  sliders.forEach(([input, output]) => {
    input.addEventListener('input', () => { output.value = Number(input.value).toFixed(2) })
    input.addEventListener('change', loadSelection)
  })

  ui.reset.addEventListener('click', () => {
    nv.scene.pan2Dxyzmm = [0, 0, 0, 1]
    nv.scene.renderAzimuth = 110
    nv.scene.renderElevation = 15
    nv.drawScene?.()
  })
}

async function boot() {
  try {
    ui.loading.classList.remove('hidden')
    const res = await fetch(`${ASSET}/metadata/tract_roi_map.json`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`metadata HTTP ${res.status}`)
    map = await res.json()

    const tracts = Object.keys(map).filter(k => !k.startsWith('_'))
    ui.tract.innerHTML = tracts.map(k => `<option value="${k}">${TRACT_LABELS[k] || k}</option>`).join('')
    ui.tract.value = tracts.includes('CST') ? 'CST' : tracts[0]

    await initViewer()
    wireControls()
    await loadSelection()
  } catch (err) {
    console.error(err)
    ui.status.textContent = `初期化エラー: ${err?.message || err}`
  } finally {
    ui.loading.classList.add('hidden')
  }
}

boot()
