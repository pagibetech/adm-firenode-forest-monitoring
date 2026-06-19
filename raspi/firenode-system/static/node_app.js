let currentConfig = {};
let currentLocal = null;
let refreshTimer = null;

function $(id) { return document.getElementById(id); }

function safe(v, fallback) {
  if (fallback === undefined) fallback = 'N/A';
  return (v === undefined || v === null || v === '') ? fallback : v;
}

function setClass(el, base, cls) {
  if (!el) return;
  el.className = base + (cls ? ' ' + cls : '');
}

async function api(url, options) {
  if (options === undefined) options = {};
  var res = await fetch(url, options);
  var text = await res.text();
  var data = {};
  try { data = JSON.parse(text); } catch (e) { data = { ok: false, error: text || res.statusText }; }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function updateHeader(status) {
  currentConfig = status.config || {};
  var el = $('smokeThresholdInput'); if (el) { el.value = currentConfig.smoke_threshold ?? 500; }
  currentLocal = status.local || {};
  var local = currentLocal;
  var network = status.network || {};

  $('nodeName').textContent = safe(local.node_name || network.node_name);
  $('baseUrl').textContent = local.base_url || 'Web GUI';

  var roleText = 'NODE';
  if (status.config && status.config.role) {
    var r = String(status.config.role).toUpperCase().replace('_', ' ');
    roleText = r;
  }
  $('roleBadge').textContent = 'Role: ' + roleText + ' | LIVE';
  setClass($('roleBadge'), 'badge', 'blue');
  $('ipBadge').textContent = 'IP: ' + safe(local.rpi_ip || network.rpi_ip);

  var localSerial = status.local_serial || {};
  var espText;
  if (local.esp32_ok) {
    if (localSerial.enabled && localSerial.connected) {
      espText = 'ESP32: ' + (local.esp32_ip || 'Serial') + ' (Serial)';
    } else {
      espText = 'ESP32: ' + local.esp32_ip;
    }
    setClass($('esp32Badge'), 'pill', 'green');
  } else if (localSerial.enabled) {
    espText = 'ESP32: Waiting for USB data';
    setClass($('esp32Badge'), 'pill', 'warn');
  } else {
    espText = 'ESP32: ' + (local.esp32_error || 'not connected');
    setClass($('esp32Badge'), 'pill', 'warn');
  }
  $('esp32Badge').textContent = espText;

  var cam = local.camera || {};
  var camLabel = safe(cam.camera_label, 'Camera');
  $('cameraBadge').textContent = cam.enabled ? camLabel + ': ' + safe(cam.camera_count, 0) : camLabel + ': OFF';
  setClass($('cameraBadge'), 'pill', cam.enabled ? 'green' : 'red');

  var ch = local.chainsaw || {};
  if (ch.confirmed_detection) {
    $('chainsawBadge').textContent = 'Chainsaw: DETECTED';
    setClass($('chainsawBadge'), 'pill', 'red');
  } else if (ch.running) {
    $('chainsawBadge').textContent = 'Chainsaw: ON';
    setClass($('chainsawBadge'), 'pill', 'green');
  } else {
    $('chainsawBadge').textContent = 'Chainsaw: OFF';
    setClass($('chainsawBadge'), 'pill', '');
  }
}

function renderLocalCamera(local) {
  var box = $('localVideo');
  box.innerHTML = '';
  var streams = [];
  if (Array.isArray(local.video_urls)) {
    streams = local.video_urls.filter(function(v) { return v && v.url; });
  }
  if (streams.length === 0 && local.video_url) {
    streams.push({ url: local.video_url, label: 'Camera', running: true });
  }
  if (streams.length === 0) {
    box.innerHTML = '<div class="video-card"><div class="video-box placeholder-box"><div><strong>No Camera Stream</strong><p>Camera may be disabled or not connected.</p></div></div></div>';
    return;
  }
  streams.forEach(function(s) {
    var cam = local.camera || {};
    var err = s.error ? '<div class="muted">' + s.error + '</div>' : '';
    var simBadge = local.operation_mode === 'simulation' ? '<span class="badge orange">SIMULATION</span>' : '';
    box.innerHTML += '<div class="video-card"><div class="video-title-row"><h3>' + safe(s.label) + '</h3>' + simBadge + '</div><div class="video-box"><img src="' + s.url + '" alt="Camera"></div>' + err + '</div>';
  });
}

function updateLocalSerial(localSerial) {
  if (!localSerial) localSerial = {};
  var enabled = localSerial.enabled;
  var connected = localSerial.connected;

  $('serialStatusCard').style.display = enabled ? '' : 'none';

  if (!enabled) return;

  $('serialPort').textContent = localSerial.port || '--';

  if (connected && localSerial.last_packet_time) {
    $('serialConnBadge').textContent = 'Connected';
    setClass($('serialConnBadge'), 'badge', 'green');
    $('serialStatus').textContent = 'Connected';
    $('serialLastPacket').textContent = localSerial.last_packet_time;
  } else if (connected) {
    $('serialConnBadge').textContent = 'Waiting for data';
    setClass($('serialConnBadge'), 'badge', 'warn');
    $('serialStatus').textContent = 'Connected (no packet yet)';
    $('serialLastPacket').textContent = '--';
  } else if (localSerial.error) {
    $('serialConnBadge').textContent = 'Error';
    setClass($('serialConnBadge'), 'badge', 'red');
    $('serialStatus').textContent = 'Error';
    $('serialLastPacket').textContent = '--';
  } else {
    $('serialConnBadge').textContent = 'Waiting for USB data';
    setClass($('serialConnBadge'), 'badge', 'warn');
    $('serialStatus').textContent = 'Waiting for USB data';
    $('serialLastPacket').textContent = '--';
  }

  if (localSerial.error) {
    $('serialErrorRow').style.display = '';
    $('serialError').textContent = localSerial.error;
  } else {
    $('serialErrorRow').style.display = 'none';
  }

  var nodeIds = localSerial.cache_keys || [];
  var pkts = localSerial.packets_by_node || {};
  $('serialNodeIds').textContent = nodeIds.length ? nodeIds.join(', ') : '--';
}

function renderLocalSensor(local, localSerial) {
  var box = $('localSensor');
  var s = local.sensor_summary || {};
  var ch = local.chainsaw || {};

  if (localSerial && localSerial.enabled && !local.esp32_ok) {
    var lines = [];
    lines.push({ label: 'Temperature', value: '--', cls: 'muted' });
    lines.push({ label: 'Humidity', value: '--', cls: 'muted' });
    lines.push({ label: 'Smoke', value: 'Waiting', cls: 'muted' });
    lines.push({ label: 'PIR Human', value: 'Waiting', cls: 'muted' });
    lines.push({ label: 'Battery', value: '--', cls: 'muted' });
    var html = '';
    lines.forEach(function(l) {
      html += '<div class="sensor-line"><span>' + l.label + '</span><strong>' + l.value + '</strong></div>';
    });
    box.innerHTML = html;
    return;
  }
  if (!local.esp32_ok && !local.esp32_error) {
    box.innerHTML = '<div class="muted">ESP32 not connected.</div>';
    return;
  }
  var lines = [];
  lines.push({ label: 'Temperature', value: safe(s.temperature) + ' °C' });
  lines.push({ label: 'Humidity', value: safe(s.humidity) + ' %' });
  lines.push({ label: 'Smoke', value: s.smoke_detected ? 'DETECTED' : 'Normal', alert: s.smoke_detected });
  lines.push({ label: 'PIR Human', value: s.human_detected ? 'Detected' : 'No motion', alert: s.human_detected });
  lines.push({ label: 'Battery', value: safe(s.battery_v) + ' V' });

  var html = '';
  lines.forEach(function(l) {
    html += '<div class="sensor-line"><span>' + l.label + '</span><strong class="' + (l.alert ? 'bad-text' : 'ok-text') + '">' + l.value + '</strong></div>';
  });
  box.innerHTML = html;
}

function updateChainsawDisplay(ch) {
  if (ch.confirmed_detection) {
    $('chainsawStatusBadge').textContent = 'DETECTED';
    $('chainsawStatusBadge').className = 'badge red';
  } else if (ch.running) {
    $('chainsawStatusBadge').textContent = 'Monitoring';
    $('chainsawStatusBadge').className = 'badge green';
  } else {
    $('chainsawStatusBadge').textContent = 'Stopped';
    $('chainsawStatusBadge').className = 'badge';
  }
  $('chStatus').textContent = ch.running ? (ch.confirmed_detection ? 'DETECTED' : 'Monitoring') : 'Stopped';
  $('chScore').textContent = safe(ch.score);
  $('chRms').textContent = safe(ch.rms);
  $('chAlerts').textContent = safe(ch.alerts_total, '0');

  if (ch.error) {
    $('chErrorRow').style.display = '';
    $('chError').textContent = ch.error;
  } else {
    $('chErrorRow').style.display = 'none';
  }
}

var audioPollTimer = null;

function updateAudioMonitor(ch, localSerial) {
  var box = $('audioMonitor');
  if (!box) return;

  var hasMic = (currentConfig.input_device !== undefined && currentConfig.input_device !== null && currentConfig.input_device !== '');
  var running = ch.running;

  if (!hasMic) {
    box.innerHTML = '<div class="muted">No audio input device selected. Use Refresh Device List below.</div>';
    return;
  }
  if (!running) {
    box.innerHTML = '<div class="muted">Mic available, detector stopped. Click Start Detection to monitor live audio.</div>';
    return;
  }

  if (ch.error) {
    box.innerHTML = '<div><span class="bad-text">Error: ' + ch.error + '</span></div>';
    return;
  }

  var rms = Number(ch.rms) || 0;
  var peak = Number(ch.peak) || 0;
  var rmsPct = Math.min(100, Math.round(rms * 2000));
  var peakPct = Math.min(100, Math.round(peak * 250));

  var wf = ch.waveform || [];
  var canvasId = 'audioWaveCanvas';
  var html = '';
  html += '<div class="audio-level-row"><span>RMS</span><div class="audio-bar-bg"><div class="audio-bar-fill" style="width:' + rmsPct + '%"></div></div><small style="font-size:10px;color:var(--muted)">' + rms.toFixed(4) + '</small></div>';
  html += '<div class="audio-level-row"><span>Peak</span><div class="audio-bar-bg"><div class="audio-bar-fill" style="width:' + peakPct + '%"></div></div><small style="font-size:10px;color:var(--muted)">' + peak.toFixed(4) + '</small></div>';
  html += '<canvas id="' + canvasId + '" class="audio-waveform"></canvas>';
  html += '<div class="audio-meta"><span>Score: ' + safe(ch.score) + (ch.sample_rate ? ' | ' + (ch.sample_rate / 1000).toFixed(1) + 'kHz' : '') + '</span><span>' + safe(ch.last_update, '--') + '</span></div>';
  box.innerHTML = html;

  var canvas = $(canvasId);
  if (canvas && wf.length > 0) {
    var ctx = canvas.getContext('2d');
    var cw = canvas.offsetWidth || canvas.parentElement.offsetWidth - 2;
    var ch = 56;
    canvas.width = cw;
    canvas.height = ch;
    ctx.clearRect(0, 0, cw, ch);
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    var mid = ch / 2;
    var scale = (ch - 4) / 2;
    for (var i = 0; i < wf.length; i++) {
      var x = (i / (wf.length - 1)) * cw;
      var y = mid - wf[i] * scale;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.strokeStyle = 'rgba(34,197,94,0.15)';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(cw, mid);
    ctx.stroke();
  }
}

function updateChainsawSettings(config) {
  $('chScoreThreshold').value = config.score_threshold !== undefined ? config.score_threshold : 60;
  $('chMinRms').value = config.min_rms !== undefined ? config.min_rms : 0.015;
  $('chRequireHits').value = config.require_hits !== undefined ? config.require_hits : 3;
  $('chCooldown').value = config.cooldown_sec !== undefined ? config.cooldown_sec : 30;
  $('browsePathInput').value = config.audio_browse_start_dir || 'test_audio';
}

function updateAlerts(alerts) {
  var tbody = $('alertRows');
  tbody.innerHTML = '';
  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No alerts logged yet.</td></tr>';
    return;
  }
  alerts.slice(0, 80).forEach(function(a) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + safe(a.timestamp) + '</td><td>' + safe(a.node_name) + '</td><td>' + safe(a.source) + '</td><td>' + safe(a.event_type) + '</td><td>' + safe(a.severity) + '</td><td>' + safe(a.message) + '</td>';
    tbody.appendChild(tr);
  });
}

