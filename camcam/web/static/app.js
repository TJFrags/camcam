/**
 * CamCam - Nikon D3100 Quick Settings & Remote Shutter Logic (Direct SD Card Trigger)
 */

// Global State
const state = {
  connected: false,
  mode: 'single', // 'single', 'burst', 'timelapse'
  delay: 0,
  burstCount: 3,
  settings: {
    iso: 'Auto',
    shutterspeed: '1/125',
    aperture: '5.6',
    exposurecompensation: '0',
    whitebalance: 'Auto',
    preset: 'Auto'
  },
  timelapseRunning: false,
  timelapseTimer: null,
  isCapturing: false,
};

// ==============================================================================
// Web Audio API Synthesizer for Realistic Camera Shutter Sound
// ==============================================================================
let audioCtx = null;

function initAudio() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audioCtx = new AudioContext();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function playBeep(freq = 880, duration = 0.08) {
  try {
    initAudio();
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {
    // Graceful fallback
  }
}

function playShutterSound() {
  try {
    initAudio();
    if (!audioCtx) return;
    const now = audioCtx.currentTime;

    // Mirror Up Click
    const osc1 = audioCtx.createOscillator();
    const gain1 = audioCtx.createGain();
    osc1.type = 'triangle';
    osc1.frequency.setValueAtTime(140, now);
    osc1.frequency.exponentialRampToValueAtTime(40, now + 0.04);
    gain1.gain.setValueAtTime(0.4, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.04);
    osc1.connect(gain1);
    gain1.connect(audioCtx.destination);
    osc1.start(now);
    osc1.stop(now + 0.04);

    // Shutter Curtain & Mirror Down Click
    const osc2 = audioCtx.createOscillator();
    const gain2 = audioCtx.createGain();
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(180, now + 0.08);
    osc2.frequency.exponentialRampToValueAtTime(30, now + 0.14);
    gain2.gain.setValueAtTime(0.5, now + 0.08);
    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.14);
    osc2.connect(gain2);
    gain2.connect(audioCtx.destination);
    osc2.start(now + 0.08);
    osc2.stop(now + 0.14);
  } catch (e) {
    // Graceful fallback
  }
}


// ==============================================================================
// DOM Elements
// ==============================================================================
const dom = {
  cameraStatusPill: document.getElementById('camera-status-pill'),
  cameraStatusText: document.getElementById('camera-status-text'),
  btnReconnect: document.getElementById('btn-reconnect'),

  valBadgeIso: document.getElementById('val-badge-iso'),
  valBadgeShutter: document.getElementById('val-badge-shutter'),
  valBadgeAperture: document.getElementById('val-badge-aperture'),
  valBadgeEc: document.getElementById('val-badge-ec'),
  valBadgeDelay: document.getElementById('val-badge-delay'),

  presetPills: document.querySelectorAll('.preset-pill'),
  isoPills: document.querySelectorAll('#iso-pills .chip-pill'),
  shutterPills: document.querySelectorAll('#shutter-pills .chip-pill'),
  aperturePills: document.querySelectorAll('#aperture-pills .chip-pill'),
  ecPills: document.querySelectorAll('#ec-pills .chip-pill'),
  delayPills: document.querySelectorAll('#delay-pills .chip-pill'),
  burstCountPills: document.querySelectorAll('#burst-count-pills .chip-pill'),

  modeTabs: document.querySelectorAll('.mode-tab'),
  shutterArena: document.getElementById('shutter-arena'),
  timelapseArena: document.getElementById('timelapse-arena'),
  burstControls: document.getElementById('burst-controls'),
  btnShutter: document.getElementById('btn-shutter'),
  shutterBtnLabel: document.getElementById('shutter-btn-label'),
  countdownDisplay: document.getElementById('countdown-display'),
  countdownFill: document.getElementById('countdown-fill'),
  countdownNum: document.getElementById('countdown-num'),

  captureStatusBanner: document.getElementById('capture-status-banner'),
  bannerIcon: document.getElementById('banner-icon'),
  bannerText: document.getElementById('banner-text'),

  tlIntervalInput: document.getElementById('tl-interval-input'),
  tlCountInput: document.getElementById('tl-count-input'),
  tlIntDec: document.getElementById('tl-int-dec'),
  tlIntInc: document.getElementById('tl-int-inc'),
  tlCountDec: document.getElementById('tl-count-dec'),
  tlCountInc: document.getElementById('tl-count-inc'),
  btnTimelapseToggle: document.getElementById('btn-timelapse-toggle'),
  tlMonitor: document.getElementById('tl-monitor'),
  tlProgressFill: document.getElementById('tl-progress-fill'),
  tlStatTaken: document.getElementById('tl-stat-taken'),
  tlStatTarget: document.getElementById('tl-stat-target'),
  tlStatElapsed: document.getElementById('tl-stat-elapsed'),

  sysDriver: document.getElementById('sys-driver'),
};


