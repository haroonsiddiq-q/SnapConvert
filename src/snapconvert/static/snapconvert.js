// ── Tool definitions ──────────────────────────────────────────────────────────
const MODELS = ['u2net', 'u2net_human_seg', 'isnet-general-use', 'birefnet-general', 'birefnet-portrait'];
const IMAGE_FORMATS = ['jpg', 'png', 'webp', 'avif'];
const VIDEO_FORMATS = ['mp4', 'webm', 'mov', 'gif'];

const TOOLS = {
  'image-remove-bg': {
    title: 'Remove Background', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '🖼',
    merged: true, // drives Single/Batch toggle
    endpointSingle: (p) => `/image/remove-bg?${p}`,
    endpointBatch: (p) => `/image/remove-bg/batch?${p}`,
    endpoint: (p) => `/image/remove-bg?${p}`, // default, overridden at runtime
    options: removeBgOptions(false),
  },
  'image-color-bg': {
    title: 'Color Background', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '🎨',
    endpoint: (p) => `/image/color-bg?${p}`,
    options: [...removeBgOptions(false), colorOption()],
  },
  'image-replace-bg': {
    title: 'Replace Background', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '🌄',
    needsBg: true,
    endpoint: (p) => `/image/replace-bg?${p}`,
    options: removeBgOptions(false),
  },
  'video-remove-bg': {
    title: 'Remove Background', sub: '— Video',
    accept: 'video/*', dropSub: 'MP4, MOV, AVI, WEBM', dropIcon: '🎬',
    endpoint: (p) => `/video/remove-bg?${p}`,
    options: removeBgOptions(true),
  },
  'video-color-bg': {
    title: 'Color Background', sub: '— Video',
    accept: 'video/*', dropSub: 'MP4, MOV, AVI, WEBM', dropIcon: '🎨',
    endpoint: (p) => `/video/color-bg?${p}`,
    options: [...removeBgOptions(true), colorOption()],
  },
  'video-replace-bg': {
    title: 'Replace Background', sub: '— Video',
    accept: 'video/*', dropSub: 'MP4, MOV, AVI, WEBM', dropIcon: '🌄',
    needsBg: true,
    endpoint: (p) => `/video/replace-bg?${p}`,
    options: removeBgOptions(true),
  },
  'image-convert': {
    title: 'Convert', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '🖼',
    endpoint: (p) => `/image/convert?${p}`,
    options: imageConvertOptions(),
  },
  'video-convert': {
    title: 'Convert', sub: '— Video',
    accept: 'video/*', dropSub: 'MP4, MOV, AVI, WEBM', dropIcon: '🎬',
    endpoint: (p) => `/video/convert?${p}`,
    options: videoConvertOptions(),
  },
  'image-transform': {
    title: 'Transform', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '✂️',
    transform: true, // drives mode selector
    endpoint: (p) => `/image/crop?${p}`, // default, overridden at runtime
    options: [],
  },
  'image-filters': {
    title: 'Filters', sub: '— Image',
    accept: 'image/*', dropSub: 'PNG, JPG, WEBP, AVIF', dropIcon: '🎚️',
    endpoint: (p) => `/image/filters?${p}`,
    options: imageFiltersOptions(),
  },
};

// ── Option builders ───────────────────────────────────────────────────────────
function removeBgOptions(isVideo) {
  return [
    { type: 'select', id: 'model', label: 'Model', options: MODELS, default: 'u2net' },
    { type: 'checkbox', id: 'alpha_matting', label: 'Alpha matting', default: false, triggersPanel: 'alphaPanel' },
    {
      type: 'panel', id: 'alphaPanel', fields: [
        { type: 'slider', id: 'alpha_matting_foreground_threshold', label: 'Foreground threshold', min: 0, max: 255, default: 240 },
        { type: 'slider', id: 'alpha_matting_background_threshold', label: 'Background threshold', min: 0, max: 255, default: 10 },
        { type: 'slider', id: 'alpha_matting_erode_size', label: 'Erode size', min: 0, max: 40, default: 10 },
      ]
    },
  ];
}

function colorOption() {
  return { type: 'color', id: 'color', label: 'Background color', default: '#ffffff' };
}