async function refreshStatus() {
  try {
    var status = await api('/api/status');
    var localSerial = status.local_serial || {};
    updateHeader(status);
    updateLocalSerial(localSerial);
    currentLocal = status.local;
    renderLocalCamera(currentLocal);
    renderLocalSensor(currentLocal, localSerial);
    updateChainsawDisplay(currentLocal.chainsaw || {});
    updateChainsawSettings(status.config || {});
    updateAlerts(status.recent_alerts || []);

    var hasAlert = false;
    var s = currentLocal.sensor_summary || {};
    var ch = currentLocal.chainsaw || {};
    if (s.smoke_detected || s.human_detected || ch.confirmed_detection) {
      hasAlert = true;
    }
    $('healthBadge').textContent = hasAlert ? 'ALERT ACTIVE' : 'System Monitoring';
    $('healthBadge').className = 'badge ' + (hasAlert ? 'red' : 'green');

    updateAudioMonitor(ch, localSerial);
  } catch (e) {
    $('healthBadge').textContent = 'Dashboard Error';
    $('healthBadge').className = 'badge red';
  }
}

async function audioPoll() {
  try {
    var data = await api('/api/audio-monitor');
    var ch = {
      running: data.running,
      rms: data.rms,
      peak: data.peak,
      score: data.score,
      waveform: data.waveform,
      last_update: data.last_update,
      error: data.error,
      sample_rate: data.sample_rate
    };
    updateAudioMonitor(ch, {});
  } catch (e) {}
}