// ==============================================================================
// Initialization & Event Binding
// ==============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  fetchCameraStatus();
  fetchCameraSettings();

  // Periodic heartbeat
  setInterval(fetchCameraStatus, 6000);
});

function initEventListeners() {
  // Reconnect
  dom.btnReconnect.addEventListener('click', async () => {
    showBanner('⏳ Connecting to Nikon D3100 via USB...', 'connecting');
    try {
      const res = await fetch('/api/camera/connect', { method: 'POST' });
      const data = await res.json();
      if (data.connected) {
        showBanner(`✅ Connected: ${data.model}`, 'success');
      } else {
        showBanner('❌ Camera not detected. Check USB cable and turn power ON.', 'error');
      }
      fetchCameraStatus();
    } catch (e) {
      showBanner('❌ Connection failed', 'error');
    }
  });

  // Presets
  dom.presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const preset = pill.getAttribute('data-preset');
      applyPreset(preset);
    });
  });

  // ISO
  dom.isoPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const val = pill.getAttribute('data-value');
      updateSetting('iso', val);
    });
  });

  // Shutter Speed
  dom.shutterPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const val = pill.getAttribute('data-value');
      updateSetting('shutterspeed', val);
    });
  });

  // Aperture
  dom.aperturePills.forEach(pill => {
    pill.addEventListener('click', () => {
      const val = pill.getAttribute('data-value');
      updateSetting('aperture', val);
    });
  });

  // Exposure Comp
  dom.ecPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const val = pill.getAttribute('data-value');
      updateSetting('exposurecompensation', val);
    });
  });

  // Delay / Self-Timer
  dom.delayPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const val = parseFloat(pill.getAttribute('data-value'));
      state.delay = val;
      dom.delayPills.forEach(p => p.classList.toggle('active', p === pill));
      dom.valBadgeDelay.textContent = `${val}s`;
    });
  });

  // Burst Count
  dom.burstCountPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const cnt = parseInt(pill.getAttribute('data-count'), 10);
      state.burstCount = cnt;
      dom.burstCountPills.forEach(p => p.classList.toggle('active', p === pill));
    });
  });

  // Mode Tabs
  dom.modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const mode = tab.getAttribute('data-mode');
      setMode(mode);
    });
  });

  // Shutter Trigger
  dom.btnShutter.addEventListener('click', handleShutterClick);

  // Timelapse controls
  dom.tlIntDec.addEventListener('click', () => {
    dom.tlIntervalInput.value = Math.max(1, parseInt(dom.tlIntervalInput.value) - 1);
  });
  dom.tlIntInc.addEventListener('click', () => {
    dom.tlIntervalInput.value = parseInt(dom.tlIntervalInput.value) + 1;
  });
  dom.tlCountDec.addEventListener('click', () => {
    dom.tlCountInput.value = Math.max(0, parseInt(dom.tlCountInput.value) - 10);
  });
  dom.tlCountInc.addEventListener('click', () => {
    dom.tlCountInput.value = parseInt(dom.tlCountInput.value) + 10;
  });
  dom.btnTimelapseToggle.addEventListener('click', handleTimelapseToggle);
}


// ==============================================================================
// Camera Status & Settings Sync
// ==============================================================================
async function fetchCameraStatus() {
  try {
    const res = await fetch('/api/camera/status');
    const data = await res.json();
    state.connected = data.connected;

    if (data.connected) {
      dom.cameraStatusPill.className = 'status-pill status-connected';
      dom.cameraStatusText.textContent = `${data.model}`;
      dom.sysDriver.textContent = data.backend;
    } else {
      dom.cameraStatusPill.className = 'status-pill status-error';
      dom.cameraStatusText.textContent = 'Camera Disconnected';
    }
  } catch (e) {
    dom.cameraStatusPill.className = 'status-pill status-error';
    dom.cameraStatusText.textContent = 'API Offline';
  }
}

async function fetchCameraSettings() {
  try {
    const res = await fetch('/api/camera/settings');
    const data = await res.json();
    if (data.current) {
      state.settings = { ...state.settings, ...data.current };
      syncSettingsUI();
    }
  } catch (e) {
    console.error('Failed to fetch settings:', e);
  }
}

