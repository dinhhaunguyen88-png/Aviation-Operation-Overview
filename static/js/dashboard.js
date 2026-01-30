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
        document.getElementById('total-crew').textContent = data.total_crew || 0;
        document.getElementById('standby-count').textContent = data.standby_available || 0;
        document.getElementById('sick-count').textContent = data.sick_leave || 0;
        document.getElementById('active-flights').textContent = data.total_flights || 0;
        document.getElementById('ac-utilization').textContent = data.aircraft_utilization || 0;
        document.getElementById('total-block-hours').textContent = data.total_block_hours || 0;
        
        // Update crew status
        if (data.crew_by_status) {
            document.getElementById('status-fly').textContent = data.crew_by_status.FLY || 0;
            document.getElementById('status-sby').textContent = data.crew_by_status.SBY || 0;
            document.getElementById('status-sl').textContent = data.crew_by_status.SL || 0;
            document.getElementById('status-csl').textContent = data.crew_by_status.CSL || 0;
            document.getElementById('status-off').textContent = data.crew_by_status.OFF || 0;
            document.getElementById('status-trn').textContent = data.crew_by_status.TRN || 0;
        }
        
        // Update alerts
        if (data.alerts && data.alerts.length > 0) {
            document.getElementById('alerts-section').style.display = 'block';
            document.getElementById('alerts-count').textContent = data.alerts_count;
            renderAlerts(data.alerts);
        } else {
            document.getElementById('alerts-section').style.display = 'none';
        }
        
        // Update last sync time
        document.getElementById('last-sync').textContent = 
            `Last sync: ${new Date().toLocaleTimeString('vi-VN')}`;
        
    } catch (error) {
        console.error('Failed to load dashboard summary:', error);
    }
}

async function loadStandbyData() {
    try {
        const data = await apiCall(`/api/standby?date=${state.selectedDate}`);
        
        // Update standby stats
        const byStatus = data.by_status || {};
        document.getElementById('sby-available').textContent = 
            (byStatus.SBY?.count) || 0;
        document.getElementById('sl-count').textContent = 
            (byStatus.SL?.count) || 0;
        document.getElementById('csl-count').textContent = 
            (byStatus.CSL?.count) || 0;
        
        // Render standby list
        const listContainer = document.getElementById('standby-list');
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
        
    } catch (error) {
        console.error('Failed to load standby data:', error);
    }
}

async function loadFTLSummary() {
    try {
        const data = await apiCall(`/api/ftl/summary?date=${state.selectedDate}`);
        
        // Update FTL stats
        document.getElementById('ftl-normal').textContent = data.by_level?.NORMAL || 0;
        document.getElementById('ftl-warning').textContent = data.by_level?.WARNING || 0;
        document.getElementById('ftl-critical').textContent = data.by_level?.CRITICAL || 0;
        
        // Update compliance rate
        const complianceRate = data.compliance_rate || 100;
        document.getElementById('compliance-rate').textContent = `${complianceRate}%`;
        document.getElementById('gauge-fill').style.width = `${complianceRate}%`;
        
        // Update badge color
        const badge = document.getElementById('compliance-rate');
        badge.className = 'badge';
        if (complianceRate >= 95) {
            badge.classList.add('badge-success');
        } else if (complianceRate >= 85) {
            badge.classList.add('badge-warning');
        } else {
            badge.classList.add('badge-danger');
        }
        
        // Render FTL tables
        renderFTLTable('ftl-28d-tbody', data.top_20_28_day || [], 'hours_28_day');
        renderFTLTable('ftl-12m-tbody', data.top_20_12_month || [], 'hours_12_month');
        
    } catch (error) {
        console.error('Failed to load FTL summary:', error);
    }
}

async function loadCrewList() {
    try {
        let url = `/api/crew?date=${state.selectedDate}`;
        if (state.baseFilter) {
            url += `&base=${state.baseFilter}`;
        }
        
        const data = await apiCall(url);
        const tbody = document.getElementById('crew-tbody');
        const crewList = data.crew || [];
        
        if (crewList.length > 0) {
            tbody.innerHTML = crewList.map(crew => `
                <tr>
                    <td>${crew.crew_id}</td>
                    <td>${crew.crew_name || '-'}</td>
                    <td>${crew.base || '-'}</td>
                    <td>${crew.position || '-'}</td>
                    <td><span class="badge badge-${getStatusBadgeClass(crew.status)}">${crew.status || '-'}</span></td>
                    <td>${crew.hours_28_day || '-'}</td>
                    <td><span class="badge badge-${getWarningBadgeClass(crew.warning_level)}">${crew.warning_level || 'NORMAL'}</span></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No crew data available</td></tr>';
        }
        
    } catch (error) {
        console.error('Failed to load crew list:', error);
        document.getElementById('crew-tbody').innerHTML = 
            '<tr class="empty-row"><td colspan="7">Failed to load crew data</td></tr>';
    }
}

async function loadFlights() {
    try {
        let url = `/api/flights?date=${state.selectedDate}`;
        if (state.aircraftFilter) {
            url += `&aircraft_type=${state.aircraftFilter}`;
        }
        
        const data = await apiCall(url);
        const tbody = document.getElementById('flights-tbody');
        const flights = data.flights || [];
        
        if (flights.length > 0) {
            tbody.innerHTML = flights.map(flight => `
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
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No flights for this date</td></tr>';
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
            loadStandbyData(),
            loadFTLSummary(),
            loadCrewList(),
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
    
    document.getElementById('base-filter').addEventListener('change', (e) => {
        state.baseFilter = e.target.value;
        loadCrewList();
    });
    
    document.getElementById('aircraft-filter').addEventListener('change', (e) => {
        state.aircraftFilter = e.target.value;
        loadFlights();
    });
    
    // Crew search
    document.getElementById('crew-search').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#crew-tbody tr:not(.empty-row)');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
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
    refreshAll();
    
    // Auto-refresh
    setInterval(refreshAll, REFRESH_INTERVAL);
    
    console.log('Dashboard initialized');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeDashboard);
