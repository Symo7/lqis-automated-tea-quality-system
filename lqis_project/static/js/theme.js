(function () {
  const storageKey = 'lqis-theme';
  const root = document.documentElement;
  let deferredPrompt = null;

  function preferredTheme() {
    const stored = localStorage.getItem(storageKey);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    root.setAttribute('data-bs-theme', theme); // Native Bootstrap 5.3 dark mode support
    localStorage.setItem(storageKey, theme);
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = theme === 'dark' ? '☀ Light' : '🌙 Dark';
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
  }
  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.register('/service-worker.js', { scope: '/' });
      await reg.update();
    } catch (_) {}
  }

  function setupInstallPrompt() {
    const installBtn = document.getElementById('installBtn');
    if (!installBtn) return;

    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      deferredPrompt = event;
      installBtn.classList.remove('d-none');
    });

    installBtn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      installBtn.classList.add('d-none');
    });

    window.addEventListener('appinstalled', () => {
      installBtn.classList.add('d-none');
      deferredPrompt = null;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(preferredTheme());
    
    const btn = document.getElementById('themeToggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }

    // Safely listen for real-time OS theme changes cross-browser
    try {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const themeChangeHandler = (e) => {
        const newTheme = e.matches ? 'dark' : 'light';
        applyTheme(newTheme);
      };
      
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', themeChangeHandler);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(themeChangeHandler); // Safari < 14 fallback
      }
    } catch (err) {
      console.warn("Theme auto-detection not supported", err);
    }

    setupInstallPrompt();
    registerServiceWorker();
  });
})();