function syncSettingsUI() {
  // ISO
  dom.valBadgeIso.textContent = state.settings.iso;
  dom.isoPills.forEach(p => {
    p.classList.toggle('active', p.getAttribute('data-value') === state.settings.iso);
  });

  // Shutter
  dom.valBadgeShutter.textContent = state.settings.shutterspeed;
  dom.shutterPills.forEach(p => {
    p.classList.toggle('active', p.getAttribute('data-value') === state.settings.shutterspeed);
  });

  // Aperture
  dom.valBadgeAperture.textContent = `f/${state.settings.aperture}`;
  dom.aperturePills.forEach(p => {
    p.classList.toggle('active', p.getAttribute('data-value') === state.settings.aperture);
  });

  // EC
  dom.valBadgeEc.textContent = `${state.settings.exposurecompensation} EV`;
  dom.ecPills.forEach(p => {
    p.classList.toggle('active', p.getAttribute('data-value') === state.settings.exposurecompensation);
  });
}

async function updateSetting(key, value) {
  state.settings[key] = value;
  syncSettingsUI();

  // Clear preset selection since custom setting chosen
  dom.presetPills.forEach(p => p.classList.remove('active'));

  try {
    await fetch('/api/camera/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value })
    });
  } catch (e) {
    console.error(`Failed to update ${key}:`, e);
  }
}

async function applyPreset(presetName) {
  dom.presetPills.forEach(p => {
    p.classList.toggle('active', p.getAttribute('data-preset') === presetName);
  });

  try {
    const res = await fetch('/api/camera/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset: presetName })
    });
    const data = await res.json();
    if (data.settings && data.settings.current) {
      state.settings = { ...state.settings, ...data.settings.current };
      syncSettingsUI();
    }
  } catch (e) {
    console.error('Failed to apply preset:', e);
  }
}


// ==============================================================================
// Mode Switching
// ==============================================================================
function setMode(mode) {
  state.mode = mode;
  dom.modeTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-mode') === mode));

  if (mode === 'single') {
    dom.shutterArena.style.display = 'flex';
    dom.timelapseArena.style.display = 'none';
    dom.burstControls.style.display = 'none';
    dom.shutterBtnLabel.textContent = 'TRIGGER';
  } else if (mode === 'burst') {
    dom.shutterArena.style.display = 'flex';
    dom.timelapseArena.style.display = 'none';
    dom.burstControls.style.display = 'flex';
    dom.shutterBtnLabel.textContent = 'BURST';
  } else if (mode === 'timelapse') {
    dom.shutterArena.style.display = 'none';
    dom.timelapseArena.style.display = 'flex';
  }
}


// ==============================================================================
// Shutter & Capture Execution (Trigger to Camera SD Card)
// ==============================================================================
async function handleShutterClick() {
  if (state.isCapturing) return;
  initAudio();

  // Run countdown if delay > 0
  if (state.delay > 0) {
    await runCountdown(state.delay);
  }

  playShutterSound();
  state.isCapturing = true;
  dom.btnShutter.classList.add('disabled');

  const cleanSettings = {
    iso: state.settings.iso,
    shutterspeed: state.settings.shutterspeed,
    aperture: state.settings.aperture,
    exposurecompensation: state.settings.exposurecompensation,
    whitebalance: state.settings.whitebalance,
  };

  if (state.mode === 'burst') {
    showBanner(`⚡ Firing ${state.burstCount}-shot burst...`, 'capturing');
    try {
      const res = await fetch('/api/shutter/burst', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          count: state.burstCount,
          delay_between: 0.2,
          settings: cleanSettings
        })
      });
      const data = await res.json();
      if (data.success) {
        showBanner(`✅ ${data.count} shots saved to camera SD card!`, 'success');
      } else {
        showBanner(`❌ Burst trigger failed: ${data.detail || ''}`, 'error');
      }
    } catch (e) {
      showBanner(`❌ Error: ${e.message}`, 'error');
    } finally {
      state.isCapturing = false;
      dom.btnShutter.classList.remove('disabled');
    }
  } else {
    showBanner('⚡ Triggering Nikon D3100 shutter...', 'capturing');
    try {
      const res = await fetch('/api/shutter/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delay: 0.0,
          settings: cleanSettings
        })
      });
      const data = await res.json();
      if (data.success) {
        showBanner(`✅ Shutter Fired! Photo saved to SD Card.`, 'success');
      } else {
        showBanner(`❌ Shutter trigger failed: ${data.detail || ''}`, 'error');
      }
    } catch (e) {
      showBanner(`❌ Error: ${e.message}`, 'error');
    } finally {
      state.isCapturing = false;
      dom.btnShutter.classList.remove('disabled');
    }
  }
}