function imageConvertOptions() {
  return [
    { type: 'select', id: 'output_format', label: 'Output format', options: IMAGE_FORMATS, default: 'png' },
    { type: 'slider', id: 'quality', label: 'Quality (JPEG / WEBP / AVIF)', min: 1, max: 95, default: 85 },
    {
      type: 'row', fields: [
        { type: 'number', id: 'width', label: 'Width (px)', placeholder: 'e.g. 1920' },
        { type: 'number', id: 'height', label: 'Height (px)', placeholder: 'e.g. 1080' },
      ]
    },
    { type: 'number', id: 'scale', label: 'Scale (%)', placeholder: 'e.g. 50  (overrides width/height)' },
  ];
}

function videoConvertOptions() {
  return [
    { type: 'select', id: 'output_format', label: 'Output format', options: VIDEO_FORMATS, default: 'mp4' },
    { type: 'slider', id: 'crf', label: 'Quality (CRF, lower = better, ignored for GIF)', min: 0, max: 51, default: 23 },
    {
      type: 'row', fields: [
        { type: 'text', id: 'start_time', label: 'Start time', placeholder: 'e.g. 0:10' },
        { type: 'text', id: 'end_time', label: 'End time', placeholder: 'e.g. 0:30' },
      ]
    },
  ];
}

function imageCropOptions() {
  return [
    {
      type: 'row', fields: [
        { type: 'number', id: 'x', label: 'X (left edge)', placeholder: 'e.g. 0', required: true },
        { type: 'number', id: 'y', label: 'Y (top edge)', placeholder: 'e.g. 0', required: true },
      ]
    },
    {
      type: 'row', fields: [
        { type: 'number', id: 'width', label: 'Width (px)', placeholder: 'e.g. 800', required: true },
        { type: 'number', id: 'height', label: 'Height (px)', placeholder: 'e.g. 600', required: true },
      ]
    },
  ];
}

function imageCropSmartOptions() {
  return [
    { type: 'select', id: 'model', label: 'Model', options: MODELS, default: 'u2net' },
    { type: 'slider', id: 'padding', label: 'Padding (px)', min: 0, max: 100, default: 10 },
  ];
}

function imageRotateOptions() {
  return [
    { type: 'slider', id: 'degrees', label: 'Degrees (counter-clockwise)', min: -180, max: 180, default: 90 },
    { type: 'checkbox', id: 'expand', label: 'Expand canvas to fit', default: true },
  ];
}

function imageFlipOptions() {
  return [
    { type: 'select', id: 'direction', label: 'Direction', options: ['horizontal', 'vertical'], default: 'horizontal' },
  ];
}

function imageFiltersOptions() {
  return [
    { type: 'slider', id: 'brightness', label: 'Brightness', min: 0, max: 3, step: 0.05, default: 1 },
    { type: 'slider', id: 'contrast', label: 'Contrast', min: 0, max: 3, step: 0.05, default: 1 },
    { type: 'slider', id: 'saturation', label: 'Saturation', min: 0, max: 3, step: 0.05, default: 1 },
    { type: 'slider', id: 'sharpness', label: 'Sharpness', min: 0, max: 3, step: 0.05, default: 1 },
  ];
}

function imageFiltersOptions() {
  return [
    { type: 'slider', id: 'brightness', label: 'Brightness', min: 0, max: 2, step: 0.05, default: 1 },
    { type: 'slider', id: 'contrast', label: 'Contrast', min: 0, max: 2, step: 0.05, default: 1 },
    { type: 'slider', id: 'saturation', label: 'Saturation', min: 0, max: 2, step: 0.05, default: 1 },
    { type: 'slider', id: 'sharpness', label: 'Sharpness', min: 0, max: 2, step: 0.05, default: 1 },
  ];
}

