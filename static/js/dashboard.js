/**
 * Aviation Operations Dashboard - JavaScript
 * Phase 3: Core Features
 */

// =====================================================
// Configuration
// =====================================================

const API_BASE = '';  // Same origin
const REFRESH_INTERVAL = 60000;  // 1 minute

// State
let state = {
    selectedDate: new Date().toISOString().split('T')[0],
    dataSource: 'AIMS',
    baseFilter: '',
    aircraftFilter: '',
    isLoading: false
};

// =====================================================
// Utility Functions
// =====================================================

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function formatTime(timeStr) {
    if (!timeStr) return '--:--';
    return timeStr.substring(0, 5);
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

async function apiCall(endpoint, options = {}) {
    try {
        const url = `${API_BASE}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'API request failed');
        }

        return data.data;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// =====================================================
// Dashboard Data Loading
// =====================================================

async function loadDashboardSummary() {
    try {
        const data = await apiCall(`/api/dashboard/summary?date=${state.selectedDate}`);

        // Update KPI cards
        const updateKPI = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        updateKPI('total-crew', data.total_crew || 0);
        updateKPI('total-ac-operation', data.total_aircraft_operation || 0);

        // KPI 3: A/C Breakdown (Use innerHTML for formatting)
        const acEl = document.getElementById('ac-type-hour');
        if (acEl) acEl.innerHTML = data.ac_type_breakdown || (data.total_block_hours || 0).toFixed(1);

        // KPI 4: Total Completed Flights
        updateKPI('total-completed', data.total_completed_flights || 0);

        updateKPI('total-flights', data.total_flights || 0);
        updateKPI('total-block-hours', (data.total_block_hours || 0).toFixed(1));
        updateKPI('pax-load', data.total_pax ? data.total_pax.toLocaleString() : '0');
        updateKPI('otp-percent', (data.otp_percentage || 0).toFixed(1) + '%');

        // Update alerts
        const alertSection = document.getElementById('alerts-section');
        const alertCount = document.getElementById('alerts-count');
        if (data.alerts && data.alerts.length > 0) {
            if (alertSection) alertSection.style.display = 'block';
            if (alertCount) alertCount.textContent = data.alerts_count;
            renderAlerts(data.alerts);
        } else {
            if (alertSection) alertSection.style.display = 'none';
        }

        // Update last sync time
        const syncEl = document.getElementById('last-sync');
        if (syncEl) {
            syncEl.textContent = `Last sync: ${new Date().toLocaleTimeString('vi-VN')}`;
        }

        // Update Charts
        updateCharts(data);

    } catch (error) {
        console.error('Failed to load dashboard summary:', error);
    }
}

async function loadStandbyData() {
    try {
        const data = await apiCall(`/api/standby?date=${state.selectedDate}`);

        // Update standby stats
        const byStatus = data.by_status || {};
        const updateStat = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        updateStat('sby-available', (byStatus.SBY?.count) || 0);
        updateStat('sl-count', (byStatus.SL?.count) || 0);
        updateStat('csl-count', (byStatus.CSL?.count) || 0);

        // Render standby list
        const listContainer = document.getElementById('standby-list');
        if (listContainer) {
            const standbyItems = data.standby || [];
            if (standbyItems.length > 0) {
                listContainer.innerHTML = standbyItems.map(item => `
                    <div class="standby-item">
                        <span>${item.crew_name || item.crew_id}</span>
                        <span class="badge badge-${item.status === 'SBY' ? 'success' : 'warning'}">${item.status}</span>
                    </div>
                `).join('');
            } else {
                listContainer.innerHTML = '<div class="empty-state">No standby data for this date</div>';
            }
        }

    } catch (error) {
        console.error('Failed to load standby data:', error);
    }
}

async function loadFTLSummary() {
    try {
        const data = await apiCall(`/api/ftl/summary?date=${state.selectedDate}`);

        // Update FTL stats
        const updateStat = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        updateStat('ftl-normal', data.by_level?.NORMAL || 0);
        updateStat('ftl-warning', data.by_level?.WARNING || 0);
        updateStat('ftl-critical', data.by_level?.CRITICAL || 0);

        // Update compliance rate
        const complianceRate = data.compliance_rate || 100;
        const rateEl = document.getElementById('compliance-rate');
        if (rateEl) {
            rateEl.textContent = `${complianceRate}%`;
            rateEl.className = 'badge';
            if (complianceRate >= 95) {
                rateEl.classList.add('badge-success');
            } else if (complianceRate >= 85) {
                rateEl.classList.add('badge-warning');
            } else {
                rateEl.classList.add('badge-danger');
            }
        }

        const gaugeEl = document.getElementById('gauge-fill');
        if (gaugeEl) gaugeEl.style.width = `${complianceRate}%`;

        // Render FTL tables
        renderFTLTable('ftl-28d-tbody', data.top_20_28_day || [], 'hours_28_day');
        renderFTLTable('ftl-12m-tbody', data.top_20_12_month || [], 'hours_12_month');

    } catch (error) {
        console.error('Failed to load FTL summary:', error);
    }
}

// Roster Heatmap removed per business requirements

// Crew list logic removed to prioritize operational focus.

async function loadFlights() {
    try {
        let url = `/api/flights?date=${state.selectedDate}`;
        if (state.aircraftFilter) {
            url += `&aircraft_type=${state.aircraftFilter}`;
        }

        const data = await apiCall(url);
        const tbody = document.getElementById('flights-tbody');
        let flights = data.flights || [];

        // Apply +/- 1 hour filter
        const now = new Date();
        const oneHourMs = 60 * 60 * 1000;

        const filteredFlights = flights.filter(f => {
            if (!f.std) return false;

            // Handle ISO string or HH:mm
            let flightTime;
            if (f.std.includes('T')) {
                flightTime = new Date(f.std);
            } else {
                // If only HH:mm, assume today's date
                const [h, m] = f.std.split(':');
                flightTime = new Date();
                flightTime.setHours(h, m, 0, 0);
            }

            const diff = now - flightTime;
            // Include: Future flights within 1 hour AND Completed flights within 1 hour
            // Future: diff is negative (e.g., -30min)
            // Past: diff is positive (e.g., +30min)
            return diff >= -oneHourMs && diff <= oneHourMs;
        });

        // Enforce 20-flight limit and sort by STD
        const displayFlights = filteredFlights
            .sort((a, b) => new Date(a.std) - new Date(b.std))
            .slice(0, 20);

        if (displayFlights.length > 0) {
            tbody.innerHTML = displayFlights.map(flight => `
                <tr>
                    <td>${flight.carrier_code || ''}${flight.flight_number || ''}</td>
                    <td>${flight.departure || ''} → ${flight.arrival || ''}</td>
                    <td>${formatTime(flight.std)}</td>
                    <td>${formatTime(flight.sta)}</td>
                    <td>${flight.aircraft_type || '-'}</td>
                    <td>${flight.aircraft_reg || '-'}</td>
                    <td><span class="badge badge-${getFlightStatusClass(flight.status)}">${flight.status || 'Scheduled'}</span></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No flights within the current 2-hour window (+/- 1h)</td></tr>';
        }

    } catch (error) {
        console.error('Failed to load flights:', error);
        document.getElementById('flights-tbody').innerHTML =
            '<tr class="empty-row"><td colspan="7">Failed to load flight data</td></tr>';
    }
}

