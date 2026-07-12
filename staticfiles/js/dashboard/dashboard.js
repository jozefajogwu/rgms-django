/* ============================================ */
/* RGMS DASHBOARD - Clinical Chart Logic */
/* ============================================ */

(function() {
    'use strict';

    console.log('Dashboard JS loaded successfully');

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
    
    function detectAnomalies(data, range) {
        if (!data || !Array.isArray(data)) return [];
        return data.map((value, index) => {
            if (value === null || value === undefined || value === 0) return null;
            if (value > range.critical[0]) return { index, value, severity: 'critical' };
            if (value > range.warning[0]) return { index, value, severity: 'warning' };
            return null;
        }).filter(item => item !== null);
    }

    function getPointStyle(value, range, color) {
        if (value === null || value === undefined || value === 0) {
            return { radius: 0, color: 'transparent', borderColor: 'transparent' };
        }
        if (value > range.critical[0]) {
            return { radius: 8, color: '#ef4444', borderColor: '#dc2626' };
        }
        if (value > range.warning[0]) {
            return { radius: 6, color: '#f59e0b', borderColor: '#d97706' };
        }
        return { radius: 3, color: color, borderColor: color };
    }

    function getStatus(value, range) {
        if (value > range.critical[0]) return { label: 'CRITICAL', class: 'status-badge-critical', emoji: '🚨' };
        if (value > range.warning[0]) return { label: 'WARNING', class: 'status-badge-warning', emoji: '⚠️' };
        return { label: 'NORMAL', class: 'status-badge-normal', emoji: '✅' };
    }

    // ============================================
    // 3. CHART CREATION
    // ============================================
    
    function createAnomalyChart(canvasId, data, range, color, labels) {
        console.log('Creating chart:', canvasId);
        
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn('Canvas element "' + canvasId + '" not found');
            return null;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.warn('Could not get context for "' + canvasId + '"');
            return null;
        }

        // Check if we have valid data
        const validData = data.map(function(v) { return v || 0; });
        const hasData = validData.some(function(v) { return v > 0; });

        if (!hasData) {
            console.warn('No valid data for ' + canvasId);
            return null;
        }

        // Detect anomalies
        const anomalies = detectAnomalies(data, range);
        const hasAnomaly = anomalies.length > 0;

        // Prepare point styles
        const pointStyles = data.map(function(value) {
            if (value === null || value === undefined || value === 0) {
                return { radius: 0, color: 'transparent', borderColor: 'transparent' };
            }
            return getPointStyle(value, range, color);
        });

        try {
            var chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels || [],
                    datasets: [{
                        label: range.label,
                        data: validData,
                        borderColor: color,
                        backgroundColor: hasAnomaly ? 'rgba(239, 68, 68, 0.05)' : 'rgba(59, 130, 246, 0.02)',
                        fill: true,
                        pointBackgroundColor: pointStyles.map(function(p) { return p.color; }),
                        pointBorderColor: pointStyles.map(function(p) { return p.borderColor || p.color; }),
                        pointRadius: pointStyles.map(function(p) { return p.radius || 3; }),
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
                                    var value = tooltipItems[0]?.parsed?.y;
                                    if (!value) return ['No data'];
                                    var status = getStatus(value, range);
                                    return [
                                        'Status: ' + status.emoji + ' ' + status.label,
                                        'Unit: ' + range.unit
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

            console.log('Chart ' + canvasId + ' created successfully');
            return chart;
        } catch (error) {
            console.error('Error creating chart ' + canvasId + ':', error);
            return null;
        }
    }

    // ============================================
    // 4. INITIALIZATION
    // ============================================
    
    function initCharts() {
        console.log('Initializing charts...');
        
        // Get data from Django context
        var chartData = window.CHART_DATA || {};
        var labels = chartData.labels || [];
        var systolicData = chartData.systolic || [];
        var diastolicData = chartData.diastolic || [];
        var pulseData = chartData.pulse || [];
        var spo2Data = chartData.spo2 || [];
        var sugarData = chartData.sugar || [];

        console.log('Chart data:', { 
            labels: labels, 
            systolicData: systolicData, 
            diastolicData: diastolicData, 
            pulseData: pulseData, 
            spo2Data: spo2Data, 
            sugarData: sugarData 
        });

        // Check if we have data
        var hasData = labels && labels.length > 0;

        if (!hasData) {
            console.warn('No chart data available');
            var container = document.querySelector('.grid-cols-1.xl\\:grid-cols-2');
            if (container) {
                container.innerHTML = 
                    '<div class="col-span-full text-center py-12 text-slate-400">' +
                        '<svg class="w-12 h-12 mx-auto text-slate-300 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">' +
                            '<path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>' +
                        '</svg>' +
                        '<p class="text-sm font-semibold">No chart data available yet</p>' +
                        '<p class="text-xs mt-1">Start adding vital readings to see trends here</p>' +
                    '</div>';
            }
            return;
        }

        // Create all charts
        var chartConfigs = [
            { id: 'bpTrend', data: systolicData, range: CLINICAL_RANGES.systolic, color: '#ef4444' },
            { id: 'bpTrend', data: diastolicData, range: CLINICAL_RANGES.diastolic, color: '#3b82f6' },
            { id: 'pulseTrend', data: pulseData, range: CLINICAL_RANGES.pulse, color: '#0d9488' },
            { id: 'spo2Trend', data: spo2Data, range: CLINICAL_RANGES.spo2, color: '#f59e0b' },
            { id: 'sugarTrend', data: sugarData, range: CLINICAL_RANGES.glucose, color: '#8b5cf6' }
        ];

        chartConfigs.forEach(function(config) {
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

    console.log('Dashboard JS initialization complete');

})();