// ── Render options ────────────────────────────────────────────────────────────
function renderOptions(options) {
  const container = document.getElementById('toolOptions');
  container.innerHTML = '';

  for (const opt of options) {
    if (opt.type === 'select') {
      container.appendChild(makeSelect(opt));
    } else if (opt.type === 'checkbox') {
      container.appendChild(makeCheckbox(opt));
    } else if (opt.type === 'slider') {
      container.appendChild(makeSlider(opt));
    } else if (opt.type === 'number') {
      container.appendChild(makeNumber(opt));
    } else if (opt.type === 'text') {
      container.appendChild(makeText(opt));
    } else if (opt.type === 'color') {
      container.appendChild(makeColor(opt));
    } else if (opt.type === 'panel') {
      container.appendChild(makePanel(opt));
    } else if (opt.type === 'row') {
      container.appendChild(makeRow(opt));
    }
  }
}

function makeSelect(opt) {
  const wrap = el('div', 'field');
  wrap.innerHTML = `<label>${opt.label}</label>`;
  const sel = el('select', '');
  sel.id = opt.id;
  opt.options.forEach(o => { const op = document.createElement('option'); op.value = o; op.textContent = o; if (o === opt.default) op.selected = true; sel.appendChild(op); });
  wrap.appendChild(sel);
  return wrap;
}

function makeCheckbox(opt) {
  const wrap = el('div', 'field');
  const label = el('label', 'check-row');
  const cb = document.createElement('input');
  cb.type = 'checkbox'; cb.id = opt.id; cb.checked = opt.default;
  label.appendChild(cb);
  const span = document.createElement('span');
  span.textContent = opt.label;
  label.appendChild(span);
  wrap.appendChild(label);

  if (opt.triggersPanel) {
    cb.addEventListener('change', () => {
      const panel = document.getElementById(opt.triggersPanel);
      if (panel) panel.classList.toggle('open', cb.checked);
    });
  }
  return wrap;
}

function makeSlider(opt) {
  const wrap = el('div', 'field');
  wrap.innerHTML = `<label>${opt.label}</label>`;
  const row = el('div', 'slider-row');
  const slider = document.createElement('input');
  slider.type = 'range'; slider.id = opt.id;
  slider.min = opt.min; slider.max = opt.max; slider.value = opt.default;
  slider.step = opt.step || 1;
  const val = el('span', 'slider-val');
  val.textContent = opt.default;
  slider.addEventListener('input', () => { val.textContent = slider.value; });
  row.appendChild(slider); row.appendChild(val);
  wrap.appendChild(row);
  return wrap;
}

function makeNumber(opt) {
  const wrap = el('div', 'field');
  wrap.innerHTML = `<label>${opt.label}${opt.required ? ' <span class="required-mark">*</span>' : ''}</label>`;
  const inp = document.createElement('input');
  inp.type = 'number'; inp.id = opt.id; inp.placeholder = opt.placeholder || '';
  wrap.appendChild(inp);
  return wrap;
}

function makeText(opt) {
  const wrap = el('div', 'field');
  wrap.innerHTML = `<label>${opt.label}</label>`;
  const inp = document.createElement('input');
  inp.type = 'text'; inp.id = opt.id; inp.placeholder = opt.placeholder || '';
  wrap.appendChild(inp);
  return wrap;
}

function makeColor(opt) {
  const wrap = el('div', 'field');
  wrap.innerHTML = `<label>${opt.label}</label>`;
  const row = el('div', 'color-row');
  const picker = document.createElement('input');
  picker.type = 'color'; picker.value = opt.default;
  const text = document.createElement('input');
  text.type = 'text'; text.id = opt.id; text.value = opt.default;
  picker.addEventListener('input', () => { text.value = picker.value; });
  text.addEventListener('input', () => { if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value; });
  row.appendChild(picker); row.appendChild(text);
  wrap.appendChild(row);
  return wrap;
}

function makePanel(opt) {
  const panel = el('div', 'alpha-panel');
  panel.id = opt.id;
  for (const f of opt.fields) {
    panel.appendChild(makeSlider(f));
  }
  // Open immediately if the linked checkbox is already checked
  requestAnimationFrame(() => {
    const cb = document.getElementById('alpha_matting');
    if (cb && cb.checked) panel.classList.add('open');
  });
  return panel;
}

function makeRow(opt) {
  const row = el('div', 'field-row');
  for (const f of opt.fields) {
    if (f.type === 'number') row.appendChild(makeNumber(f));
    else if (f.type === 'text') row.appendChild(makeText(f));
  }
  return row;
}

