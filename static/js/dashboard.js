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



        // Update last sync time
        const syncEl = document.getElementById('last-sync');
        if (syncEl) {
            syncEl.textContent = `Last sync: ${new Date().toLocaleTimeString('vi-VN')}`;
        }

        // Update Charts
        console.log('[DEBUG] loadDashboardSummary - slots_by_base:', JSON.stringify(data.slots_by_base));
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
// Departure Slots Bar Chart (Pure CSS)
// =====================================================

function renderSlotsBarChart(slotsData) {
    const container = document.getElementById('slots-bar-chart');
    const xAxisContainer = document.getElementById('slots-x-axis');

    if (!container || !slotsData) {
        console.log('[DEBUG] renderSlotsBarChart: container or data missing');
        return;
    }

    const sgn = slotsData.SGN || Array(24).fill(0);
    const han = slotsData.HAN || Array(24).fill(0);
    const dad = slotsData.DAD || Array(24).fill(0);

    // Find max value for scaling
    const allValues = [...sgn, ...han, ...dad];
    const maxVal = Math.max(...allValues, 1); // At least 1 to avoid division by zero

    console.log('[DEBUG] renderSlotsBarChart - max:', maxVal, 'SGN total:', sgn.reduce((a, b) => a + b, 0));

    // Clear container
    container.innerHTML = '';
    xAxisContainer.innerHTML = '';

    // Only show hours 4-23 (operational hours)
    const startHour = 4;
    const endHour = 23;
    const containerHeight = 130; // pixels

    for (let hour = startHour; hour <= endHour; hour++) {
        // Create wrapper with label + bars
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0; height: 100%;';

        // Total count label on top
        const sgnVal = sgn[hour] || 0;
        const hanVal = han[hour] || 0;
        const dadVal = dad[hour] || 0;
        const totalVal = sgnVal + hanVal + dadVal;

        const countLabel = document.createElement('div');
        countLabel.style.cssText = 'font-size: 0.6rem; color: rgba(255,255,255,0.7); margin-bottom: 2px; height: 14px;';
        countLabel.textContent = totalVal > 0 ? totalVal : '';

        // Bar group
        const group = document.createElement('div');
        group.style.cssText = 'display: flex; gap: 1px; align-items: flex-end; flex: 1; width: 100%;';

        // SGN bar (red) - use PIXEL heights
        const sgnHeightPx = Math.max((sgnVal / maxVal) * containerHeight, sgnVal > 0 ? 5 : 0);
        const sgnBar = document.createElement('div');
        sgnBar.style.cssText = `flex: 1; background: #ef4444; height: ${sgnHeightPx}px; border-radius: 2px 2px 0 0; transition: height 0.3s ease; cursor: pointer;`;
        sgnBar.title = `SGN ${hour}:00 - ${sgnVal} flights`;

        // HAN bar (yellow)
        const hanHeightPx = Math.max((hanVal / maxVal) * containerHeight, hanVal > 0 ? 5 : 0);
        const hanBar = document.createElement('div');
        hanBar.style.cssText = `flex: 1; background: #eab308; height: ${hanHeightPx}px; border-radius: 2px 2px 0 0; transition: height 0.3s ease; cursor: pointer;`;
        hanBar.title = `HAN ${hour}:00 - ${hanVal} flights`;

        // DAD bar (blue)
        const dadHeightPx = Math.max((dadVal / maxVal) * containerHeight, dadVal > 0 ? 5 : 0);
        const dadBar = document.createElement('div');
        dadBar.style.cssText = `flex: 1; background: #3b82f6; height: ${dadHeightPx}px; border-radius: 2px 2px 0 0; transition: height 0.3s ease; cursor: pointer;`;
        dadBar.title = `DAD ${hour}:00 - ${dadVal} flights`;

        group.appendChild(sgnBar);
        group.appendChild(hanBar);
        group.appendChild(dadBar);

        wrapper.appendChild(countLabel);
        wrapper.appendChild(group);
        container.appendChild(wrapper);

        // X-axis label (show every 2 hours)
        const label = document.createElement('div');
        label.style.cssText = 'flex: 1; text-align: center; min-width: 0;';
        label.textContent = hour % 2 === 0 ? `${hour}:00` : '';
        xAxisContainer.appendChild(label);
    }
}

function updateCharts(data) {
    if (!data) return;

    // Render CSS-based bar chart
    if (data.slots_by_base) {
        console.log('[DEBUG] updateCharts - SGN[0]:', data.slots_by_base.SGN?.[0], 'max SGN:', Math.max(...(data.slots_by_base.SGN || [])));
        renderSlotsBarChart(data.slots_by_base);
    } else {
        console.log('[DEBUG] updateCharts - slots_by_base is NULL or UNDEFINED');
    }
}

function initCharts() {
    // No longer using Chart.js - using pure CSS bars
    console.log('[DEBUG] initCharts - using CSS bar chart (no Chart.js needed)');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeDashboard);


// =====================================================
// Aircraft Modal Functions
// =====================================================

function openAircraftModal() {
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadAircraftData();
    }
}

function closeAircraftModal() {
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadAircraftData() {
    const tbody = document.getElementById('aircraft-table-body');
    const totalSpan = document.getElementById('aircraft-total');
    const typeFilter = document.getElementById('ac-type-filter');
    const selectedType = typeFilter ? typeFilter.value : '';

    try {
        const data = await apiCall(`/api/aircraft/daily-summary?date=${state.selectedDate}`);

        if (!data.aircraft || data.aircraft.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No aircraft data</td></tr>';
            totalSpan.textContent = 'Total: 0 aircraft';
            return;
        }

        // Filter by selected type
        let filteredAircraft = data.aircraft;
        if (selectedType) {
            filteredAircraft = data.aircraft.filter(ac => {
                // Exact match for type (case insensitive)
                const acType = (ac.type || '').toString().toUpperCase().trim();
                const filterType = selectedType.toUpperCase().trim();
                return acType === filterType;
            });
        }

        let html = '';
        filteredAircraft.forEach(ac => {
            const statusClass = ac.status === 'FLYING' ? 'status-active' : 'status-ground';
            const statusIcon = ac.status === 'FLYING' ? '✈️' : '🅿️';

            html += `
                <tr data-type="${ac.type}">
                    <td><strong>${ac.reg}</strong></td>
                    <td>${ac.type}</td>
                    <td style="text-align: center;">${ac.flight_count}</td>
                    <td style="text-align: center;">${ac.block_hours}h</td>
                    <td style="text-align: center;">${ac.utilization}%</td>
                    <td>${ac.first_flight} → ${ac.last_flight}</td>
                    <td class="${statusClass}">${statusIcon} ${ac.status}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html || '<tr><td colspan="7" style="text-align: center;">No matching aircraft</td></tr>';
        totalSpan.textContent = `Showing: ${filteredAircraft.length} / ${data.total} aircraft`;

    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #ff6b6b;">Failed to load data</td></tr>';
    }
}

// Setup Aircraft Modal Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Click on Aircraft Operation card
    const acCard = document.getElementById('aircraft-operation-card');
    if (acCard) {
        acCard.addEventListener('click', openAircraftModal);
    }

    // Close button
    const closeBtn = document.getElementById('close-aircraft-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeAircraftModal);
    }

    // Click outside to close
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAircraftModal();
            }
        });
    }

    // Type filter change
    const typeFilter = document.getElementById('ac-type-filter');
    if (typeFilter) {
        typeFilter.addEventListener('change', loadAircraftData);
    }
});