async function refreshNow() {
  await refreshStatus();
}

async function startDetector() {
  $('chStatus').textContent = 'Starting...';
  $('chainsawStatusBadge').textContent = 'Starting';
  $('chainsawStatusBadge').className = 'badge warn';
  try {
    var res = await api('/api/start', { method: 'POST' });
    if (!res.started && res.status && res.status.error) {
      $('chStatus').textContent = 'Stopped';
      $('chainsawStatusBadge').textContent = 'Error';
      $('chainsawStatusBadge').className = 'badge red';
      $('chErrorRow').style.display = '';
      $('chError').textContent = res.status.error;
      return;
    }
  } catch (e) {
    $('chStatus').textContent = 'Stopped';
    $('chainsawStatusBadge').textContent = 'Error';
    $('chainsawStatusBadge').className = 'badge red';
    $('chErrorRow').style.display = '';
    $('chError').textContent = 'Start failed: ' + e.message;
    return;
  }
  await refreshStatus();
  setTimeout(refreshStatus, 1500);
}

async function saveThreshold() {
  const payload = {
    smoke_threshold: Number($('smokeThresholdInput').value || 500)
  };
  try {
    await api('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    alert('Threshold saved.');
  } catch (e) {
    alert('Save failed: ' + e.message);
  }
}

async function stopDetector() {
  await api('/api/stop', { method: 'POST' });
  await refreshStatus();
}

async function saveChainSettings() {
  var payload = {
    score_threshold: Number($('chScoreThreshold').value || 60),
    min_rms: Number($('chMinRms').value || 0.015),
    require_hits: Number($('chRequireHits').value || 3),
    cooldown_sec: Number($('chCooldown').value || 30),
    audio_browse_start_dir: $('browsePathInput').value.trim() || 'test_audio'
  };
  try {
    await api('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    await refreshStatus();
  } catch (e) {
    alert('Save failed: ' + e.message);
  }
}

async function loadMicDevices() {
  var box = $('micDevices');
  box.innerHTML = '<div class="muted">Loading...</div>';
  try {
    var data = await api('/api/devices');
    if (!data.devices || data.devices.length === 0) {
      box.innerHTML = '<div class="muted">No audio input devices found.</div>';
      return;
    }
    var selectedDevice = (currentConfig.input_device !== undefined && currentConfig.input_device !== null && currentConfig.input_device !== '') ? Number(currentConfig.input_device) : null;
    box.innerHTML = '';
    data.devices.forEach(function(d) {
      var div = document.createElement('div');
      var isSelected = (selectedDevice !== null && Number(d.id) === selectedDevice);
      div.className = 'result-item' + (isSelected ? ' selected-device' : '');
      var label = '<div><strong>ID ' + d.id + (isSelected ? ' (selected)' : '') + '</strong><div class="meta">' + d.name + ' | ' + d.max_input_channels + ' ch | ' + Math.round(d.default_samplerate) + ' Hz</div></div>';
      var btn = isSelected ? '<span class="badge green">Active</span>' : '<button onclick="selectMicDevice(' + d.id + ')">Select</button>';
      div.innerHTML = label + btn;
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = '<div class="muted">Device list error: ' + e.message + '</div>';
  }
}

async function selectMicDevice(deviceId) {
  try {
    var payload = { input_device: Number(deviceId) };
    await api('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    currentConfig.input_device = Number(deviceId);
    await loadMicDevices();
  } catch (e) {
    alert('Device select failed: ' + e.message);
  }
}

async function browseAudio(path) {
  var box = $('audioBrowser');
  var target = path || $('browsePathInput').value.trim();
  if (!target) {
    box.innerHTML = '<div class="muted">Enter a folder path and click Open Folder, or use Included Test Audio.</div>';
    return;
  }
  box.innerHTML = '<div class="muted">Opening folder...</div>';
  try {
    var data = await api('/api/browse?path=' + encodeURIComponent(target));
    $('browsePathInput').value = data.path;
    box.innerHTML = '<div class="browser-path">' + data.path + '</div>';
    if (data.parent) {
      var row = document.createElement('div');
      row.className = 'dir-row';
      row.innerHTML = '<span>Up Parent</span><button>Open</button>';
      row.querySelector('button').onclick = function() { browseAudio(data.parent); };
      box.appendChild(row);
    }
    (data.shortcuts || []).forEach(function(s) {
      var r = document.createElement('div');
      r.className = 'dir-row';
      r.innerHTML = '<span>' + s.label + '</span><button>Open</button>';
      r.querySelector('button').onclick = function() { browseAudio(s.path); };
      box.appendChild(r);
    });
    (data.dirs || []).forEach(function(d) {
      var r = document.createElement('div');
      r.className = 'dir-row';
      r.innerHTML = '<span>' + d.name + '</span><button>Open</button>';
      r.querySelector('button').onclick = function() { browseAudio(d.path); };
      box.appendChild(r);
    });
    (data.files || []).forEach(function(f) {
      var r = document.createElement('div');
      r.className = 'file-row';
      r.innerHTML = '<span>' + f.name + ' <span class="muted">' + safe(f.size_mb) + ' MB</span></span><button>Analyze</button>';
      r.querySelector('button').onclick = function() { analyzeAudioFile(f.path); };
      box.appendChild(r);
    });
    if ((!data.dirs || !data.dirs.length) && (!data.files || !data.files.length)) {
      box.insertAdjacentHTML('beforeend', '<div class="muted">No supported audio files in this folder. Supported: WAV, MP3, M4A, AAC, FLAC, OGG.</div>');
    }
  } catch (e) {
    box.innerHTML = '<div class="browser-path">' + target + '</div><div class="muted">Browse error: ' + e.message + '</div>';
  }
}

async function analyzeAudioFile(path) {
  $('analysisResult').textContent = 'Analyzing ' + path + ' ...';
  try {
    var data = await api('/api/analyze-file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: path }) });
    $('analysisResult').textContent = JSON.stringify(data.result, null, 2);
    await refreshStatus();
  } catch (e) {
    $('analysisResult').textContent = 'Analyze error: ' + e.message;
  }
}

window.addEventListener('load', function() {
  refreshStatus();
  loadMicDevices();
  browseAudio('test_audio');
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshStatus, 3000);
  if (audioPollTimer) clearInterval(audioPollTimer);
  audioPollTimer = setInterval(audioPoll, 600);
});