function el(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

// ── Tool switching ────────────────────────────────────────────────────────────
let currentTool = 'image-remove-bg';
let isBatchMode = false;
let transformMode = 'crop'; // crop | smart-crop | rotate | flip

const TRANSFORM_MODES = {
  'crop': { label: 'Crop', endpoint: (p) => `/image/crop?${p}`, options: imageCropOptions() },
  'smart-crop': { label: 'Smart Crop', endpoint: (p) => `/image/crop/smart?${p}`, options: imageCropSmartOptions() },
  'rotate': { label: 'Rotate', endpoint: (p) => `/image/rotate?${p}`, options: imageRotateOptions() },
  'flip': { label: 'Flip', endpoint: (p) => `/image/flip?${p}`, options: imageFlipOptions() },
};

function switchTool(toolId) {
  currentTool = toolId;
  const tool = TOOLS[toolId];

  // Sidebar active state
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`[data-tool="${toolId}"]`).classList.add('active');

  // Topbar
  document.getElementById('toolTitle').textContent = tool.title;
  document.getElementById('toolSub').textContent = tool.sub;

  // Drop zone
  document.getElementById('dropIcon').textContent = tool.dropIcon;
  document.getElementById('dropSub').textContent = tool.dropSub;
  const fi = document.getElementById('fileInput');
  fi.accept = tool.accept;
  fi.multiple = false;
  fi.value = '';
  document.getElementById('fileInfo').textContent = '';
  document.getElementById('fileInfo').classList.remove('visible');

  // BG upload
  document.getElementById('bgUpload').classList.toggle('visible', !!tool.needsBg);

  // Options
  const optEl = document.getElementById('toolOptions');
  optEl.innerHTML = '';

  // Merged tool: Single/Batch toggle
  if (tool.merged) {
    isBatchMode = false;
    const bar = document.createElement('div');
    bar.className = 'batch-toggle';
    ['Single', 'Batch'].forEach((label, i) => {
      const btn = document.createElement('button');
      btn.className = 'batch-btn' + (i === 0 ? ' active' : '');
      btn.textContent = label;
      btn.addEventListener('click', () => {
        isBatchMode = i === 1;
        fi.multiple = isBatchMode;
        fi.value = '';
        document.getElementById('fileInfo').textContent = '';
        document.getElementById('fileInfo').classList.remove('visible');
        document.getElementById('inputPreview').style.display = 'none';
        document.getElementById('inputPreview').innerHTML = '';
        bar.querySelectorAll('.batch-btn').forEach((b, j) => b.classList.toggle('active', j === i));
      });
      bar.appendChild(btn);
    });
    optEl.appendChild(bar);
  }

  // Transform tool: mode selector
  if (tool.transform) {
    const sel = document.createElement('div');
    sel.className = 'mode-selector';
    Object.entries(TRANSFORM_MODES).forEach(([key, cfg]) => {
      const btn = document.createElement('button');
      btn.className = 'mode-btn' + (key === transformMode ? ' active' : '');
      btn.textContent = cfg.label;
      btn.addEventListener('click', () => {
        transformMode = key;
        sel.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Re-render only the dynamic options below the mode selector
        renderTransformOptions(optEl, sel);
      });
      sel.appendChild(btn);
    });
    optEl.appendChild(sel);
    renderTransformOptions(optEl, sel);
  } else {
    renderOptions(tool.options);
  }
}

function renderTransformOptions(container, selectorEl) {
  // Remove any previously rendered transform options (everything after the selector)
  while (container.lastChild && container.lastChild !== selectorEl) {
    container.removeChild(container.lastChild);
  }
  const opts = TRANSFORM_MODES[transformMode].options;
  for (const opt of opts) {
    if (opt.type === 'select') container.appendChild(makeSelect(opt));
    else if (opt.type === 'slider') container.appendChild(makeSlider(opt));
    else if (opt.type === 'checkbox') container.appendChild(makeCheckbox(opt));
    else if (opt.type === 'row') container.appendChild(makeRow(opt));
  }
}

// ── File handling ─────────────────────────────────────────────────────────────
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');

