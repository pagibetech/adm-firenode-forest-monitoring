let currentConfig = {};
let currentLocal = null;
let allNodes = [];
let refreshTimer = null;
let lastVideoSignature = "";

function $(id) { return document.getElementById(id); }

function safe(v, fallback = '--') {
  return (v === undefined || v === null || v === '') ? fallback : v;
}

function boolVal(id) {
  return $(id).value === 'true';
}

function setClass(el, base, cls) {
  if (!el) return;
  el.className = base + (cls ? ' ' + cls : '');
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data = {};
  try { data = JSON.parse(text); } catch (e) { data = { ok: false, error: text || res.statusText }; }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function showTab(tabId) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
  const panel = $(tabId);
  if (panel) panel.classList.add('active');
  const btn = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
  if (btn) btn.classList.add('active');
}

function nodeTitle(n, index = 0) {
  return safe(n.node_name || n.rpi_ip || n.ip, 'Node ' + (index + 1));
}

function nodeOnline(n) {
  return n && n.online !== false;
}

function nodeHasAlert(n) {
  const s = n.sensor_summary || {};
  const c = n.chainsaw || {};
  const t = n.thermal || {};
  const td = t.detection || {};
  return Boolean(s.smoke_detected || s.human_detected || c.confirmed_detection);
}

function alertCount(nodes) {
  return (nodes || []).filter(nodeHasAlert).length;
}

function nodeStreams(n) {
  let streams = [];
  if (Array.isArray(n.video_urls)) {
    streams = n.video_urls.filter(v => v && (v.url || v.placeholder));
  }
  if (streams.length === 0 && n.video_url) {
    streams.push({ type: 'usb_camera', label: 'USB Camera', url: n.video_url, running: true });
  }
  if (n.thermal_url && !streams.some(s => s.url === n.thermal_url)) {
    const td = ((n.thermal || {}).detection || {});
    streams.push({ type: 'thermal', label: 'MLX90640 Thermal Camera', url: n.thermal_url, running: (n.thermal || {}).running, human_detected: td.human_detected });
  }
  return streams;
}

function updateSettingsFields(config) {
  if (!config || Object.keys(config).length === 0) return;
  $('roleSelect').value = config.role || 'server';
  $('operationModeInput').value = config.operation_mode || 'live';
  $('esp32IpInput').value = config.selected_esp32_ip || '';
  $('esp32PrefixInput').value = config.esp32_scan_prefix || 'auto';
  $('nodePrefixInput').value = config.node_scan_prefix || 'auto';
  $('serverRefreshInput').value = config.server_refresh_sec ?? 3;
  $('remoteIpsInput').value = (config.remote_node_ips || []).join('\n');

  $('cameraEnabledInput').value = String(config.camera_enabled !== false);
  $('camIndexesInput').value = (config.camera_device_indexes || [config.camera_device_index ?? 0]).join(',');
  $('camWidthInput').value = config.camera_width ?? 320;
  $('camHeightInput').value = config.camera_height ?? 240;
  $('camFpsInput').value = config.camera_fps ?? 10;
  $('camQualityInput').value = config.camera_jpeg_quality ?? 55;

  $('thermalEnabledInput').value = String(config.thermal_enabled !== false);
  $('thermalSimInput').value = String(config.thermal_simulation === true);
  $('thermalAddressInput').value = config.thermal_i2c_address || '0x33';
  $('thermalRefreshInput').value = String(config.thermal_refresh_rate_hz ?? 2);
  $('thermalDisplayMinInput').value = config.thermal_display_min_c ?? 20;
  $('thermalDisplayMaxInput').value = config.thermal_display_max_c ?? 45;
  $('thermalHumanMinInput').value = config.thermal_min_human_temp_c ?? 28;
  $('thermalHumanMaxInput').value = config.thermal_max_human_temp_c ?? 42;
  $('thermalDeltaInput').value = config.thermal_min_delta_above_ambient_c ?? 4;
  $('thermalBlobInput').value = config.thermal_min_blob_pixels ?? 5;
  $('thermalRotateInput').value = String(config.thermal_rotate_degrees ?? 0);
  const mx = Boolean(config.thermal_mirror_x);
  const my = Boolean(config.thermal_mirror_y);
  $('thermalMirrorInput').value = mx && my ? 'xy' : (mx ? 'x' : (my ? 'y' : 'none'));

  $('wifiSsidInput').value = config.wifi_ssid || '';
  $('wifiPasswordInput').value = config.wifi_password || '';
  $('wifiCountryInput').value = config.wifi_country || 'PH';
  $('wifiInterfaceInput').value = config.wifi_interface || 'wlan0';
  $('browsePathInput').value = config.audio_browse_start_dir || 'test_audio';
}

