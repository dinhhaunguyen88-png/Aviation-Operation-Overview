/**
 * Aircraft Swap Analysis Dashboard - JavaScript Controller
 * Wires static template to dynamic API data.
 */

// =====================================================
// Configuration
// =====================================================

const SWAP_API = '';  // Same origin
const SWAP_REFRESH = 60000;  // 60 seconds

// State
const swapState = {
    period: '7d',
    page: 1,
    perPage: 10,
    categoryFilter: '',
    totalEvents: 0,
    isLoading: false
};

let refreshTimer = null;

// =====================================================
// API Helper
// =====================================================

async function swapApi(endpoint) {
    const url = `${SWAP_API}${endpoint}`;
    const res = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': window.API_KEY || ''
        }
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error || 'API error');
    return json.data;
}

// =====================================================
// KPI Summary Cards
// =====================================================

async function loadSwapSummary() {
    const ids = ['kpi-total-swaps', 'kpi-impacted-flights', 'kpi-avg-time', 'kpi-recovery-rate'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.classList.add('animate-pulse'); });

    try {
        const data = await swapApi(`/api/swap/summary?period=${swapState.period}`);

        setText('kpi-total-swaps', data.total_swaps ?? 0);
        setText('kpi-impacted-flights', data.impacted_flights ?? 0);
        setText('kpi-avg-time', (data.avg_delay_hours ?? 0).toFixed(1) + 'h');
        setText('kpi-recovery-rate', (data.recovery_rate ?? 0).toFixed(1) + '%');

        // Trend indicator
        const trend = data.trend_vs_last_period ?? 0;
        const trendEl = document.getElementById('kpi-trend');
        if (trendEl) {
            const isUp = trend > 0;
            const arrow = isUp ? '↑' : trend < 0 ? '↓' : '→';
            trendEl.textContent = `${arrow} ${Math.abs(trend).toFixed(1)}% from last period`;
            trendEl.className = `text-xs mt-1 ${isUp ? 'text-secondary' : 'text-primary'}`;
        }
    } catch (e) {
        console.error('Swap summary failed:', e);
    } finally {
        ids.forEach(id => { const el = document.getElementById(id); if (el) el.classList.remove('animate-pulse'); });
    }
}

// =====================================================
// Swap Reasons Breakdown
// =====================================================

const REASON_COLORS = {
    'MAINTENANCE': { bar: 'bg-secondary', text: 'text-secondary' },
    'WEATHER': { bar: 'bg-primary', text: 'text-primary' },
    'CREW': { bar: 'bg-[#f59e0b]', text: 'text-[#f59e0b]' },
    'OPERATIONAL': { bar: 'bg-[#8aa3a6]', text: 'text-[#8aa3a6]' },
    'UNKNOWN': { bar: 'bg-[#64748b]', text: 'text-[#64748b]' }
};