function wireDropzone(zoneEl, inputEl, infoEl) {
  zoneEl.addEventListener('dragover', e => { e.preventDefault(); zoneEl.classList.add('drag-over'); });
  zoneEl.addEventListener('dragleave', () => zoneEl.classList.remove('drag-over'));
  zoneEl.addEventListener('drop', e => {
    e.preventDefault(); zoneEl.classList.remove('drag-over');
    if (e.dataTransfer.files.length) { inputEl.files = e.dataTransfer.files; showFileInfo(infoEl, inputEl.files); }
  });
  inputEl.addEventListener('change', () => {
    if (inputEl.files.length) {
      showFileInfo(infoEl, inputEl.files);
      // Show input preview for main dropzone only
      if (inputEl === fileInput) showInputPreview(inputEl.files);
    }
  });
}

wireDropzone(dropzone, fileInput, fileInfo);

const bgDropzone = document.getElementById('bgDropzone');
const bgFileInput = document.getElementById('bgFileInput');
const bgFileInfo = document.getElementById('bgFileInfo');
wireDropzone(bgDropzone, bgFileInput, bgFileInfo);

function showFileInfo(infoEl, files) {
  if (files.length === 1) {
    infoEl.textContent = `${files[0].name}  (${formatBytes(files[0].size)})`;
  } else {
    infoEl.textContent = `${files.length} files selected`;
  }
  infoEl.classList.add('visible');
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

function showInputPreview(files) {
  const el = document.getElementById('inputPreview');
  el.innerHTML = '';
  el.style.display = 'flex';
  hasInputPreview = true;

  const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
  const videoFiles = Array.from(files).filter(f => f.type.startsWith('video/'));

  if (imageFiles.length === 1 && files.length === 1) {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(imageFiles[0]);
    el.appendChild(img);
  } else if (videoFiles.length === 1 && files.length === 1) {
    const video = document.createElement('video');
    video.src = URL.createObjectURL(videoFiles[0]);
    video.controls = true;
    el.appendChild(video);
  } else if (imageFiles.length > 1) {
    const grid = document.createElement('div');
    grid.className = 'input-preview-grid';
    imageFiles.forEach(f => {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(f);
      grid.appendChild(img);
    });
    el.appendChild(grid);
  }
}

// ── Collect params ────────────────────────────────────────────────────────────
function collectParams() {
  const params = new URLSearchParams();
  const tool = TOOLS[currentTool];
  let missingField = null;

  const opts = tool.transform
    ? TRANSFORM_MODES[transformMode].options
    : tool.options;

  function collectFrom(options) {
    for (const opt of options) {
      if (opt.type === 'panel') { collectFrom(opt.fields); continue; }
      if (opt.type === 'row') { collectFrom(opt.fields); continue; }

      const el = document.getElementById(opt.id);
      if (!el) continue;

      if (opt.type === 'checkbox') {
        params.set(opt.id, el.checked);
      } else {
        const v = el.value.trim();
        if (v !== '') {
          params.set(opt.id, v);
        } else if (opt.required) {
          missingField = opt.label;
        }
      }
    }
  }
  collectFrom(opts);
  return { params, missingField };
}

// ── Process ───────────────────────────────────────────────────────────────────
document.getElementById('btnProcess').addEventListener('click', async () => {
  const tool = TOOLS[currentTool];
  const files = fileInput.files;

  if (!files.length) { showError('Please select a file first.'); return; }

  const { params, missingField } = collectParams();
  if (missingField) { showError(`Please fill in: ${missingField}`); return; }

  // Resolve endpoint — merged (remove-bg single/batch) or transform (mode-based)
  let endpoint;
  if (tool.merged) {
    endpoint = isBatchMode
      ? tool.endpointBatch(params.toString())
      : tool.endpointSingle(params.toString());
  } else if (tool.transform) {
    endpoint = TRANSFORM_MODES[transformMode].endpoint(params.toString());
  } else {
    endpoint = tool.endpoint(params.toString());
  }

  const formData = new FormData();
  if (isBatchMode && tool.merged) {
    Array.from(files).forEach(f => formData.append('files', f));
  } else {
    formData.append('file', files[0]);
  }

  if (tool.needsBg) {
    const bgFile = document.getElementById('bgFileInput').files[0];
    if (!bgFile) { showError('Please select a background image.'); return; }
    formData.append('background', bgFile);
  }

  showProcessing();

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      showError(err.detail || 'Something went wrong.');
      return;
    }

    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename=(.+)/);
    const filename = match ? match[1].replace(/['"]/g, '') : 'result';

    showResult(blob, filename);
  } catch (e) {
    showError('Could not reach the server. Is SnapConvert running?');
  }
});

