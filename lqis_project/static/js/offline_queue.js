(function () {
  const DB_NAME = 'lqis_offline_db';
  const STORE = 'sampling_queue';
  const META = 'meta_store';
  const META_KEY = 'master_data_snapshot';
  const LAST_SYNC_KEY = 'last_sync_at';

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          const st = db.createObjectStore(STORE, { keyPath: 'local_id' });
          st.createIndex('sync_status', 'sync_status', { unique: false });
          st.createIndex('created_at', 'created_at', { unique: false });
        }
        if (!db.objectStoreNames.contains(META)) {
          db.createObjectStore(META, { keyPath: 'key' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function tx(store, mode, fn) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const t = db.transaction(store, mode);
      const s = t.objectStore(store);
      const result = fn(s);
      t.oncomplete = () => resolve(result && result.result !== undefined ? result.result : result);
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error);
    });
  }

  async function putQueue(item) { return tx(STORE, 'readwrite', (s) => s.put(item)); }
  async function deleteQueue(localId) { return tx(STORE, 'readwrite', (s) => s.delete(localId)); }
  async function getAllQueue() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const t = db.transaction(STORE, 'readonly');
      const req = t.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }
  async function setMeta(key, value) { return tx(META, 'readwrite', (s) => s.put({ key, value })); }
  async function getMeta(key) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const t = db.transaction(META, 'readonly');
      const req = t.objectStore(META).get(key);
      req.onsuccess = () => resolve(req.result ? req.result.value : null);
      req.onerror = () => reject(req.error);
    });
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function toast(message, type = 'info') {
    const host = document.querySelector('main') || document.body;
    const el = document.createElement('div');
    el.className = `alert alert-${type} shadow-sm`;
    el.textContent = message;
    host.prepend(el);
    setTimeout(() => el.remove(), 4500);
  }

  function onlineState() { return navigator.onLine ? 'Online' : 'Offline'; }

  async function updateStatusUi() {
    const chip = document.getElementById('connectionChip');
    const txt = document.getElementById('connectionText');
    const all = await getAllQueue();
    const pending = all.filter((x) => x.sync_status === 'pending' || x.sync_status === 'failed');
    const badge = document.getElementById('queueCountBadge');
    const list = document.getElementById('queueList');
    const lastSync = document.getElementById('lastSyncText');

    if (txt) txt.textContent = onlineState();
    if (chip) chip.classList.toggle('chip-offline', !navigator.onLine);
    if (badge) badge.textContent = String(pending.length);

    if (list) {
      if (!all.length) {
        list.innerHTML = '<div class="empty-state">No queued submissions.</div>';
      } else {
        list.innerHTML = all
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
          .map(
            (i) => `<div class="card mb-2"><div class="card-body p-2"><div class="fw-semibold">${i.batch_label || 'Batch'}</div><div class="small text-muted">${i.sync_status} • retries ${i.retry_count || 0}</div>${i.last_error_message ? `<div class="small text-danger">${i.last_error_message}</div>` : ''}</div></div>`
          )
          .join('');
      }
    }

    const last = await getMeta(LAST_SYNC_KEY);
    if (lastSync) lastSync.textContent = last ? new Date(last).toLocaleString() : 'Never';
  }

  async function imageFileToDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  async function refreshMasterDataCache() {
    if (!navigator.onLine) return;
    try {
      const res = await fetch('/api/master-data-snapshot/', { headers: { Accept: 'application/json' } });
      if (!res.ok) return;
      const payload = await res.json();
      await setMeta(META_KEY, payload);
      window.dispatchEvent(new CustomEvent('masterDataUpdated', { detail: payload }));
    } catch (_) {}
  }

  async function getMasterDataCache() {
    return (await getMeta(META_KEY)) || { factories: [], centers: [], suppliers: [], batches: [] };
  }

  function fillSelect(select, options, labelFn, valueKey = 'id') {
    if (!select) return;
    const current = select.value;
    select.innerHTML = '<option value="">---------</option>';
    options.forEach((item) => {
      const opt = document.createElement('option');
      opt.value = item[valueKey];
      opt.textContent = labelFn(item);
      select.appendChild(opt);
    });
    if (current) select.value = current;
  }

  let _cacheListenerBound = false;
  async function applyCachedMasterDataToSamplingForm() {
    const form = document.getElementById('samplingForm');
    if (!form) return;
    const cache = await getMasterDataCache();
    const factorySel = document.getElementById('id_factory');
    const centerSel = document.getElementById('id_tea_buying_center');
    const supplierSel = document.getElementById('id_supplier');
    const batchSel = document.getElementById('id_batch');

    if (!factorySel || !cache.factories?.length) return;

    fillSelect(factorySel, cache.factories, (x) => `${x.name} (${x.code})`);
    if (supplierSel && cache.suppliers?.length) fillSelect(supplierSel, cache.suppliers, (x) => `${x.name} (${x.code})`);

    const bindFactory = () => {
      const f = Number(factorySel.value);
      const centers = cache.centers.filter((x) => Number(x.factory_id) === f);
      const batches = cache.batches.filter((x) => Number(x.factory_id) === f);
      fillSelect(centerSel, centers, (x) => `${x.name} (${x.code})`);
      fillSelect(batchSel, batches, (x) => x.batch_code);
    };
    if (!_cacheListenerBound) {
      factorySel.addEventListener('change', bindFactory);
      _cacheListenerBound = true;
    }
    bindFactory();
  }

  async function queueCurrentFormOffline() {
    const form = document.getElementById('samplingForm');
    if (!form) return false;

    const fileInput = document.getElementById('id_leaf_image');
    const imageFile = fileInput && fileInput.files ? fileInput.files[0] : null;
    if (!imageFile) {
      toast('Leaf image is required for offline queue.', 'warning');
      return false;
    }

    const localId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const imageDataUrl = await imageFileToDataUrl(imageFile);

    const item = {
      local_id: localId,
      created_at: new Date().toISOString(),
      sync_status: 'pending',
      retry_count: 0,
      last_error_message: '',
      endpoint: '/sampling/sync-submit/',
      payload: {
        local_id: localId,
        factory: document.getElementById('id_factory')?.value || '',
        tea_buying_center: document.getElementById('id_tea_buying_center')?.value || '',
        supplier: document.getElementById('id_supplier')?.value || '',
        batch: document.getElementById('id_batch')?.value || '',
        intake_timestamp: document.getElementById('id_intake_timestamp')?.value || '',
        manual_override_pluck_score: document.getElementById('id_manual_override_pluck_score')?.value || '',
        moisture_pct: document.getElementById('id_moisture_pct')?.value || '',
        foreign_matter_pct: document.getElementById('id_foreign_matter_pct')?.value || '',
        notes: document.getElementById('id_notes')?.value || '',
        image_data_url: imageDataUrl,
      },
      batch_label: document.getElementById('id_batch')?.selectedOptions?.[0]?.textContent || 'Batch',
    };

    await putQueue(item);
    toast('Saved offline. Will sync when connection returns.', 'success');
    form.reset();
    await updateStatusUi();
    registerBackgroundSync();
    // Notify form template to clean up image preview + re-populate selects
    window.dispatchEvent(new CustomEvent('offlineSampleQueued'));
    return true;
  }

  async function syncQueuedSubmissions() {
    if (!navigator.onLine) return;
    const all = await getAllQueue();
    const targets = all.filter((x) => x.sync_status === 'pending' || x.sync_status === 'failed');
    if (!targets.length) {
      await setMeta(LAST_SYNC_KEY, new Date().toISOString());
      await updateStatusUi();
      return;
    }

    for (const item of targets) {
      try {
        const res = await fetch(item.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          credentials: 'same-origin',
          body: JSON.stringify(item.payload),
        });

        if (!res.ok) {
          const errTxt = await res.text();
          item.sync_status = 'failed';
          item.retry_count = (item.retry_count || 0) + 1;
          item.last_error_message = `HTTP ${res.status}: ${errTxt.slice(0, 120)}`;
          await putQueue(item);
          continue;
        }

        await deleteQueue(item.local_id);
      } catch (error) {
        item.sync_status = 'failed';
        item.retry_count = (item.retry_count || 0) + 1;
        item.last_error_message = String(error).slice(0, 140);
        await putQueue(item);
      }
    }

    await setMeta(LAST_SYNC_KEY, new Date().toISOString());
    await updateStatusUi();
  }

  async function registerBackgroundSync() {
    if (!('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.ready;
    if (reg.sync && typeof reg.sync.register === 'function') {
      try { await reg.sync.register('lqis-sync'); } catch (_) {}
    }
  }

  function bindSamplingSubmitInterception() {
    const form = document.getElementById('samplingForm');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      if (navigator.onLine) return;
      event.preventDefault();
      await queueCurrentFormOffline();
    });
  }

  function bindGlobalSyncUi() {
    const syncNow = document.getElementById('syncNowBtn');
    if (syncNow) syncNow.addEventListener('click', () => syncQueuedSubmissions());

    window.addEventListener('online', async () => {
      toast('Connection restored. Syncing queued submissions…', 'info');
      await syncQueuedSubmissions();
    });
    window.addEventListener('offline', () => updateStatusUi());
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && navigator.onLine) syncQueuedSubmissions();
    });

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'TRIGGER_SYNC') syncQueuedSubmissions();
      });
    }
  }

  async function init() {
    await updateStatusUi();
    bindSamplingSubmitInterception();
    bindGlobalSyncUi();
    await refreshMasterDataCache();
    await applyCachedMasterDataToSamplingForm();
    if (navigator.onLine) await syncQueuedSubmissions();
  }

  window.lqisOffline = {
    syncNow: syncQueuedSubmissions,
    queueOffline: queueCurrentFormOffline,
    getQueue: getAllQueue,
    getMasterCache: getMasterDataCache,
    reloadFormFromCache: applyCachedMasterDataToSamplingForm,
  };

  document.addEventListener('DOMContentLoaded', init);
})();
