/**
 * FTL List - Crew Flight Time Limitations
 * Full implementation with search, filters, sort, pagination, export, KPI cards
 */

// =========================================================
// State
// =========================================================
let state = {
    page: 1,
    perPage: 25,
    search: '',
    level: 'all',
    base: '',
    sortBy: 'hours_28_day',
    sortOrder: 'desc',
    isLoading: false,
    totalCrew: 0,
    kpiData: { NORMAL: 0, WARNING: 0, CRITICAL: 0, total: 0 }
};

// =========================================================
// API Functions
// =========================================================

async function fetchCrewData() {
    if (state.isLoading) return;
    state.isLoading = true;
    showLoading();

    try {
        const params = new URLSearchParams({
            page: state.page,
            per_page: state.perPage,
            sort_by: state.sortBy,
            sort_order: state.sortOrder
        });

        // Only add non-empty filters
        if (state.search) params.set('search', state.search);
        if (state.level && state.level !== 'all') params.set('level', state.level);
        if (state.base) params.set('base', state.base);

        const response = await fetch(`/api/crew?${params.toString()}`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            renderTable(data.crew);
            updatePagination(data.total, data.page, data.per_page);
            updateStats(data.total);
            state.totalCrew = data.total;
        } else {
            console.error('Fetch error:', result.error);
            showError('Failed to load crew data');
        }
    } catch (error) {
        console.error('API Error:', error);
        showError('Connection error. Please retry.');
    } finally {
        state.isLoading = false;
        hideLoading();
    }
}

async function fetchKPISummary() {
    try {
        const response = await fetch('/api/ftl/summary', {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            state.kpiData = {
                NORMAL: data.by_level?.NORMAL || 0,
                WARNING: data.by_level?.WARNING || 0,
                CRITICAL: data.by_level?.CRITICAL || 0,
                total: data.total_crew || 0
            };
            updateKPICards();
            updateComplianceStatus(data.compliance_rate);
        }
    } catch (error) {
        console.error('KPI fetch error:', error);
    }
}

// =========================================================
// Render Functions
// =========================================================

function renderTable(crew) {
    const tbody = document.getElementById('ftl-list-tbody');

    if (!crew || crew.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7">
                    <div class="empty-state">
                        <span class="empty-icon">📋</span>
                        <p>No crew members match your filters.</p>
                        <button class="btn btn-secondary btn-sm" onclick="resetFilters()">Reset Filters</button>
                    </div>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = crew.map(c => {
        const ftl = c.crew_flight_hours && c.crew_flight_hours.length > 0 && c.crew_flight_hours[0]
            ? c.crew_flight_hours[0]
            : { hours_28_day: 0, hours_12_month: 0, warning_level: 'NORMAL' };

        const hours28d = ftl.hours_28_day || 0;
        const hours12m = ftl.hours_12_month || 0;
        const level = ftl.warning_level || 'NORMAL';

        // Calculate progress percentages
        const pct28d = Math.min((hours28d / 100) * 100, 100);
        const pct12m = Math.min((hours12m / 1000) * 100, 100);

        return `
            <tr class="crew-row" onclick="viewCrewDetail('${c.crew_id}')">
                <td><strong class="crew-id">${c.crew_id}</strong></td>
                <td>${c.crew_name || 'N/A'}</td>
                <td>${(c.base || '-').trim()}</td>
                <td class="hours-cell">
                    <div class="hours-bar-container">
                        <div class="hours-bar hours-bar-${getBarColorClass(pct28d)}" style="width: ${pct28d}%"></div>
                        <span class="hours-value">${hours28d.toFixed(1)}</span>
                    </div>
                </td>
                <td class="hours-cell">
                    <div class="hours-bar-container">
                        <div class="hours-bar hours-bar-${getBarColorClass(pct12m)}" style="width: ${pct12m}%"></div>
                        <span class="hours-value">${hours12m.toFixed(1)}</span>
                    </div>
                </td>
                <td><span class="badge badge-${getWarningBadgeClass(level)}">${level}</span></td>
                <td class="actions-cell">
                    <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); viewCrewDetail('${c.crew_id}')">Details</button>
                </td>
            </tr>
        `;
    }).join('');
}

function updatePagination(total, page, perPage) {
    const totalPages = Math.ceil(total / perPage) || 1;
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    pageInfo.textContent = `Page ${page} of ${totalPages}`;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= totalPages;
}

function updateStats(total) {
    document.getElementById('total-crew-count').textContent = `Total: ${total} crew`;
}

function updateKPICards() {
    const { NORMAL, WARNING, CRITICAL, total } = state.kpiData;

    document.getElementById('kpi-total-value').textContent = total;
    document.getElementById('kpi-normal-value').textContent = NORMAL;
    document.getElementById('kpi-warning-value').textContent = WARNING;
    document.getElementById('kpi-critical-value').textContent = CRITICAL;
}

function updateComplianceStatus(rate) {
    const el = document.getElementById('compliance-status');
    if (el && rate !== undefined) {
        el.textContent = `${rate}%`;
        el.className = rate >= 95 ? 'compliance-good' : rate >= 80 ? 'compliance-warn' : 'compliance-bad';
    }
}

// =========================================================
// UI Helper Functions
// =========================================================

function getWarningBadgeClass(level) {
    switch (level) {
        case 'CRITICAL': return 'danger';
        case 'WARNING': return 'warning';
        default: return 'success';
    }
}

function getBarColorClass(pct) {
    if (pct >= 95) return 'critical';
    if (pct >= 85) return 'warning';
    return 'normal';
}

function showLoading() {
    const overlay = document.getElementById('table-loading');
    if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('table-loading');
    if (overlay) overlay.style.display = 'none';
}

function showError(msg) {
    const tbody = document.getElementById('ftl-list-tbody');
    tbody.innerHTML = `
        <tr class="empty-row">
            <td colspan="7">
                <div class="empty-state error-state">
                    <span class="empty-icon">❌</span>
                    <p>${msg}</p>
                    <button class="btn btn-primary btn-sm" onclick="fetchCrewData()">Retry</button>
                </div>
            </td>
        </tr>`;
}

function viewCrewDetail(crewId) {
    window.location.href = `/crew_detail.html?id=${crewId}`;
}

// =========================================================
// Filter & Sort Functions
// =========================================================

function resetFilters() {
    document.getElementById('crew-search').value = '';
    document.getElementById('filter-base').value = '';
    document.querySelectorAll('#filter-level .toggle-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-level="all"]').classList.add('active');

    state = {
        ...state,
        page: 1,
        search: '',
        level: 'all',
        base: '',
        sortBy: 'hours_28_day',
        sortOrder: 'desc'
    };

    // Reset sort indicators
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });

    fetchCrewData();
}