async function loadSwapReasons() {
    try {
        const data = await swapApi(`/api/swap/reasons?period=${swapState.period}`);
        const container = document.getElementById('reasons-container');
        if (!container) return;

        const reasons = data.reasons || [];

        if (reasons.length === 0) {
            container.innerHTML = '<p class="text-sm text-[#8aa3a6] text-center py-4">No swap data for this period</p>';
            return;
        }

        container.innerHTML = reasons.map(r => {
            const colors = REASON_COLORS[r.category] || REASON_COLORS['UNKNOWN'];
            const pct = r.percentage || 0;
            return `
                <div class="flex items-center gap-4">
                    <span class="w-24 text-sm text-[#8aa3a6]">${capitalize(r.category)}</span>
                    <div class="flex-1 h-6 bg-[#1e293b] rounded-full relative overflow-hidden">
                        <div class="absolute inset-y-0 left-0 ${colors.bar} rounded-full transition-all duration-500" style="width: ${pct}%"></div>
                    </div>
                    <span class="w-16 text-sm font-bold text-right">${pct}% <span class="text-[#8aa3a6] font-normal">(${r.count})</span></span>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Swap reasons failed:', e);
    }
}

// =====================================================
// Top Impacted Tails
// =====================================================

async function loadTopTails() {
    try {
        const data = await swapApi(`/api/swap/top-tails?period=${swapState.period}&limit=5`);
        const container = document.getElementById('top-tails-container');
        if (!container) return;

        const tails = data.tails || [];

        if (tails.length === 0) {
            container.innerHTML = '<p class="text-sm text-[#8aa3a6] text-center py-4">No tail data for this period</p>';
            return;
        }

        const rankColors = ['text-secondary', 'text-[#f59e0b]', 'text-primary', 'text-[#8aa3a6]', 'text-[#64748b]'];
        const badgeColors = {
            'Critical': 'bg-secondary/20 text-secondary',
            'High': 'bg-[#f59e0b]/20 text-[#f59e0b]',
            'Normal': 'bg-primary/20 text-primary'
        };

        container.innerHTML = tails.map((t, i) => {
            const rankColor = rankColors[i] || rankColors[4];
            const badge = badgeColors[t.severity] || badgeColors['Normal'];
            return `
                <div class="flex items-center justify-between p-3 bg-[#263537]/50 rounded-lg hover:bg-[#263537] transition-colors">
                    <div class="flex items-center gap-4">
                        <span class="text-2xl font-bold ${rankColor}">${i + 1}</span>
                        <div>
                            <span class="text-sm font-bold text-white">${t.reg || '-'}</span>
                            <span class="text-xs text-[#8aa3a6] ml-2">${t.ac_type || ''}</span>
                        </div>
                    </div>
                    <span class="${badge} px-3 py-1 rounded text-xs font-bold">${t.swap_count} swaps</span>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Top tails failed:', e);
    }
}

// =====================================================
// Swap Event Log Table
// =====================================================

const REASON_BADGE = {
    'MAINTENANCE': 'bg-secondary/20 text-secondary',
    'WEATHER': 'bg-primary/20 text-primary',
    'CREW': 'bg-[#f59e0b]/20 text-[#f59e0b]',
    'OPERATIONAL': 'bg-[#8aa3a6]/20 text-[#8aa3a6]',
    'UNKNOWN': 'bg-[#64748b]/20 text-[#64748b]'
};

const STATUS_BADGE = {
    'RECOVERED': 'bg-primary/20 text-primary',
    'DELAYED': 'bg-[#f59e0b]/20 text-[#f59e0b]',
    'ON_TIME': 'bg-primary/20 text-primary',
    'PENDING': 'bg-[#8aa3a6]/20 text-[#8aa3a6]'
};

async function loadSwapEvents() {
    try {
        let url = `/api/swap/events?period=${swapState.period}&page=${swapState.page}&per_page=${swapState.perPage}`;
        if (swapState.categoryFilter) {
            url += `&category=${swapState.categoryFilter}`;
        }

        const data = await swapApi(url);
        const tbody = document.getElementById('swap-events-tbody');
        const paginationInfo = document.getElementById('pagination-info');
        if (!tbody) return;

        const events = data.events || [];
        swapState.totalEvents = data.total || 0;

        if (events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-8 text-center text-[#8aa3a6]">No swap events for this period</td></tr>';
        } else {
            tbody.innerHTML = events.map(ev => {
                const reasonBadge = REASON_BADGE[ev.swap_category] || REASON_BADGE['UNKNOWN'];
                const statusBadge = STATUS_BADGE[ev.recovery_status] || STATUS_BADGE['PENDING'];
                const delay = ev.delay_minutes;
                const delayText = delay > 0 ? `+${delay} min` : delay < 0 ? `${delay} min` : 'On-time';
                const delayColor = delay > 0 ? 'text-secondary' : delay < 0 ? 'text-secondary' : 'text-primary';

                return `
                    <tr class="hover:bg-primary/5 transition-colors">
                        <td class="px-6 py-4 font-mono text-sm text-primary">#${ev.swap_event_id || '-'}</td>
                        <td class="px-6 py-4 font-mono text-sm">${ev.flight_number || '-'}</td>
                        <td class="px-6 py-4 text-sm">${ev.original_reg || '-'}</td>
                        <td class="px-6 py-4 text-sm">${ev.swapped_reg || '-'}</td>
                        <td class="px-6 py-4">
                            <span class="${reasonBadge} text-xs px-2 py-1 rounded">${capitalize(ev.swap_category || 'Unknown')}</span>
                        </td>
                        <td class="px-6 py-4 text-sm ${delayColor}">${delayText}</td>
                        <td class="px-6 py-4">
                            <span class="${statusBadge} text-xs px-2 py-1 rounded font-bold">${capitalize(ev.recovery_status || 'Pending')}</span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        // Update pagination
        renderPagination();

    } catch (e) {
        console.error('Swap events failed:', e);
    }
}

// =====================================================
// Pagination
// =====================================================

function renderPagination() {
    const info = document.getElementById('pagination-info');
    const controls = document.getElementById('pagination-controls');
    if (!info || !controls) return;

    const total = swapState.totalEvents;
    const start = (swapState.page - 1) * swapState.perPage + 1;
    const end = Math.min(swapState.page * swapState.perPage, total);
    const totalPages = Math.ceil(total / swapState.perPage) || 1;

    info.textContent = total > 0
        ? `Showing ${start}-${end} of ${total} swap events`
        : 'No swap events';

    let html = '';
    // Previous button
    html += `<button onclick="changePage(${swapState.page - 1})" ${swapState.page <= 1 ? 'disabled' : ''}
        class="px-3 py-1 rounded border border-[#263537] text-xs ${swapState.page <= 1 ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#263537]'}">Previous</button>`;

    // Page buttons (show max 5)
    const startPage = Math.max(1, swapState.page - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    for (let p = startPage; p <= endPage; p++) {
        if (p === swapState.page) {
            html += `<button class="px-3 py-1 rounded bg-primary text-[#111f22] text-xs font-bold">${p}</button>`;
        } else {
            html += `<button onclick="changePage(${p})" class="px-3 py-1 rounded border border-[#263537] text-xs hover:bg-[#263537]">${p}</button>`;
        }
    }

    // Next button
    html += `<button onclick="changePage(${swapState.page + 1})" ${swapState.page >= totalPages ? 'disabled' : ''}
        class="px-3 py-1 rounded border border-[#263537] text-xs ${swapState.page >= totalPages ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#263537]'}">Next</button>`;

    controls.innerHTML = html;
}

function changePage(page) {
    if (page < 1) return;
    const totalPages = Math.ceil(swapState.totalEvents / swapState.perPage) || 1;
    if (page > totalPages) return;
    swapState.page = page;
    loadSwapEvents();
}

// =====================================================
// Period Selector
// =====================================================

function setPeriod(period) {
    swapState.period = period;
    swapState.page = 1;  // Reset pagination

    // Update button styles
    document.querySelectorAll('[data-period]').forEach(btn => {
        if (btn.dataset.period === period) {
            btn.className = 'px-4 py-1.5 rounded-md text-xs font-bold bg-primary text-[#111f22]';
        } else {
            btn.className = 'px-4 py-1.5 rounded-md text-xs font-bold text-[#8aa3a6] hover:text-white transition-colors';
        }
    });

    refreshSwapData();
}

// =====================================================
// Category Filter
// =====================================================

function toggleCategoryFilter() {
    const dropdown = document.getElementById('category-dropdown');
    if (dropdown) dropdown.classList.toggle('hidden');
}

function setCategory(category) {
    swapState.categoryFilter = category;
    swapState.page = 1;

    // Update filter button label
    const label = document.getElementById('filter-label');
    if (label) label.textContent = category ? capitalize(category) : 'Filter';

    // Close dropdown
    const dropdown = document.getElementById('category-dropdown');
    if (dropdown) dropdown.classList.add('hidden');

    loadSwapEvents();
}

// =====================================================
// CSV Export
// =====================================================

async function exportSwapCSV() {
    try {
        let url = `/api/swap/events?period=${swapState.period}&page=1&per_page=1000`;
        if (swapState.categoryFilter) url += `&category=${swapState.categoryFilter}`;

        const data = await swapApi(url);
        const events = data.events || [];

        if (events.length === 0) {
            alert('No data to export');
            return;
        }

        // Build CSV
        const headers = ['Event ID', 'Date', 'Flight', 'Departure', 'Arrival', 'Original A/C', 'Swapped A/C', 'Reason', 'Delay (min)', 'Status'];
        const rows = events.map(e => [
            e.swap_event_id,
            e.flight_date,
            e.flight_number,
            e.departure,
            e.arrival,
            e.original_reg,
            e.swapped_reg,
            e.swap_category,
            e.delay_minutes,
            e.recovery_status
        ]);

        let csv = headers.join(',') + '\n';
        rows.forEach(r => { csv += r.map(v => `"${v ?? ''}"`).join(',') + '\n'; });

        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `swap_events_${swapState.period}_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(link.href);
    } catch (e) {
        console.error('Export failed:', e);
        alert('Export failed: ' + e.message);
    }
}

// =====================================================
// Refresh All Sections
// =====================================================

async function refreshSwapData() {
    if (swapState.isLoading) return;
    swapState.isLoading = true;

    try {
        await Promise.all([
            loadSwapSummary(),
            loadSwapReasons(),
            loadTopTails(),
            loadSwapEvents()
        ]);
    } catch (e) {
        console.error('Refresh failed:', e);
    } finally {
        swapState.isLoading = false;
    }
}

// =====================================================
// Utilities
// =====================================================

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

// =====================================================
// Initialize
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initial data load
    refreshSwapData();

    // Auto-refresh every 60s
    refreshTimer = setInterval(refreshSwapData, SWAP_REFRESH);

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('category-dropdown');
        const filterBtn = document.getElementById('filter-btn');
        if (dropdown && filterBtn && !filterBtn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    console.log('Aircraft Swap Dashboard initialized');
});