function updateHeader(status) {
  currentConfig = status.config || {};
  currentLocal = status.local || {};
  const local = currentLocal;
  const network = status.network || {};

  $('nodeName').textContent = safe(local.node_name || network.node_name);
  $('baseUrl').textContent = local.base_url || 'Web GUI';
  const opMode = safe(currentConfig.operation_mode, 'live').toUpperCase();
  $('roleBadge').textContent = 'Role: ' + safe(currentConfig.role, 'server').toUpperCase() + ' | ' + opMode;
  setClass($('roleBadge'), 'badge', currentConfig.role === 'server' ? 'orange' : 'blue');
  $('ipBadge').textContent = 'IP: ' + safe(local.rpi_ip || network.rpi_ip);

  const espText = local.esp32_ok ? `ESP32: ${local.esp32_ip}` : `ESP32: ${local.esp32_error || 'not connected'}`;
  $('esp32Badge').textContent = espText;
  setClass($('esp32Badge'), 'pill', local.esp32_ok ? 'green' : 'warn');
  $('esp32Status').textContent = local.esp32_ok ? local.esp32_ip : (local.esp32_error || 'Not connected');
  $('esp32Fetch').textContent = local.esp32_ok ? `Fetch: ${safe(local.esp32_elapsed_ms)} ms` : 'Fetch: failed';
  setClass($('esp32Fetch'), 'badge', local.esp32_ok ? 'green' : 'red');

  const cam = local.camera || {};
  const camLabel = safe(cam.camera_label, 'Camera');
  $('cameraBadge').textContent = cam.enabled ? `${camLabel}: ${safe(cam.camera_count, 0)}` : `${camLabel}: OFF`;
  setClass($('cameraBadge'), 'pill', cam.enabled ? 'green' : 'red');

  const th = local.thermal || {};
  const td = th.detection || {};
  $('thermalBadge').textContent = th.enabled ? (td.human_detected ? 'Thermal: HUMAN' : 'Thermal: ON') : 'Thermal: OFF';
  setClass($('thermalBadge'), 'pill', td.human_detected ? 'red' : (th.enabled ? 'green' : ''));
  $('thermalHumanVal').textContent = td.human_detected ? 'DETECTED' : (th.enabled ? 'No human' : 'Disabled');
  $('thermalHumanVal').className = 'value ' + (td.human_detected ? 'bad-text' : 'ok-text');
  $('thermalTempBadge').textContent = `Max: ${safe(td.max_temp_c)} °C | Ambient: ${safe(td.ambient_c)} °C`;
  setClass($('thermalTempBadge'), 'badge', td.human_detected ? 'red' : 'green');

  const ch = local.chainsaw || {};
  $('chainsawBadge').textContent = ch.running ? (ch.confirmed_detection ? 'Chainsaw: DETECTED' : 'Chainsaw: ON') : 'Chainsaw: OFF';
  setClass($('chainsawBadge'), 'pill', ch.confirmed_detection ? 'red' : (ch.running ? 'green' : ''));

  $('jsonBox').textContent = JSON.stringify(local, null, 2);
  updateSettingsFields(currentConfig);
}

function renderVideoCard(n, stream = {}, index) {
  const title = nodeTitle(n, index);
  const offline = !nodeOnline(n);
  const isThermal = stream.type === 'thermal';
  const isSim = Boolean(stream.simulation || n.simulation);
  const isPlaceholder = Boolean(stream.placeholder);
  const alert = isThermal && stream.human_detected;
  const label = safe(stream.label, isThermal ? 'Thermal' : 'Video');
  const badgeClass = isPlaceholder ? 'warn' : (isSim ? 'orange' : (isThermal ? 'orange' : 'blue'));

  if (isPlaceholder) {
    return `<div class="video-card placeholder-card ${offline ? 'offline' : ''}">
      <div class="video-title-row">
        <h3>${title}</h3>
        <span class="badge ${badgeClass}">${label}</span>
      </div>
      <div class="video-box placeholder-box">
        <div>
          <strong>Remote Video Placeholder</strong>
          <p>${safe(stream.message || n.error, 'Waiting for remote node stream.')}</p>
        </div>
      </div>
      <div class="muted">Slot ${safe(stream.slot || n.remote_slot)} of 3 ${n.rpi_ip ? '| ' + n.rpi_ip : ''}</div>
    </div>`;
  }

  if (offline) {
    return `<div class="video-card offline"><h3>${title}</h3><p class="muted">Offline: ${safe(n.error)}</p></div>`;
  }
  return `<div class="video-card ${alert ? 'alert-card' : ''} ${isSim ? 'simulation-card' : ''}">
    <div class="video-title-row">
      <h3>${title}</h3>
      <span class="badge ${badgeClass}">${label}</span>
    </div>
    <div class="video-box"><img src="${stream.url}" alt="${title} ${label}"></div>
    <div class="muted">${safe(n.base_url || n.url)} ${isSim ? '| Simulation stream' : ''} ${stream.error ? '| ' + stream.error : ''}</div>
  </div>`;
}

function renderAllVideos(nodes) {
  const signature = JSON.stringify((nodes || []).map((n, i) => ({
    node: nodeTitle(n, i),
    online: nodeOnline(n),
    streams: nodeStreams(n).map(s => [s.type, s.label, s.url, s.placeholder, s.message])
  })));
  if (signature === lastVideoSignature) return;
  lastVideoSignature = signature;
  const box = $('allVideos');
  box.innerHTML = '';
  if (!nodes || nodes.length === 0) {
    box.innerHTML = '<div class="muted">No nodes available yet.</div>';
    return;
  }
  nodes.forEach((n, i) => {
    const streams = nodeStreams(n);
    if (streams.length > 0) {
      streams.forEach(s => box.insertAdjacentHTML('beforeend', renderVideoCard(n, s, i)));
    } else if (!nodeOnline(n)) {
      box.insertAdjacentHTML('beforeend', renderVideoCard(n, {}, i));
    } else {
      box.insertAdjacentHTML('beforeend', `<div class="video-card"><h3>${nodeTitle(n, i)}</h3><p class="muted">No stream URL exposed by this node.</p></div>`);
    }
  });
}

