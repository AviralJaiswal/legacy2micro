// Prodapt ModernizeAI — App interactions, button wiring, validation

// Animated count-up for stat values
function animateCount(el) {
  const target = parseFloat(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const duration = 1200;
  const start = performance.now();
  const isFloat = String(el.dataset.count).includes('.');

  function frame(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const val = target * eased;
    el.textContent = (isFloat ? val.toFixed(1) : Math.round(val).toLocaleString()) + suffix;
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// Animate progress bars
function animateBars() {
  document.querySelectorAll('.progress > span').forEach((bar) => {
    const w = bar.style.width;
    bar.style.width = '0';
    requestAnimationFrame(() => requestAnimationFrame(() => { bar.style.width = w; }));
  });
}

// Toast notification
function showToast(msg, type) {
  type = type || 'info';
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed; bottom:24px; right:24px; padding:12px 20px; border-radius:10px; font-size:13px; font-weight:600; color:#fff; z-index:9999; box-shadow:0 8px 24px rgba(0,0,0,0.2); transition:opacity 0.3s, transform 0.3s; transform:translateY(10px); opacity:0;';
  if (type === 'success') toast.style.background = 'linear-gradient(135deg, #10B981, #059669)';
  else if (type === 'error') toast.style.background = 'linear-gradient(135deg, #EF4444, #DC2626)';
  else toast.style.background = 'linear-gradient(135deg, #2E6BFF, #8B5CF6)';
  toast.textContent = msg;
  document.body.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; toast.style.transform = 'translateY(0)'; });
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateY(10px)'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// Confirm dialog
function confirmAction(msg, onYes) {
  if (confirm(msg)) onYes();
}

// Form validation helper
function validateForm(form) {
  let valid = true;
  form.querySelectorAll('[required]').forEach((field) => {
    field.style.borderColor = '';
    if (!field.value.trim()) {
      field.style.borderColor = '#EF4444';
      valid = false;
    }
  });
  form.querySelectorAll('input[type="email"]').forEach((field) => {
    if (field.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
      field.style.borderColor = '#EF4444';
      valid = false;
    }
  });
  return valid;
}

// Wire up all buttons with data-action attributes
document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;

  switch (action) {
    case 'new-project':
      window.location.href = 'upload.html';
      break;
    case 'import-report':
      showToast('Report import started...', 'info');
      break;
    case 'save-draft':
      showToast('Draft saved to local DB', 'success');
      break;
    case 'start-analysis':
      showToast('Analysis started — processing 573 files', 'success');
      break;
    case 'export-graph':
      showToast('Graph exported as JSON', 'success');
      break;
    case 'review-arch':
      window.location.href = 'architecture.html';
      break;
    case 'open-source':
      showToast('Opening source file...', 'info');
      break;
    case 'add-scope':
      showToast('Added to migration scope', 'success');
      break;
    case 'modify-boundaries':
      showToast('Boundary modification mode enabled', 'info');
      break;
    case 'approve-boundary':
      showToast('Boundary approved', 'success');
      break;
    case 'save-scope-draft':
      showToast('Scope draft saved', 'success');
      break;
    case 'approve-migrate':
      confirmAction('Approve migration scope and begin?', () => {
        showToast('Migration scope approved — starting AI generation', 'success');
        setTimeout(() => { window.location.href = 'workspace.html'; }, 1000);
      });
      break;
    case 'pause-run':
      showToast('Migration run paused', 'info');
      break;
    case 'fix-regenerate':
      showToast('Fixing validation errors and regenerating...', 'info');
      break;
    case 'send-failures':
      showToast('Failures sent to AI for analysis', 'info');
      break;
    case 'approve-outputs':
      confirmAction('Approve validated outputs for target system?', () => {
        showToast('Outputs approved — committing to target system', 'success');
        setTimeout(() => { window.location.href = 'reports.html'; }, 1000);
      });
      break;
    case 'open-repo':
      showToast('Opening target repository...', 'info');
      break;
    case 'download-docs':
      showToast('Documentation download started', 'success');
      break;
    case 'view-diff':
      showToast('Loading diff view...', 'info');
      break;
    case 'view-all':
      showToast('Loading all projects...', 'info');
      break;
    case 'reset-db':
      confirmAction('Reset all data to defaults?', () => {
        LocalDB.reset();
        showToast('Database reset', 'success');
        setTimeout(() => window.location.reload(), 800);
      });
      break;
    case 'connect-repo':
      showToast('Repository connected', 'success');
      break;
    case 'tab-file-explorer':
    case 'tab-dependency-graph':
    case 'tab-documentation':
      document.querySelectorAll('.ca-tab').forEach((t) => t.classList.remove('active'));
      btn.classList.add('active');
      showToast('Switched to ' + btn.textContent.trim(), 'info');
      break;
    case 'cancel-approve':
      showToast('Approval cancelled', 'info');
      break;
    default:
      break;
  }
});

// Sidebar nav active state
document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach((i) => i.classList.remove('active'));
    item.classList.add('active');
  });
});

// Toggle switches
document.addEventListener('click', (e) => {
  const toggle = e.target.closest('.toggle');
  if (toggle) toggle.classList.toggle('on');
});

// Drop zone
document.addEventListener('DOMContentLoaded', () => {
  const dz = document.getElementById('dropZone');
  if (dz) {
    dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', (e) => {
      e.preventDefault();
      dz.classList.remove('dragover');
      showToast('Files added to upload queue', 'success');
    });
  }

  // Form validation on submit
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (validateForm(form)) {
        showToast('Form submitted successfully', 'success');
      } else {
        showToast('Please fill in all required fields', 'error');
      }
    });
  });

  // Search input
  const searchInput = document.querySelector('.topbar-search input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && searchInput.value.trim()) {
        showToast('Searching for "' + searchInput.value.trim() + '"...', 'info');
      }
    });
  }
});

// Init
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.stat-value[data-count]').forEach(animateCount);
  animateBars();
});
