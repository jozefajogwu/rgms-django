/* ============================================ */
/* RGMS DASHBOARD - Clinical Chart Logic */
/* ============================================ */

(function() {
    'use strict';

    // ============================================
    // 1. CLINICAL REFERENCE RANGES
    // ============================================
    const CLINICAL_RANGES = {
        systolic: { 
            normal: [90, 120], 
            warning: [121, 140], 
            critical: [141, 999],
            unit: 'mmHg',
            label: 'Systolic BP'
        },
        diastolic: { 
            normal: [60, 80], 
            warning: [81, 90], 
            critical: [91, 999],
            unit: 'mmHg',
            label: 'Diastolic BP'
        },
        pulse: { 
            normal: [60, 100], 
            warning: [101, 120], 
            critical: [121, 999],
            unit: 'bpm',
            label: 'Heart Rate'
        },
        spo2: { 
            normal: [95, 100], 
            warning: [90, 94], 
            critical: [0, 89],
            unit: '%',
            label: 'Oxygen Saturation'
        },
        glucose: { 
            normal: [70, 100], 
            warning: [101, 140], 
            critical: [141, 999],
            unit: 'mg/dL',
            label: 'Blood Glucose'
        }
    };

    // ============================================
    // 2. HELPER FUNCTIONS
    // ============================================
    
    /**
     * Detect anomalies in a dataset
     */
    function detectAnomalies(data, range) {
        return data.map((value, index) => {
            if (value === null || value === undefined) return null;
            if (value > range.critical[0]) return { index, value, severity: 'critical' };
            if (value > range.warning[0]) return { index, value, severity: 'warning' };
            return null;
        }).filter(item => item !== null);
    }

    /**
     * Get point styling based on value
     */
    function getPointStyle(value, range, color) {
        if (value > range.critical[0]) {
            return { radius: 8, color: '#ef4444', borderColor: '#dc2626' };
        }
        if (value > range.warning[0]) {
            return { radius: 6, color: '#f59e0b', borderColor: '#d97706' };
        }
        return { radius: 3, color: color, borderColor: color };
    }

    /**
     * Create anomaly indicator HTML
     */
    function createAnomalyIndicator(count, label) {
        if (count === 0) return '';
        return `
            <div class="anomaly-indicator">
                <span class="icon">🚨</span>
                <span class="text">${count} anomaly detected in ${label}</span>
            </div>
        `;
    }

    /**
     * Get status label for a value
     */
    function getStatus(value, range) {
        if (value > range.critical[0]) return { label: 'CRITICAL', class: 'status-badge-critical', emoji: '🚨' };
        if (value > range.warning[0]) return { label: 'WARNING', class: 'status-badge-warning', emoji: '⚠️' };
        return { label: 'NORMAL', class: 'status-badge-normal', emoji: '✅' };
    }

    // ============================================
    // 3. CHART CREATION
    // ============================================
    
    /**
     * Create an enhanced chart with anomaly detection
     */
    function createAnomalyChart(canvasId, data, range, color, labels) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas element "${canvasId}" not found`);
            return null;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.warn(`Could not get context for "${canvasId}"`);
            return null;
        }

        // Detect anomalies
        const anomalies = detectAnomalies(data, range);
        const hasAnomaly = anomalies.length > 0;

        // Prepare point styles
        const pointStyles = data.map(value => {
            if (value === null || value === undefined) return { radius: 0, color: 'transparent' };
            return getPointStyle(value, range, color);
        });

        // Create the chart
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: range.label,
                    data: data,
                    borderColor: color,
                    backgroundColor: hasAnomaly ? 'rgba(239, 68, 68, 0.05)' : 'rgba(59, 130, 246, 0.02)',
                    fill: true,
                    pointBackgroundColor: pointStyles.map(p => p.color),
                    pointBorderColor: pointStyles.map(p => p.borderColor || p.color),
                    pointRadius: pointStyles.map(p => p.radius || 3),
                    pointHoverRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: { family: 'Inter', size: 10, weight: 600 },
                            boxWidth: 7,
                            boxHeight: 7,
                            usePointStyle: true,
                            color: '#475569',
                            padding: 14
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterBody: function(tooltipItems) {
                                const value = tooltipItems[0].parsed.y;
                                const status = getStatus(value, range);
                                return [
                                    `Status: ${status.emoji} ${status.label}`,
                                    `Unit: ${range.unit}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { 
                            font: { family: 'Inter', size: 9.5, weight: 500 }, 
                            color: '#64748b',
                            maxRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 7
                        }
                    },
                    y: {
                        grid: { color: 'rgba(226, 232, 240, 0.55)' },
                        ticks: { 
                            font: { family: 'Inter', size: 9.5, weight: 500 }, 
                            color: '#64748b' 
                        }
                    }
                },
                elements: {
                    line: { borderWidth: 2.2, tension: 0.35 }
                }
            }
        });

        // Add anomaly indicator to the container
        if (hasAnomaly) {
            const container = canvas.closest('.chart-container');
            if (container) {
                const indicator = document.createElement('div');
                indicator.className = 'mt-2';
                indicator.innerHTML = createAnomalyIndicator(anomalies.length, range.label);
                container.appendChild(indicator);
            }
        }

        return chart;
    }

    // ============================================
    // 4. INITIALIZATION
    // ============================================
    
    /**
     * Initialize all charts
     */
    function initCharts() {
        // Get data from Django context
        const labels = window.CHART_DATA?.labels || [];
        const systolicData = window.CHART_DATA?.systolic || [];
        const diastolicData = window.CHART_DATA?.diastolic || [];
        const pulseData = window.CHART_DATA?.pulse || [];
        const spo2Data = window.CHART_DATA?.spo2 || [];
        const sugarData = window.CHART_DATA?.sugar || [];

        // Check if we have data
        const hasData = labels && labels.length > 0;

        if (!hasData) {
            // Show no-data message
            const container = document.querySelector('.grid-cols-1.xl\\:grid-cols-2');
            if (container) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-12 text-slate-400">
                        <svg class="w-12 h-12 mx-auto text-slate-300 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <p class="text-sm font-semibold">No chart data available yet</p>
                        <p class="text-xs mt-1">Start adding vital readings to see trends here</p>
                    </div>
                `;
            }
            return;
        }

        // Create all charts
        const chartConfigs = [
            { id: 'bpTrend', data: systolicData, range: CLINICAL_RANGES.systolic, color: '#ef4444' },
            { id: 'bpTrend', data: diastolicData, range: CLINICAL_RANGES.diastolic, color: '#3b82f6' },
            { id: 'pulseTrend', data: pulseData, range: CLINICAL_RANGES.pulse, color: '#0d9488' },
            { id: 'spo2Trend', data: spo2Data, range: CLINICAL_RANGES.spo2, color: '#f59e0b' },
            { id: 'sugarTrend', data: sugarData, range: CLINICAL_RANGES.glucose, color: '#8b5cf6' }
        ];

        chartConfigs.forEach(config => {
            createAnomalyChart(config.id, config.data, config.range, config.color, labels);
        });
    }

    // ============================================
    // 5. EXPOSE TO GLOBAL SCOPE
    // ============================================
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCharts);
    } else {
        initCharts();
    }

    // Expose functions globally for debugging
    window.RGMS = {
        initCharts: initCharts,
        detectAnomalies: detectAnomalies,
        CLINICAL_RANGES: CLINICAL_RANGES
    };

})();
EOFcat > static/js/dashboard/dashboard.js << 'EOF'
/* ============================================ */
/* RGMS DASHBOARD - Clinical Chart Logic */
/* ============================================ */

(function() {
    'use strict';

    // ============================================
    // 1. CLINICAL REFERENCE RANGES
    // ============================================
    const CLINICAL_RANGES = {
        systolic: { 
            normal: [90, 120], 
            warning: [121, 140], 
            critical: [141, 999],
            unit: 'mmHg',
            label: 'Systolic BP'
        },
        diastolic: { 
            normal: [60, 80], 
            warning: [81, 90], 
            critical: [91, 999],
            unit: 'mmHg',
            label: 'Diastolic BP'
        },
        pulse: { 
            normal: [60, 100], 
            warning: [101, 120], 
            critical: [121, 999],
            unit: 'bpm',
            label: 'Heart Rate'
        },
        spo2: { 
            normal: [95, 100], 
            warning: [90, 94], 
            critical: [0, 89],
            unit: '%',
            label: 'Oxygen Saturation'
        },
        glucose: { 
            normal: [70, 100], 
            warning: [101, 140], 
            critical: [141, 999],
            unit: 'mg/dL',
            label: 'Blood Glucose'
        }
    };

    // ============================================
    // 2. HELPER FUNCTIONS
    // ============================================
    
    /**
     * Detect anomalies in a dataset
     */
    function detectAnomalies(data, range) {
        return data.map((value, index) => {
            if (value === null || value === undefined) return null;
            if (value > range.critical[0]) return { index, value, severity: 'critical' };
            if (value > range.warning[0]) return { index, value, severity: 'warning' };
            return null;
        }).filter(item => item !== null);
    }

    /**
     * Get point styling based on value
     */
    function getPointStyle(value, range, color) {
        if (value > range.critical[0]) {
            return { radius: 8, color: '#ef4444', borderColor: '#dc2626' };
        }
        if (value > range.warning[0]) {
            return { radius: 6, color: '#f59e0b', borderColor: '#d97706' };
        }
        return { radius: 3, color: color, borderColor: color };
    }

    /**
     * Create anomaly indicator HTML
     */
    function createAnomalyIndicator(count, label) {
        if (count === 0) return '';
        return `
            <div class="anomaly-indicator">
                <span class="icon">🚨</span>
                <span class="text">${count} anomaly detected in ${label}</span>
            </div>
        `;
    }

    /**
     * Get status label for a value
     */
    function getStatus(value, range) {
        if (value > range.critical[0]) return { label: 'CRITICAL', class: 'status-badge-critical', emoji: '🚨' };
        if (value > range.warning[0]) return { label: 'WARNING', class: 'status-badge-warning', emoji: '⚠️' };
        return { label: 'NORMAL', class: 'status-badge-normal', emoji: '✅' };
    }

    // ============================================
    // 3. CHART CREATION
    // ============================================
    
    /**
     * Create an enhanced chart with anomaly detection
     */
    function createAnomalyChart(canvasId, data, range, color, labels) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas element "${canvasId}" not found`);
            return null;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.warn(`Could not get context for "${canvasId}"`);
            return null;
        }

        // Detect anomalies
        const anomalies = detectAnomalies(data, range);
        const hasAnomaly = anomalies.length > 0;

        // Prepare point styles
        const pointStyles = data.map(value => {
            if (value === null || value === undefined) return { radius: 0, color: 'transparent' };
            return getPointStyle(value, range, color);
        });

        // Create the chart
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: range.label,
                    data: data,
                    borderColor: color,
                    backgroundColor: hasAnomaly ? 'rgba(239, 68, 68, 0.05)' : 'rgba(59, 130, 246, 0.02)',
                    fill: true,
                    pointBackgroundColor: pointStyles.map(p => p.color),
                    pointBorderColor: pointStyles.map(p => p.borderColor || p.color),
                    pointRadius: pointStyles.map(p => p.radius || 3),
                    pointHoverRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: { family: 'Inter', size: 10, weight: 600 },
                            boxWidth: 7,
                            boxHeight: 7,
                            usePointStyle: true,
                            color: '#475569',
                            padding: 14
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterBody: function(tooltipItems) {
                                const value = tooltipItems[0].parsed.y;
                                const status = getStatus(value, range);
                                return [
                                    `Status: ${status.emoji} ${status.label}`,
                                    `Unit: ${range.unit}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { 
                            font: { family: 'Inter', size: 9.5, weight: 500 }, 
                            color: '#64748b',
                            maxRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 7
                        }
                    },
                    y: {
                        grid: { color: 'rgba(226, 232, 240, 0.55)' },
                        ticks: { 
                            font: { family: 'Inter', size: 9.5, weight: 500 }, 
                            color: '#64748b' 
                        }
                    }
                },
                elements: {
                    line: { borderWidth: 2.2, tension: 0.35 }
                }
            }
        });

        // Add anomaly indicator to the container
        if (hasAnomaly) {
            const container = canvas.closest('.chart-container');
            if (container) {
                const indicator = document.createElement('div');
                indicator.className = 'mt-2';
                indicator.innerHTML = createAnomalyIndicator(anomalies.length, range.label);
                container.appendChild(indicator);
            }
        }

        return chart;
    }

    // ============================================
    // 4. INITIALIZATION
    // ============================================
    
    /**
     * Initialize all charts
     */
    function initCharts() {
        // Get data from Django context
        const labels = window.CHART_DATA?.labels || [];
        const systolicData = window.CHART_DATA?.systolic || [];
        const diastolicData = window.CHART_DATA?.diastolic || [];
        const pulseData = window.CHART_DATA?.pulse || [];
        const spo2Data = window.CHART_DATA?.spo2 || [];
        const sugarData = window.CHART_DATA?.sugar || [];

        // Check if we have data
        const hasData = labels && labels.length > 0;

        if (!hasData) {
            // Show no-data message
            const container = document.querySelector('.grid-cols-1.xl\\:grid-cols-2');
            if (container) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-12 text-slate-400">
                        <svg class="w-12 h-12 mx-auto text-slate-300 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <p class="text-sm font-semibold">No chart data available yet</p>
                        <p class="text-xs mt-1">Start adding vital readings to see trends here</p>
                    </div>
                `;
            }
            return;
        }

        // Create all charts
        const chartConfigs = [
            { id: 'bpTrend', data: systolicData, range: CLINICAL_RANGES.systolic, color: '#ef4444' },
            { id: 'bpTrend', data: diastolicData, range: CLINICAL_RANGES.diastolic, color: '#3b82f6' },
            { id: 'pulseTrend', data: pulseData, range: CLINICAL_RANGES.pulse, color: '#0d9488' },
            { id: 'spo2Trend', data: spo2Data, range: CLINICAL_RANGES.spo2, color: '#f59e0b' },
            { id: 'sugarTrend', data: sugarData, range: CLINICAL_RANGES.glucose, color: '#8b5cf6' }
        ];

        chartConfigs.forEach(config => {
            createAnomalyChart(config.id, config.data, config.range, config.color, labels);
        });
    }

    // ============================================
    // 5. EXPOSE TO GLOBAL SCOPE
    // ============================================
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCharts);
    } else {
        initCharts();
    }

    // Expose functions globally for debugging
    window.RGMS = {
        initCharts: initCharts,
        detectAnomalies: detectAnomalies,
        CLINICAL_RANGES: CLINICAL_RANGES
    };

})();