function renderSensorCards(nodes) {
  const box = $('sensorCards');
  box.innerHTML = '';
  if (!nodes || nodes.length === 0) {
    box.innerHTML = '<div class="muted">No sensor data available yet.</div>';
    return;
  }
  nodes.forEach((n, i) => {
    const s = n.sensor_summary || {};
    const c = n.chainsaw || {};
    const t = n.thermal || {};
    const td = t.detection || {};
    const online = nodeOnline(n);
    const card = document.createElement('div');
    card.className = 'sensor-card' + (online ? '' : ' offline') + (nodeHasAlert(n) ? ' alert-card' : '');
    card.innerHTML = `<h3>${nodeTitle(n, i)}</h3>
      <div class="muted">${online ? safe(n.rpi_ip || n.ip) : 'Offline: ' + safe(n.error)}</div>
      <div class="sensor-line"><span>ESP32</span><strong>${n.esp32_ok ? safe(n.esp32_ip) : 'Not connected'}</strong></div>
      <div class="sensor-line"><span>Temp/Humidity</span><strong>${safe(s.temperature)} °C / ${safe(s.humidity)} %</strong></div>
      <div class="sensor-line"><span>Smoke</span><strong class="${s.smoke_detected ? 'bad-text' : 'ok-text'}">${s.smoke_detected ? 'DETECTED' : 'Normal'}</strong></div>
      <div class="sensor-line"><span>PIR Human</span><strong class="${s.human_detected ? 'bad-text' : 'ok-text'}">${s.human_detected ? 'Detected' : 'No motion'}</strong></div>

      <div class="sensor-line"><span>Chainsaw</span><strong class="${c.confirmed_detection ? 'bad-text' : 'ok-text'}">${c.confirmed_detection ? 'DETECTED' : (c.running ? 'Monitoring' : 'Stopped')}</strong></div>`;
    card.innerHTML += `<div class="sensor-line"><span>Battery</span><strong>${safe(s.battery_v)} V</strong></div>`;
    box.appendChild(card);
  });
}