function runCountdown(seconds) {
  return new Promise((resolve) => {
    dom.countdownDisplay.style.display = 'flex';
    let remaining = seconds;
    const totalCircumference = 440;

    dom.countdownNum.textContent = remaining;
    dom.countdownFill.style.strokeDashoffset = '0';
    playBeep(880, 0.1);

    const interval = setInterval(() => {
      remaining -= 1;
      if (remaining > 0) {
        dom.countdownNum.textContent = remaining;
        const offset = totalCircumference * (1 - remaining / seconds);
        dom.countdownFill.style.strokeDashoffset = `${offset}`;
        playBeep(880, 0.1);
      } else {
        clearInterval(interval);
        dom.countdownDisplay.style.display = 'none';
        playBeep(1760, 0.2);
        resolve();
      }
    }, 1000);
  });
}

function showBanner(text, type = 'info') {
  dom.captureStatusBanner.style.display = 'flex';
  dom.bannerText.textContent = text;

  if (type === 'success') {
    dom.bannerIcon.textContent = '✅';
    dom.captureStatusBanner.style.borderColor = 'rgba(0, 230, 118, 0.4)';
    dom.captureStatusBanner.style.color = 'var(--accent-green)';
  } else if (type === 'error') {
    dom.bannerIcon.textContent = '❌';
    dom.captureStatusBanner.style.borderColor = 'rgba(255, 51, 102, 0.4)';
    dom.captureStatusBanner.style.color = 'var(--accent-red)';
  } else {
    dom.bannerIcon.textContent = '⚡';
    dom.captureStatusBanner.style.borderColor = 'rgba(0, 210, 255, 0.4)';
    dom.captureStatusBanner.style.color = 'var(--primary)';
  }

  if (type === 'success' || type === 'error') {
    setTimeout(() => {
      dom.captureStatusBanner.style.display = 'none';
    }, 4000);
  }
}


// ==============================================================================
// Timelapse / Intervalometer
// ==============================================================================
async function handleTimelapseToggle() {
  if (state.timelapseRunning) {
    // Stop
    try {
      await fetch('/api/timelapse/stop', { method: 'POST' });
      stopTimelapseUI();
    } catch (e) {
      console.error(e);
    }
  } else {
    // Start
    const interval = parseFloat(dom.tlIntervalInput.value) || 5;
    const count = parseInt(dom.tlCountInput.value, 10) || 0;

    try {
      const res = await fetch('/api/timelapse/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval, count })
      });
      const data = await res.json();
      if (data.success) {
        startTimelapseUI(interval, count);
      }
    } catch (e) {
      showBanner(`❌ Failed to start timelapse: ${e.message}`, 'error');
    }
  }
}

function startTimelapseUI(interval, count) {
  state.timelapseRunning = true;
  dom.btnTimelapseToggle.textContent = '⏹ Stop Timelapse';
  dom.btnTimelapseToggle.className = 'btn-primary-action btn-danger';
  dom.tlMonitor.style.display = 'flex';
  dom.tlStatTarget.textContent = count === 0 ? '∞' : count;

  let startTime = Date.now();
  state.timelapseTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/timelapse/status');
      const st = await res.json();
      if (!st.active) {
        stopTimelapseUI();
        return;
      }

      dom.tlStatTaken.textContent = st.shots_taken;
      if (st.total_shots > 0) {
        const pct = Math.min(100, (st.shots_taken / st.total_shots) * 100);
        dom.tlProgressFill.style.width = `${pct}%`;
      } else {
        dom.tlProgressFill.style.width = '100%';
      }

      const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
      const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const secs = String(elapsedSec % 60).padStart(2, '0');
      dom.tlStatElapsed.textContent = `${mins}:${secs}`;
    } catch (e) {
      // Ignore
    }
  }, 1000);
}

function stopTimelapseUI() {
  state.timelapseRunning = false;
  clearInterval(state.timelapseTimer);
  dom.btnTimelapseToggle.textContent = '▶ Start Timelapse';
  dom.btnTimelapseToggle.className = 'btn-primary-action';
  dom.tlMonitor.style.display = 'none';
}