// =====================================================
// Render Functions
// =====================================================

function renderAlerts(alerts) {
    const container = document.getElementById('alerts-list');
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.type.includes('CRITICAL') ? 'critical' : 'warning'}">
            <span>${alert.crew_name || alert.crew_id}</span>
            <span>${alert.hours_28_day}h (28d)</span>
        </div>
    `).join('');
}

function renderFTLTable(tbodyId, data, hoursField) {
    const tbody = document.getElementById(tbodyId);

    if (data.length > 0) {
        tbody.innerHTML = data.map((crew, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${crew.crew_name || crew.crew_id}</td>
                <td>${crew[hoursField] || 0}</td>
                <td><span class="badge badge-${getWarningBadgeClass(crew.warning_level)}">${crew.warning_level || 'NORMAL'}</span></td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No data</td></tr>';
    }
}

// =====================================================
// Helper Functions
// =====================================================

function getStatusBadgeClass(status) {
    switch (status) {
        case 'FLY': return 'info';
        case 'SBY': return 'success';
        case 'SL':
        case 'CSL': return 'warning';
        case 'OFF': return 'secondary';
        default: return 'secondary';
    }
}

function getWarningBadgeClass(level) {
    switch (level) {
        case 'NORMAL': return 'success';
        case 'WARNING': return 'warning';
        case 'CRITICAL': return 'danger';
        default: return 'success';
    }
}

function getFlightStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'departed': return 'info';
        case 'arrived': return 'success';
        case 'delayed': return 'warning';
        case 'cancelled': return 'danger';
        default: return 'secondary';
    }
}

// =====================================================
// Data Source Toggle
// =====================================================

async function setDataSource(source) {
    try {
        await apiCall('/api/config/datasource', {
            method: 'POST',
            body: JSON.stringify({ source })
        });

        state.dataSource = source;

        // Update UI
        document.getElementById('btn-aims').classList.toggle('active', source === 'AIMS');
        document.getElementById('btn-csv').classList.toggle('active', source === 'CSV');
        document.getElementById('data-source-label').textContent = `Source: ${source}`;

        // Update sync status
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        if (source === 'AIMS') {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'Connected';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'CSV Mode';
        }

        showToast(`Data source changed to ${source}`, 'success');

        // Reload data
        refreshAll();

    } catch (error) {
        console.error('Failed to set data source:', error);
    }
}

// =====================================================
// Upload Functions
// =====================================================

function openUploadModal() {
    document.getElementById('upload-modal').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.remove('active');
}

async function handleUpload() {
    const fileInput = document.getElementById('csv-file');
    const fileType = document.getElementById('upload-type').value;

    if (!fileInput.files.length) {
        showToast('Please select a file', 'warning');
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', fileType);

    try {
        const response = await fetch('/api/upload/csv', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Uploaded ${result.data.records_count} records`, 'success');
            closeUploadModal();
            refreshAll();
        } else {
            showToast(result.error || 'Upload failed', 'error');
        }

    } catch (error) {
        console.error('Upload failed:', error);
        showToast('Upload failed', 'error');
    }
}