function updateAlerts(alerts) {
  const tbody = $('alertRows');
  tbody.innerHTML = '';
  (alerts || []).slice(0, 80).forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${safe(a.timestamp)}</td><td>${safe(a.node_name)}</td><td>${safe(a.source)}</td><td>${safe(a.event_type)}</td><td>${safe(a.severity)}</td><td>${safe(a.message)}</td>`;
    tbody.appendChild(tr);
  });
  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No alerts logged yet.</td></tr>';
  }
}

async function loadRecordings() {
  const box = $('recordingCards');
  if (!box) return;
  try {
    const data = await api('/api/recordings?limit=12');
    const recordings = data.recordings || [];
    box.innerHTML = '';
    if (recordings.length === 0) {
      box.innerHTML = '<div class="muted">No chainsaw recording snapshots saved yet.</div>';
      return;
    }
    recordings.forEach(rec => {
      const urls = rec.file_urls || [];
      const img = urls.length ? `<div style="position:relative"><img src="${urls[0]}" alt="${safe(rec.event_type)} recording snapshot" style="display:block;width:100%"><div style="margin-top:6px;text-align:center"><a href="${urls[0]}" download="${rec.node_name}-${(rec.timestamp||"").replace(/[: ]/g,"-")}-${rec.event_type}.jpg" class="primary" style="padding:4px 12px;font-size:0.8rem;text-decoration:none;display:inline-block;border-radius:6px;background:#3b82f6;color:#fff">Download Image</a></div></div>` : '<div class="placeholder-box"><strong>No snapshot</strong></div>';
      const card = document.createElement('div');
      card.className = 'recording-card';
      card.innerHTML = `${img}
        <div class="recording-meta">
          <strong>${safe(rec.event_type)}</strong>
          <span>${safe(rec.node_name)} | ${safe(rec.timestamp)}</span>
        </div>`;
      box.appendChild(card);
    });
  } catch (e) {
    box.innerHTML = `<div class="muted">Recording list error: ${e.message}</div>`;
  }
}

function updateNodeSelect(nodes) {
  const select = $('nodeSelect');
  const old = select.value;
  select.innerHTML = '';
  (nodes || []).forEach((n, i) => {
    const opt = document.createElement('option');
    opt.value = String(i);
    opt.textContent = nodeTitle(n, i);
    select.appendChild(opt);
  });
  if (old && Number(old) < nodes.length) select.value = old;
  renderSelectedNode();
}

function renderSelectedNode() {
  const box = $('nodeDetail');
  const idx = Number($('nodeSelect').value || 0);
  const n = allNodes[idx];
  if (!n) {
    box.innerHTML = '<div class="muted">No node selected.</div>';
    return;
  }
  const s = n.sensor_summary || {};
  const c = n.chainsaw || {};
  const t = n.thermal || {};
  const td = t.detection || {};
  const streams = nodeStreams(n);
  const streamHtml = streams.map(st => renderVideoCard(n, st, idx)).join('') || '<div class="muted">No video stream available.</div>';
  box.innerHTML = `<div class="node-detail-grid">
    <div>
      <h2>${nodeTitle(n, idx)}</h2>
      <p class="muted">${safe(n.base_url || n.url)} | ${nodeOnline(n) ? 'Online' : 'Offline'}</p>
      <div class="video-grid detail-videos">${streamHtml}</div>
    </div>
    <div>
      <h2>Status</h2>
      <div class="sensor-line"><span>ESP32</span><strong>${n.esp32_ok ? safe(n.esp32_ip) : 'Not connected'}</strong></div>
      <div class="sensor-line"><span>Temperature</span><strong>${safe(s.temperature)} °C</strong></div>
      <div class="sensor-line"><span>Humidity</span><strong>${safe(s.humidity)} %</strong></div>
      <div class="sensor-line"><span>Smoke</span><strong class="${s.smoke_detected ? 'bad-text' : 'ok-text'}">${s.smoke_detected ? 'Detected' : 'Normal'}</strong></div>
      <div class="sensor-line"><span>PIR Human</span><strong class="${s.human_detected ? 'bad-text' : 'ok-text'}">${s.human_detected ? 'Detected' : 'No motion'}</strong></div>
      <div class="sensor-line"><span>Chainsaw</span><strong class="${c.confirmed_detection ? 'bad-text' : 'ok-text'}">${c.confirmed_detection ? 'Detected' : (c.running ? 'Monitoring' : 'Stopped')}</strong></div>
      <div class="sensor-line"><span>Battery</span><strong>${safe(s.battery_v)} V</strong></div>
    </div>
  </div>`;
}

async function refreshStatus() {
  try {
    const status = await api('/api/status');
    updateHeader(status);
    let serverData = null;
    if ((status.config || {}).role === 'server') {
      serverData = await api('/api/server-dashboard');
      allNodes = serverData.all_nodes || [status.local];
      updateAlerts(serverData.recent_alerts || []);
    } else {
      allNodes = [status.local];
      updateAlerts(status.recent_alerts || []);
    }
    const remoteCount = serverData ? (serverData.remote_nodes || []).length : 0;
    $('nodeCountVal').textContent = String(remoteCount);
    const count = alertCount(allNodes);
    $('activeAlertVal').textContent = String(count);
    $('activeAlertVal').className = 'value ' + (count > 0 ? 'bad-text' : 'ok-text');
    $('activeAlertBadge').className = 'badge ' + (count > 0 ? 'red' : 'green');
    $('healthBadge').textContent = count > 0 ? 'ALERT ACTIVE' : 'System Monitoring';
    $('healthBadge').className = 'badge ' + (count > 0 ? 'red' : 'green');
    renderAllVideos(allNodes);
    renderSensorCards(allNodes);
    { let lsv = document.getElementById("liveSmokeVal"); if (lsv) { let sm = status.local.sensor_summary || {}; lsv.textContent = sm.smoke_raw != null ? sm.smoke_raw : "--"; let lss = document.getElementById("liveSmokeStatus"); if (lss) { let raw = sm.smoke_raw; let thresh = currentConfig.smoke_threshold || 500; lss.textContent = raw != null ? (raw > thresh ? "ABNORMAL" : "Normal") : "--"; lss.className = "badge " + (raw != null && raw > thresh ? "red" : "green"); } } }
  var lsv = document.getElementById('liveSmokeVal'); if (lsv) { var sm = status.local.sensor_summary || {}; lsv.textContent = sm.smoke_raw != null ? sm.smoke_raw : '--'; }
    updateNodeSelect(allNodes);
    loadRecordings();
    var localCh = (status.local || {}).chainsaw || {};
    updateChainsawDisplay(localCh);
    updateChainsawSettings(status.config || {});
    updateAudioMonitor(localCh, status.local_serial || {});
  } catch (e) {
    $('healthBadge').textContent = 'Dashboard Error';
    $('healthBadge').className = 'badge red';
    $('jsonBox').textContent = 'Status error: ' + e.message;
  }
}

async function refreshNow() {
  await refreshStatus();
}

async function scanESP32() {
  const box = $('esp32Results');
  box.innerHTML = '<div class="muted">Scanning ESP32 devices on the local subnet...</div>';
  try {
    const data = await api('/api/scan-esp32', { method: 'POST' });
    if (!data.devices || data.devices.length === 0) {
      box.innerHTML = `<div class="muted">No ESP32 FireNode found on ${data.prefix}.x. Confirm the ESP32 and RPi are on the same Wi-Fi network.</div>`;
      return;
    }
    box.innerHTML = '';
    data.devices.forEach(dev => {
      const div = document.createElement('div');
      div.className = 'result-item';
      div.innerHTML = `<div><strong>${safe(dev.node_id)}</strong><div class="meta">${dev.ip} | Temp: ${safe(dev.temperature)} °C | Hum: ${safe(dev.humidity)} %</div></div><button>Select</button>`;
      div.querySelector('button').onclick = () => selectESP32(dev.ip);
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = `<div class="muted">Scan error: ${e.message}</div>`;
  }
}

async function selectESP32(ip) {
  await api('/api/select-esp32', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ip}) });
  await refreshStatus();
}

async function scanNodes() {
  const box = $('nodeResults');
  box.innerHTML = '<div class="muted">Scanning RPi FireNode web apps...</div>';
  try {
    const data = await api('/api/scan-nodes', { method: 'POST' });
    if (!data.nodes || data.nodes.length === 0) {
      box.innerHTML = `<div class="muted">No other RPi FireNode found on ${data.prefix}.x. Make sure the other nodes are running this app on port 8090.</div>`;
      return;
    }
    box.innerHTML = '';
    data.nodes.forEach(n => {
      const div = document.createElement('div');
      div.className = 'result-item';
      div.innerHTML = `<div><strong>${safe(n.node_name)}</strong><div class="meta">${safe(n.rpi_ip)} | ${safe(n.base_url)}</div></div><span class="badge green">Added</span>`;
      box.appendChild(div);
    });
    await refreshStatus();
  } catch (e) {
    box.innerHTML = `<div class="muted">Node scan error: ${e.message}</div>`;
  }
}


async function stepperStart() {
  const speed = Number($('stepperSpeedInput').value || 2000);
  const interval = Number($('stepperIntervalInput').value || 10);
  try {
    const data = await api('/api/stepper/start?speed=' + speed + '&interval=' + interval);
    if (data.ok) {
      $('stepperStartBtn').disabled = true;
      $('stepperStopBtn').disabled = false;
      pollStepperStatus();
    } else {
      alert('Start failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { alert('Error: ' + e.message); }
}


async function stepperInitialize() {
  try {
    const data = await api('/api/stepper/initialize');
    if (data.ok) {
      $('stepperInitBtn').disabled = true;
      pollStepperStatus();
    } else {
      alert('Initialize failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { alert('Error: ' + e.message); }
}

async function stepperSingleRotation() {
  try {
    const data = await api('/api/stepper/single-rotation');
    if (data.ok) {
      $('stepperSingleBtn').disabled = true;
      pollStepperStatus();
    } else {
      alert('Single Rotation failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { alert('Error: ' + e.message); }
}

async function stepperInitialize() {
  try {
    const data = await api('/api/stepper/initialize');
    if (data.ok) {
      $('stepperInitBtn').disabled = true;
      pollStepperStatus();
    } else {
      alert('Initialize failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { alert('Error: ' + e.message); }
}

async function stepperSingleRotation() {
  try {
    const data = await api('/api/stepper/single-rotation');
    if (data.ok) {
      $('stepperSingleBtn').disabled = true;
      pollStepperStatus();
    } else {
      alert('Single Rotation failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { alert('Error: ' + e.message); }
}

async function stepperStop() {
  try {
    const data = await api('/api/stepper/stop');
    if (data.ok) {
      $('stepperStartBtn').disabled = false;
      $('stepperStopBtn').disabled = true;
      $('stepperStatus').textContent = 'Stopped';
    }
  } catch (e) {}
}



async function downloadSensorLogsCSV() {
  const node = document.getElementById("logNodeFilter")?.value || "";
  const sort = document.getElementById("logSortSelect")?.value || "desc";
  let url = "/api/sensor-logs/csv?limit=10000&sort=" + sort;
  if (node) url += "&node=" + encodeURIComponent(node);
  window.open(url, "_blank");
}

async function loadSensorLogs() {
  const node = document.getElementById('logNodeFilter')?.value || '';
  const limit = document.getElementById('logLimitSelect')?.value || 100;
  const sort = document.getElementById('logSortSelect')?.value || 'desc';
  let url = '/api/sensor-logs?limit=' + limit + '&sort=' + sort;
  if (node) url += '&node=' + encodeURIComponent(node);
  try {
    const data = await api(url);
    if (!data.ok) throw new Error(data.error || 'API error');
    const tbody = document.getElementById('sensorLogBody');
    if (!tbody) return;
    // Update node filter options
    const filter = document.getElementById('logNodeFilter');
    if (filter && data.nodes) {
      const current = filter.value;
      filter.innerHTML = '<option value="">All Nodes</option>' + data.nodes.map(n => '<option value="' + n + '"' + (n === current ? ' selected' : '') + '>' + n + '</option>').join('');
    }
    // Render rows
    tbody.innerHTML = data.rows.map(r => '<tr>' +
      '<td>' + (r.timestamp || '').slice(0,19) + '</td>' +
      '<td>' + (r.node_name || '') + '</td>' +
      '<td>' + (r.temperature != null ? r.temperature.toFixed(1) + '°C' : '--') + '</td>' +
      '<td>' + (r.humidity != null ? r.humidity.toFixed(1) + '%' : '--') + '</td>' +
      '<td>' + (r.smoke != null ? r.smoke : '--') + '</td>' +
      '<td>' + (r.pir != null ? (r.pir ? '⚠️' : '✓') : '--') + '</td>' +
      '<td>' + (r.human_detected != null ? (r.human_detected ? '⚠️' : '✓') : '--') + '</td>' +
      '<td>' + (r.battery_raw != null ? r.battery_raw + 'mV' : '--') + '</td>' +
      '</tr>').join('');
    document.getElementById('sensorLogTotal').textContent = 'Total: ' + data.total + ' rows';
  } catch (e) {
    const errDiv = document.getElementById('sensorLogError');
    if (errDiv) { errDiv.textContent = 'Error: ' + e.message; errDiv.style.display = 'block'; }
  }
}

// Auto-load sensor logs when the tab is shown
(function() {
  const origShowTab = window.showTab;
  if (origShowTab) {
    window.showTab = function(tabId) {
      origShowTab(tabId);
      if (tabId === 'sensorLogsTab') {
        setTimeout(loadSensorLogs, 100);
      }
    };
  }
})();

let stepperPollTimer = null;
async function pollStepperStatus() {
  try {
    const data = await api('/api/stepper/status');
    if (data.ok && data.status) {
      const s = data.status;
      $('stepperStatus').textContent = (s.running ? 'Running' : 'Stopped') + ' | Home: ' + (s.home ? 'YES' : 'no');
      if (!s.running) {
        $('stepperStartBtn').disabled = false;
        $('stepperStopBtn').disabled = true;
        if (stepperPollTimer) { clearInterval(stepperPollTimer); stepperPollTimer = null; }
        return;
      }
      if (!stepperPollTimer) {
        stepperPollTimer = setInterval(pollStepperStatus, 1000);
      }
    }
  } catch (e) {}
}

// Initial status check
(async function() { try { const d = await api('/api/stepper/status'); if (d.ok && d.status && d.status.running) { $('stepperStartBtn').disabled = true; $('stepperStopBtn').disabled = false; pollStepperStatus(); } } catch(e) {} })();


async function saveSettings() {
  const mirror = $('thermalMirrorInput').value;
  const payload = {
    role: $('roleSelect').value,
    operation_mode: $('operationModeInput').value,
    selected_esp32_ip: $('esp32IpInput').value.trim(),
    esp32_scan_prefix: $('esp32PrefixInput').value.trim() || 'auto',
    node_scan_prefix: $('nodePrefixInput').value.trim() || 'auto',
    server_refresh_sec: Number($('serverRefreshInput').value || 3),
    remote_node_ips: $('remoteIpsInput').value,

    camera_enabled: boolVal('cameraEnabledInput'),
    camera_device_indexes: $('camIndexesInput').value.trim() || '0',
    camera_width: Number($('camWidthInput').value || 320),
    camera_height: Number($('camHeightInput').value || 240),
    camera_fps: Number($('camFpsInput').value || 10),
    camera_jpeg_quality: Number($('camQualityInput').value || 55),

    thermal_enabled: boolVal('thermalEnabledInput'),
    thermal_simulation: boolVal('thermalSimInput'),
    thermal_i2c_address: $('thermalAddressInput').value.trim() || '0x33',
    thermal_refresh_rate_hz: Number($('thermalRefreshInput').value || 2),
    thermal_display_min_c: Number($('thermalDisplayMinInput').value || 20),
    thermal_display_max_c: Number($('thermalDisplayMaxInput').value || 45),
    thermal_min_human_temp_c: Number($('thermalHumanMinInput').value || 28),
    thermal_max_human_temp_c: Number($('thermalHumanMaxInput').value || 42),
    thermal_min_delta_above_ambient_c: Number($('thermalDeltaInput').value || 4),
    thermal_min_blob_pixels: Number($('thermalBlobInput').value || 5),
    thermal_rotate_degrees: Number($('thermalRotateInput').value || 0),
    thermal_mirror_x: mirror === 'x' || mirror === 'xy',
    thermal_mirror_y: mirror === 'y' || mirror === 'xy',

    wifi_ssid: $('wifiSsidInput').value.trim(),
    wifi_password: $('wifiPasswordInput').value,
    wifi_country: $('wifiCountryInput').value.trim() || 'PH',
    smoke_threshold: Number($('smokeThresholdInput').value || 500),
    wifi_interface: $('wifiInterfaceInput').value.trim() || 'wlan0'
  };
  try {
    await api('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    const secs = Math.max(1, Number(payload.server_refresh_sec || 3));
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(refreshStatus, secs * 1000);
    await refreshStatus();
    alert('Settings saved. If camera or thermal stream looks stuck, refresh the browser page.');
  } catch (e) {
    alert('Save failed: ' + e.message);
  }
}

async function showWifiCommands() {
  await saveSettings();
  try {
    const data = await api('/api/wifi-command-preview');
    $('wifiCommands').textContent = (data.note || '') + '\n\n' + (data.commands || []).join('\n');
  } catch (e) {
    $('wifiCommands').textContent = 'Could not generate Wi-Fi commands: ' + e.message;
  }
}

async function startDetector() {
  await api('/api/start', { method: 'POST' });
  await refreshStatus();
}
async function stopDetector() {
  await api('/api/stop', { method: 'POST' });
  await refreshStatus();
}

async function loadMicDevices() {
  const box = $('micDevices');
  box.innerHTML = '<div class="muted">Loading...</div>';
  try {
    const data = await api('/api/devices');
    if (!data.devices || data.devices.length === 0) {
      box.innerHTML = `<div class="muted">No USB microphone input found. Run ./check_mic.sh on the RPi.</div>`;
      return;
    }
    box.innerHTML = '';
    data.devices.forEach(d => {
      const div = document.createElement('div');
      div.className = 'result-item';
      div.innerHTML = `<div><strong>ID ${d.id}</strong><div class="meta">${d.name} | ${d.max_input_channels} ch | ${Math.round(d.default_samplerate)} Hz</div></div>`;
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = `<div class="muted">Mic list error: ${e.message}</div>`;
  }
}

async function browseAudio(path) {
  const box = $('audioBrowser');
  const target = path || $('browsePathInput').value || 'test_audio';
  box.innerHTML = '<div class="muted">Opening folder...</div>';
  try {
    const data = await api('/api/browse?path=' + encodeURIComponent(target));
    $('browsePathInput').value = data.path;
    box.innerHTML = `<div class="browser-path">${data.path}</div>`;
    if (data.parent) {
      const row = document.createElement('div');
      row.className = 'dir-row';
      row.innerHTML = `<span>⬆ Parent</span><button>Open</button>`;
      row.querySelector('button').onclick = () => browseAudio(data.parent);
      box.appendChild(row);
    }
    (data.shortcuts || []).forEach(s => {
      const row = document.createElement('div');
      row.className = 'dir-row';
      row.innerHTML = `<span>⭐ ${s.label}</span><button>Open</button>`;
      row.querySelector('button').onclick = () => browseAudio(s.path);
      box.appendChild(row);
    });
    (data.dirs || []).forEach(d => {
      const row = document.createElement('div');
      row.className = 'dir-row';
      row.innerHTML = `<span>📁 ${d.name}</span><button>Open</button>`;
      row.querySelector('button').onclick = () => browseAudio(d.path);
      box.appendChild(row);
    });
    (data.files || []).forEach(f => {
      const row = document.createElement('div');
      row.className = 'file-row';
      row.innerHTML = `<span>🎵 ${f.name} <span class="muted">${safe(f.size_mb)} MB</span></span><button>Analyze</button>`;
      row.querySelector('button').onclick = () => analyzeAudioFile(f.path);
      box.appendChild(row);
    });
    if ((!data.dirs || !data.dirs.length) && (!data.files || !data.files.length)) {
      box.insertAdjacentHTML('beforeend', '<div class="muted">No supported audio files in this folder. Supported: WAV, MP3, M4A, AAC, FLAC, OGG.</div>');
    }
  } catch (e) {
    box.innerHTML = `<div class="muted">Browse error: ${e.message}</div>`;
  }
}

async function analyzeAudioFile(path) {
  $('analysisResult').textContent = 'Analyzing ' + path + ' ...';
  try {
    const data = await api('/api/analyze-file', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path}) });
    $('analysisResult').textContent = JSON.stringify(data.result, null, 2);
    await refreshStatus();
  } catch (e) {
    $('analysisResult').textContent = 'Analyze error: ' + e.message;
  }
}

window.addEventListener('load', () => {
  refreshStatus();
  loadMicDevices();
  browseAudio('test_audio');
  loadRecordings();
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(refreshStatus, 3000);
  if (audioPollTimer) clearInterval(audioPollTimer);
  audioPollTimer = setInterval(audioPoll, 600);
});
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
  if (!window._selectedAudioPath) {
    $('browsePathInput').value = config.audio_browse_start_dir || 'test_audio';
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

function closeBrowserDialog() {
  var overlay = document.getElementById('browserOverlay');
  if (overlay) overlay.remove();
}

function showBrowserDialog(path) {
  // Remove existing dialog if any
  closeBrowserDialog();

  var overlay = document.createElement('div');
  overlay.id = 'browserOverlay';
  overlay.innerHTML = '<div id="browserDialog">'
    + '<div class="browser-header"><h3>Browse RPi Files</h3><button onclick="closeBrowserDialog()">×</button></div>'
    + '<div class="browser-path-bar" id="browserPathBar">Loading...</div>'
    + '<div class="browser-body" id="browserBody"></div>'
    + '</div>';
  document.body.appendChild(overlay);

  // Close on overlay click (not dialog click)
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeBrowserDialog();
  });

  // Navigate
  navigateBrowser(path || $('browsePathInput').value.trim() || 'test_audio');
}

function navigateBrowser(target) {
  var pathBar = document.getElementById('browserPathBar');
  var body = document.getElementById('browserBody');
  if (!pathBar || !body) return;
  pathBar.textContent = 'Opening folder...';
  body.innerHTML = '<div class="browser-loading">Loading...</div>';

  api('/api/browse?path=' + encodeURIComponent(target)).then(function(data) {
    pathBar.textContent = data.path;
    body.innerHTML = '';

    // Parent directory
    if (data.parent) {
      var item = document.createElement('div');
      item.className = 'browser-item';
      item.innerHTML = '<span class="item-name">.. (parent)</span><button>Open</button>';
      item.querySelector('button').onclick = function() { navigateBrowser(data.parent); };
      body.appendChild(item);
    }

    // Shortcuts
    (data.shortcuts || []).forEach(function(s) {
      var item = document.createElement('div');
      item.className = 'browser-item';
      item.innerHTML = '<span class="item-name">' + s.label + '</span><button>Open</button>';
      item.querySelector('button').onclick = function() { navigateBrowser(s.path); };
      body.appendChild(item);
    });

    // Directories
    (data.dirs || []).forEach(function(d) {
      var item = document.createElement('div');
      item.className = 'browser-item';
      item.innerHTML = '<span class="item-name">' + d.name + '/</span><button>Open</button>';
      item.querySelector('button').onclick = function() { navigateBrowser(d.path); };
      body.appendChild(item);
    });

    // Files
    (data.files || []).forEach(function(f) {
      var item = document.createElement('div');
      item.className = 'browser-item';
      item.innerHTML = '<span class="item-name">' + f.name + ' <span class="item-size">' + safe(f.size_mb) + ' MB</span></span><button>Select</button>';
      item.querySelector('button').onclick = function() {
        selectBrowserFile(f.path, data.path);
      };
      body.appendChild(item);
    });

    if ((!data.dirs || !data.dirs.length) && (!data.files || !data.files.length)) {
      body.innerHTML = '<div class="browser-empty">No supported audio files in this folder.</div>';
    }
  }).catch(function(e) {
    // Fallback to home dir
    if (target === 'test_audio' || target.indexOf('/home/betech/admfire/raspi/firenode-system/test_audio') >= 0) {
      pathBar.textContent = 'Default folder not found, trying /home/betech...';
      navigateBrowser('/home/betech');
    } else {
      pathBar.textContent = target;
      body.innerHTML = '<div class="browser-empty">Browse error: ' + e.message + '</div>';
    }
  });
}

function selectBrowserFile(filePath, dirPath) {
  $('browsePathInput').value = filePath;
  closeBrowserDialog();
  var ctrl = $('fileControls');
  ctrl.style.display = 'block';
  $('audioPlayer').src = '/api/audio?path=' + encodeURIComponent(filePath);
  $('audioPlayer').style.display = 'none';
  $('detectionResult').style.display = 'none';
  $('playFileBtn').textContent = 'Play';
  $('playFileBtn').disabled = false;
  window._selectedAudioPath = filePath;
}

function playSelectedAudio() {
  var player = $('audioPlayer');
  var btn = $('playFileBtn');
  if (player.paused) {
    player.style.display = 'block';
    player.play().catch(function(e) {
      $('detectionResult').style.display = 'block';
      $('detectionResult').innerHTML = '<div class="muted">Playback error: ' + e.message + '</div>';
    });
    btn.textContent = 'Pause';
    // Auto-detect when playing
    setTimeout(function() { detectSelectedFile(); }, 500);
  } else {
    player.pause();
    btn.textContent = 'Play';
  }
}

function stopSelectedAudio() {
  var player = $('audioPlayer');
  player.pause();
  player.currentTime = 0;
  player.style.display = 'none';
  $('playFileBtn').textContent = 'Play';
}

function detectSelectedFile() {
  var path = window._selectedAudioPath;
  if (!path) return;
  var result = $('detectionResult');
  var btn = $('playFileBtn');
  result.style.display = 'block';
  result.innerHTML = '<div class="muted">Analyzing ' + path.split('/').pop() + ' ...</div>';

  api('/api/analyze-file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: path })
  }).then(function(data) {
    var r = data.result || {};
    var confirmed = r.confirmed;
    var avgScore = (r.average_score || 0).toFixed(1);
    var hits = r.hits || 0;
    var duration = (r.duration_sec || 0).toFixed(1);
    var maxScore = (r.max_score || 0).toFixed(1);
    var html = '';
    if (confirmed) {
      html += '<div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:10px;margin-bottom:8px">';
      html += '<strong style="color:#ef4444;font-size:16px">CHAINSAW CONFIRMED</strong>';
      html += '</div>';
    } else {
      html += '<div style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:10px;margin-bottom:8px">';
      html += '<strong style="color:#22c55e;font-size:16px">No chainsaw detected</strong>';
      html += '</div>';
    }
    html += '<div class="sensor-line"><span>Avg Score</span><strong>' + avgScore + '</strong></div>';
    html += '<div class="sensor-line"><span>Max Score</span><strong>' + maxScore + '</strong></div>';
    html += '<div class="sensor-line"><span>Detection Hits</span><strong>' + hits + '</strong></div>';
    html += '<div class="sensor-line"><span>Duration</span><strong>' + duration + 's</strong></div>';
    if (r.best_window && r.best_window.bands) {
      var b = r.best_window.bands;
      html += '<div style="margin-top:8px;font-size:12px;color:var(--muted)">';
      html += '<div>Chain ratio: ' + (b.chain_ratio || 0).toFixed(3) + '</div>';
      html += '<div>Engine ratio: ' + (b.engine_ratio || 0).toFixed(3) + '</div>';
      html += '<div>Mechanical ratio: ' + (b.mechanical_ratio || 0).toFixed(3) + '</div>';
      html += '</div>';
    }
    result.innerHTML = html;
    // Refresh status to update dashboard
    refreshStatus();
  }).catch(function(e) {
    btn.disabled = false;
    btn.textContent = 'Detect Chainsaw';
    result.innerHTML = '<div class="muted">Detection error: ' + e.message + '</div>';
  });
}

function clearSelectedFile() {
  var ctrl = $('fileControls');
  var player = $('audioPlayer');
  player.pause();
  player.src = '';
  player.style.display = 'none';
  ctrl.style.display = 'none';
  $('browsePathInput').value = '/home/betech/chainsaw_audio';
  window._selectedAudioPath = null;
  $('detectionResult').style.display = 'none';
  $('playFileBtn').textContent = 'Play';
}

// Keep browseAudio as entry point for onclick

async function shutdownRPi() {
  var btn = document.activeElement;
  var msg = document.getElementById('shutdownMsg');
  if (!msg) return;
  if (!confirm('Shutdown this RPi? The web GUI will go offline.')) return;
  btn.disabled = true;
  btn.textContent = 'Shutting down...';
  msg.innerHTML = '<span class="bad-text">Shutting down...</span>';
  try {
    var r = await fetch('/api/shutdown', {method:'POST', headers:{'Authorization':'Basic ' + btoa('betech:betech')}});
    var d = await r.json();
    if (d.ok) {
      msg.innerHTML = '<span class="ok-text">Shutdown initiated. RPi will power off.</span>';
    } else {
      msg.innerHTML = '<span class="bad-text">Error: ' + (d.error || 'unknown') + '</span>';
      btn.disabled = false;
      btn.textContent = 'Shutdown Now';
    }
  } catch(e) {
    msg.innerHTML = '<span class="bad-text">Request failed: ' + e.message + '</span>';
    btn.disabled = false;
    btn.textContent = 'Shutdown Now';
  }
}