function exportFTL() {
    const levelParam = state.level && state.level !== 'all' ? `?level=${state.level}` : '';
    window.location.href = `/api/ftl/export${levelParam}`;
}

// =========================================================
// Event Listeners
// =========================================================

function setupEventListeners() {
    // Search (debounced 300ms)
    let searchTimeout;
    document.getElementById('crew-search').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.search = e.target.value.trim();
            state.page = 1;
            fetchCrewData();
        }, 300);
    });

    // Level Filter Toggle
    document.querySelectorAll('#filter-level .toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#filter-level .toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.level = btn.dataset.level;
            state.page = 1;
            fetchCrewData();
        });
    });

    // Base Dropdown
    document.getElementById('filter-base').addEventListener('change', (e) => {
        state.base = e.target.value;
        state.page = 1;
        fetchCrewData();
    });

    // Reset Button
    document.getElementById('reset-filters').addEventListener('click', resetFilters);

    // Export Button
    document.getElementById('export-ftl-btn').addEventListener('click', exportFTL);

    // Sortable Headers
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;

            if (state.sortBy === field) {
                state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
            } else {
                state.sortBy = field;
                state.sortOrder = 'desc';
            }

            // Update sort indicators
            document.querySelectorAll('.sortable').forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            th.classList.add(state.sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');

            state.page = 1;
            fetchCrewData();
        });
    });

    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => {
        if (state.page > 1) {
            state.page--;
            fetchCrewData();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(state.totalCrew / state.perPage);
        if (state.page < totalPages) {
            state.page++;
            fetchCrewData();
        }
    });
}

// =========================================================
// Initialization
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();

    // Load data
    fetchCrewData();
    fetchKPISummary();

    // Update timestamp
    document.getElementById('last-update').textContent =
        `Last update: ${new Date().toLocaleString('vi-VN')}`;
});
