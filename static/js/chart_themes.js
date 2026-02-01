/**
 * Chart.js Theme Configuration for Slate Dark Design System
 * 
 * Colors:
 * - Primary: #22C55E (Emerald-500)
 * - Secondary: #EF4444 (Red-500)
 * - Background: #020617 (Slate-950)
 * - Surface: #0f172a (Slate-900)
 * - Border: #1e293b (Slate-800)
 * - Text: #94a3b8 (Slate-400)
 */

window.ChartTheme = {
    colors: {
        primary: '#22C55E',
        secondary: '#EF4444',
        accentOrange: '#F97316',
        accentBlue: '#3B82F6',
        success: '#22C55E',
        danger: '#EF4444',
        warning: '#EAB308',
        info: '#3B82F6',
        text: '#94a3b8',
        textLight: '#f1f5f9',
        border: '#1e293b',
        surface: '#0f172a',
        background: '#020617'
    },
    
    font: {
        family: "'Fira Sans', sans-serif",
        size: 11,
        weight: 500
    },

    // Common Grid Configuration
    grid: {
        color: '#1e293b',
        borderColor: '#1e293b',
        tickColor: '#1e293b',
        borderDash: [4, 4]
    },

    // Common Tooltip Configuration
    tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        borderColor: '#1e293b',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        boxPadding: 4
    }
};

// Apply global defaults if Chart is available
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = window.ChartTheme.colors.text;
    Chart.defaults.font.family = window.ChartTheme.font.family;
    Chart.defaults.font.size = window.ChartTheme.font.size;
    
    // Line Chart Defaults
    Chart.defaults.elements.line.borderWidth = 2;
    Chart.defaults.elements.line.tension = 0.4; // Smooth curves
    Chart.defaults.elements.point.radius = 0;
    Chart.defaults.elements.point.hoverRadius = 4;
    
    // Bar Chart Defaults
    Chart.defaults.elements.bar.borderRadius = 4;
    Chart.defaults.elements.bar.borderSkipped = false;
    
    // Grid Defaults
    Chart.defaults.scale.grid.color = window.ChartTheme.grid.color;
    Chart.defaults.scale.grid.borderColor = window.ChartTheme.grid.borderColor;
    Chart.defaults.scale.grid.tickColor = window.ChartTheme.grid.tickColor;
    
    // Tooltip Defaults
    Object.assign(Chart.defaults.plugins.tooltip, window.ChartTheme.tooltip);
}
