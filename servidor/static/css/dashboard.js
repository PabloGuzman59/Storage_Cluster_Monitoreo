/* dashboard.js — Auto-refresh y reloj en tiempo real */

let refreshTimer = null;
let countdown    = 0;
let countdownTimer = null;

const select    = document.getElementById('refresh-interval');
const countEl   = document.getElementById('refresh-countdown');
const timeEl    = document.getElementById('current-time');

// ── Reloj ────────────────────────────────────────────────
function updateClock() {
    if (timeEl) {
        timeEl.textContent = new Date().toLocaleString('es-BO');
    }
}
setInterval(updateClock, 1000);
updateClock();

// ── Auto-refresh ─────────────────────────────────────────
function startRefresh(seconds) {
    clearInterval(refreshTimer);
    clearInterval(countdownTimer);
    if (seconds <= 0) { if (countEl) countEl.textContent = ''; return; }

    countdown = seconds;
    if (countEl) countEl.textContent = countdown + 's';

    countdownTimer = setInterval(() => {
        countdown--;
        if (countEl) countEl.textContent = countdown + 's';
        if (countdown <= 0) {
            countdown = seconds;
            refreshPage();
        }
    }, 1000);
}

async function refreshPage() {
    try {
        const [summaryRes, nodesRes] = await Promise.all([
            fetch('/api/summary'),
            fetch('/api/nodes')
        ]);
        const summary = await summaryRes.json();
        const nodes   = await nodesRes.json();
        updateSummaryCards(summary);
        updateNodesTable(nodes);
    } catch (e) {
        console.warn('Auto-refresh error:', e);
    }
}

function updateSummaryCards(s) {
    const grid = document.getElementById('summary-grid');
    if (!grid) return;
    const util = (s.utilization_pct || 0).toFixed(1);
    const utilColor = s.utilization_pct > 80 ? 'card-red' : s.utilization_pct > 60 ? 'card-orange' : 'card-green';
    grid.innerHTML = `
        <div class="card card-blue">
            <div class="card-value">${s.total_nodes || 0}</div>
            <div class="card-label">Total Nodos</div>
        </div>
        <div class="card card-green">
            <div class="card-value">${s.active_nodes || 0}</div>
            <div class="card-label">Nodos Activos</div>
        </div>
        <div class="card card-red">
            <div class="card-value">${s.unreported_nodes || 0}</div>
            <div class="card-label">No Reportan</div>
        </div>
        <div class="card card-gray">
            <div class="card-value">${(s.cluster_total_gb||0).toFixed(1)} GB</div>
            <div class="card-label">Capacidad Total</div>
        </div>
        <div class="card card-orange">
            <div class="card-value">${(s.cluster_used_gb||0).toFixed(1)} GB</div>
            <div class="card-label">Espacio Usado</div>
        </div>
        <div class="card card-teal">
            <div class="card-value">${(s.cluster_free_gb||0).toFixed(1)} GB</div>
            <div class="card-label">Espacio Libre</div>
        </div>
        <div class="card ${utilColor}">
            <div class="card-value">${util}%</div>
            <div class="card-label">Utilización Global</div>
        </div>
    `;
}

function updateNodesTable(nodes) {
    const tbody = document.getElementById('nodes-tbody');
    if (!tbody) return;
    if (!nodes.length) {
        tbody.innerHTML = `<tr><td colspan="13" style="text-align:center;padding:2rem;color:#888;">Esperando conexión de nodos clientes...</td></tr>`;
        return;
    }
    tbody.innerHTML = nodes.map(n => {
        const statusBadge = n.status === 'active'
            ? '<span class="badge badge-active">✅ Activo</span>'
            : n.status === 'no_reporta'
            ? '<span class="badge badge-warn">⚠️ No Reporta</span>'
            : '<span class="badge badge-off">🔴 Desconectado</span>';

        const util = n.utilization != null ? parseFloat(n.utilization) : null;
        const barColor = util > 80 ? 'bar-red' : util > 60 ? 'bar-orange' : 'bar-green';
        const utilCell = util != null
            ? `<div class="progress-bar-container">
                 <div class="progress-bar ${barColor}" style="width:${Math.min(util,100)}%"></div>
                 <span class="progress-label">${util.toFixed(1)}%</span>
               </div>`
            : '—';

        return `<tr class="node-row status-${n.status}">
            <td><strong>${n.client_id}</strong></td>
            <td>${n.region || '—'}</td>
            <td>${n.hostname || '—'}</td>
            <td>${n.ip_address || '—'}</td>
            <td>${statusBadge}</td>
            <td>${n.disk_type || '—'}</td>
            <td>${n.total_gb != null ? parseFloat(n.total_gb).toFixed(1) : '—'}</td>
            <td>${n.used_gb  != null ? parseFloat(n.used_gb).toFixed(1)  : '—'}</td>
            <td>${n.free_gb  != null ? parseFloat(n.free_gb).toFixed(1)  : '—'}</td>
            <td>${utilCell}</td>
            <td>${n.iops || '—'}</td>
            <td class="timestamp">${n.reported_at || n.last_seen_at || '—'}</td>
            <td><a href="/node/${n.client_id}" class="btn-detail">Ver</a></td>
        </tr>`;
    }).join('');
}

// ── Init ─────────────────────────────────────────────────
if (select) {
    select.addEventListener('change', () => startRefresh(parseInt(select.value)));
    startRefresh(parseInt(select.value));
}