// =====================================================
// Main Functions
// =====================================================

async function refreshAll() {
    if (state.isLoading) return;

    state.isLoading = true;

    try {
        await Promise.all([
            loadDashboardSummary(),
            loadFlights()
        ]);
    } catch (error) {
        console.error('Refresh failed:', error);
    } finally {
        state.isLoading = false;
    }
}

function initializeDashboard() {
    // Set initial date
    const dateInput = document.getElementById('filter-date');
    dateInput.value = state.selectedDate;

    // Event listeners
    dateInput.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        refreshAll();
    });

    document.getElementById('refresh-btn').addEventListener('click', refreshAll);

    document.getElementById('btn-aims').addEventListener('click', () => setDataSource('AIMS'));
    document.getElementById('btn-csv').addEventListener('click', () => setDataSource('CSV'));



    document.getElementById('aircraft-filter').addEventListener('change', (e) => {
        state.aircraftFilter = e.target.value;
        loadFlights();
    });

    // Focus Mode listener
    document.getElementById('focus-mode-btn').addEventListener('click', (e) => {
        const btn = e.currentTarget;
        const section = document.getElementById('charts-section');

        btn.classList.toggle('active');
        section.classList.toggle('hidden');

        // Trigger resize for tables if needed
        window.dispatchEvent(new Event('resize'));
    });

    // Upload modal
    const uploadZone = document.getElementById('upload-zone');
    const csvInput = document.getElementById('csv-file');

    uploadZone.addEventListener('click', () => csvInput.click());
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--primary)';
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--border)';
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--border)';
        if (e.dataTransfer.files.length) {
            csvInput.files = e.dataTransfer.files;
        }
    });

    document.getElementById('modal-close').addEventListener('click', closeUploadModal);
    document.getElementById('cancel-upload').addEventListener('click', closeUploadModal);
    document.getElementById('submit-upload').addEventListener('click', handleUpload);

    // Initial load
    initCharts(); // Initialize charts first
    refreshAll();

    // Auto-refresh
    setInterval(refreshAll, REFRESH_INTERVAL);

    console.log('Dashboard initialized');
}

// =====================================================
// Chart.js Configuration & Logic
// =====================================================

let chartInstances = {
    pulse: null,
    crewMix: null
};

function _unsafeInitCharts() {
    // Shared Options
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = 'Inter';

    // 1. Operational Pulse (Line)
    const ctxPulse = document.getElementById('pulseChart').getContext('2d');
    chartInstances.pulse = new Chart(ctxPulse, {
        type: 'line',
        data: {
            labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
            datasets: [{
                label: 'Flights',
                data: [], // Populated later
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#3b82f6',
                pointRadius: 0,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f8fafc',
                    bodyColor: '#3b82f6',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // 2. Crew Mix (Donut)
    const ctxMix = document.getElementById('crewMixChart').getContext('2d');
    chartInstances.crewMix = new Chart(ctxMix, {
        type: 'doughnut',
        data: {
            labels: ['Flying', 'Standby', 'Sick/CSL', 'Off/Other'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    '#3b82f6', // Fly (Blue)
                    '#10b981', // SBY (Green)
                    '#ef4444', // Sick (Red)
                    '#64748b'  // Off (Gray)
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: { boxWidth: 12, padding: 15 }
                }
            }
        }
    });
}

function _unsafeUpdateCharts(data) {
    if (!data) return;

    // Update Pulse Chart
    if (chartInstances.pulse && data.flights_per_hour) {
        chartInstances.pulse.data.datasets[0].data = data.flights_per_hour;
        chartInstances.pulse.update();
    }

    // Update Crew Mix Chart
    if (chartInstances.crewMix && data.crew_by_status) {
        const stats = data.crew_by_status;
        const flying = stats.FLY || 0;
        const sby = stats.SBY || 0;
        const sick = (stats.SL || 0) + (stats.CSL || 0);
        const other = (stats.OFF || 0) + (stats.LVE || 0) + (stats.TRN || 0) + (stats.OTHER || 0);

        chartInstances.crewMix.data.datasets[0].data = [flying, sby, sick, other];
        chartInstances.crewMix.update();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeDashboard);


// Safe Wrappers for Chart Functions
function initCharts() {
    try {
        if (typeof Chart === 'undefined') { console.warn('Chart.js missing'); return; }
        _unsafeInitCharts();
    } catch (e) { console.error('InitCharts failed:', e); }
}

function updateCharts(data) {
    try {
        _unsafeUpdateCharts(data);
    } catch (e) { console.error('UpdateCharts failed:', e); }
}