// ── Result helpers ────────────────────────────────────────────────────────────
let resultURL = null;
let hasInputPreview = false;

function showProcessing() {
  const s = document.getElementById('status');
  s.textContent = '⏳ Processing… this may take a moment for video.';
  s.className = 'status visible processing';
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('resultPlaceholder').style.display = 'none';
  document.getElementById('btnProcess').disabled = true;
}

function showError(msg) {
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('resultPlaceholder').style.display = 'none';
  const s = document.getElementById('status');
  s.textContent = `🚨 ${msg}`;
  s.className = 'status visible error';
  document.getElementById('btnProcess').disabled = false;
}

function showResult(blob, filename) {
  document.getElementById('status').className = 'status';
  document.getElementById('btnProcess').disabled = false;
  document.getElementById('resultPlaceholder').style.display = 'none';

  if (resultURL) URL.revokeObjectURL(resultURL);
  resultURL = URL.createObjectURL(blob);

  const preview = document.getElementById('resultPreview');
  preview.innerHTML = '';

  if (blob.type.startsWith('image/')) {
    const img = document.createElement('img');
    img.src = resultURL;
    preview.appendChild(img);
  } else if (blob.type.startsWith('video/')) {
    const video = document.createElement('video');
    video.src = resultURL; video.controls = true; video.autoplay = false;
    preview.appendChild(video);
  } else if (blob.type === 'application/zip') {
    preview.innerHTML = `<div style="padding:32px;text-align:center;color:var(--text-2)"><div style="font-size:40px;margin-bottom:10px">📦</div><div style="font-size:13px">Batch complete — ${filename}</div></div>`;
  } else {
    preview.innerHTML = `<div style="padding:20px;color:var(--text-2)">📦 File ready to download</div>`;
  }

  document.getElementById('resultFilename').textContent = filename;

  const btn = document.getElementById('btnDownload');
  btn.onclick = () => {
    const a = document.createElement('a');
    a.href = resultURL; a.download = filename; a.click();
  };

  document.getElementById('resultArea').classList.add('visible');

  // Before/After toggle — only when there's an input preview to compare
  const inputPreview = document.getElementById('inputPreview');
  const bar = document.getElementById('beforeAfterBar');
  const btnBefore = document.getElementById('btnBefore');
  const btnAfter = document.getElementById('btnAfter');

  if (hasInputPreview) {
    bar.classList.add('visible');
    // Restore input preview content visibility, default to After view
    inputPreview.style.display = 'none';
    document.getElementById('resultArea').classList.add('visible');
    btnAfter.classList.add('active'); btnBefore.classList.remove('active');

    btnBefore.onclick = () => {
      inputPreview.style.display = 'flex';
      document.getElementById('resultArea').classList.remove('visible');
      btnBefore.classList.add('active'); btnAfter.classList.remove('active');
    };
    btnAfter.onclick = () => {
      inputPreview.style.display = 'none';
      document.getElementById('resultArea').classList.add('visible');
      btnAfter.classList.add('active'); btnBefore.classList.remove('active');
    };
  } else {
    bar.classList.remove('visible');
  }
}

function clearResult() {
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('resultPlaceholder').style.display = '';
  document.getElementById('status').className = 'status';
  document.getElementById('beforeAfterBar').classList.remove('visible');
  const ip = document.getElementById('inputPreview');
  ip.style.display = 'none';
  ip.innerHTML = '';
  hasInputPreview = false;
}

// ── Theme toggle ──────────────────────────────────────────────────────────────
document.getElementById('themeToggle').addEventListener('change', function () {
  document.documentElement.setAttribute('data-theme', this.checked ? 'dark' : 'light');
});

// ── Nav ───────────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => switchTool(item.dataset.tool));
});

// ── Init ──────────────────────────────────────────────────────────────────────
switchTool('image-remove-bg');
