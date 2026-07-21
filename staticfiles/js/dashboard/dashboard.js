/* ============================================ */
/* RGMS DASHBOARD - Genesis Medevac Clinical Charts */
/* ============================================ */

(function() {
    'use strict';

    console.log('🏥 RGMS Dashboard JS v2.0 loaded');

    // ============================================
    // 1. CLINICAL REFERENCE RANGES
    // ============================================
    const CLINICAL_RANGES = {
        systolic: { 
            normal: [90, 120], 
            warning: [121, 140], 
            critical: [141, 999],
            unit: 'mmHg',
            label: 'Systolic BP',
            emoji: '💓'
        },
        diastolic: { 
            normal: [60, 80], 
            warning: [81, 90], 
            critical: [91, 999],
            unit: 'mmHg',
            label: 'Diastolic BP',
            emoji: '💓'
        },
        pulse: { 
            normal: [60, 100], 
            warning: [101, 120], 
            critical: [121, 999],
            unit: 'bpm',
            label: 'Heart Rate',
            emoji: '❤️'
        },
        spo2: { 
            normal: [95, 100], 
            warning: [90, 94], 
            critical: [0, 89],
            unit: '%',
            label: 'Oxygen Saturation',
            emoji: '🫁'
        },
        glucose: { 
            normal: [70, 100], 
            warning: [101, 140], 
            critical: [141, 999],
            unit: 'mg/dL',
            label: 'Blood Glucose',
            emoji: '🩸'
        }
    };

    // ============================================
    // 2. COLOR PALETTE - Genesis Medevac
    // ============================================
    const COLORS = {
        navy: '#211568',
        navyLight: '#3a2a8a',
        red: '#DC3545',
        redLight: '#fde8ea',
        redGlow: 'rgba(220, 53, 69, 0.25)',
        cyan: '#00A3E0',
        cyanLight: '#AED9F6',
        white: '#FFFFFF',
        muted: '#6c757d',
        border: '#e9ecef',
        success: '#22c55e',
        warning: '#f59e0b',
        critical: '#dc2626',
        chartColors: {
            systolic: '#DC3545',
            diastolic: '#211568',
            pulse: '#00A3E0',
            spo2: '#22c55e',
            glucose: '#8b5cf6'
        }
    };

    // ============================================
    // 3. HELPER FUNCTIONS
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
            return { 
                radius: 10, 
                color: COLORS.critical, 
                borderColor: COLORS.critical,
                borderWidth: 3
            };
        }
        if (value > range.warning[0]) {
            return { 
                radius: 7, 
                color: COLORS.warning, 
                borderColor: COLORS.warning,
                borderWidth: 2
            };
        }
        return { 
            radius: 4, 
            color: color, 
            borderColor: color,
            borderWidth: 1
        };
    }

    function getStatus(value, range) {
        if (value > range.critical[0]) {
            return { 
                label: 'CRITICAL', 
                class: 'status-badge-critical', 
                emoji: '🚨',
                color: COLORS.critical
            };
        }
        if (value > range.warning[0]) {
            return { 
                label: 'WARNING', 
                class: 'status-badge-warning', 
                emoji: '⚠️',
                color: COLORS.warning
            };
        }
        return { 
            label: 'NORMAL', 
            class: 'status-badge-normal', 
            emoji: '✅',
            color: COLORS.success
        };
    }

    function formatDateLabel(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch (e) {
            return dateStr;
        }
    }

    function getGradient(ctx, chartArea, color, opacity = 0.15) {
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, color + Math.round(opacity * 255).toString(16).padStart(2, '0'));
        gradient.addColorStop(1, color + '00');
        return gradient;
    }

    // ============================================
    // 4. CHART CREATION - Enhanced Version
    // ============================================
    
    function createAnomalyChart(canvasId, data, range, color, labels, options = {}) {
        console.log(`📊 Creating chart: ${canvasId}`);
        
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`⚠️ Canvas element "${canvasId}" not found`);
            return null;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            console.warn(`⚠️ Could not get context for "${canvasId}"`);
            return null;
        }

        // Validate data
        const validData = data.map(v => v || 0);
        const hasData = validData.some(v => v > 0);

        if (!hasData) {
            console.warn(`⚠️ No valid data for ${canvasId}`);
            // Show empty state
            showEmptyState(canvas);
            return null;
        }

        // Detect anomalies
        const anomalies = detectAnomalies(data, range);
        const hasAnomaly = anomalies.length > 0;

        // Prepare point styles
        const pointStyles = data.map(value => {
            if (value === null || value === undefined || value === 0) {
                return { radius: 0, color: 'transparent', borderColor: 'transparent', borderWidth: 0 };
            }
            return getPointStyle(value, range, color);
        });

        // Format labels
        const formattedLabels = labels.map(formatDateLabel);

        try {
            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: formattedLabels,
                    datasets: [{
                        label: `${range.emoji} ${range.label}`,
                        data: validData,
                        borderColor: color,
                        backgroundColor: function(context) {
                            const chart = context.chart;
                            const { ctx, chartArea } = chart;
                            if (!chartArea) return 'transparent';
                            return getGradient(ctx, chartArea, color, hasAnomaly ? 0.25 : 0.08);
                        },
                        fill: true,
                        pointBackgroundColor: pointStyles.map(p => p.color),
                        pointBorderColor: pointStyles.map(p => p.borderColor || p.color),
                        pointBorderWidth: pointStyles.map(p => p.borderWidth || 1),
                        pointRadius: pointStyles.map(p => p.radius || 3),
                        pointHoverRadius: 10,
                        pointHoverBorderWidth: 4,
                        pointHoverBorderColor: COLORS.white,
                        tension: 0.4,
                        borderWidth: 2.5,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: { 
                                    family: 'Montserrat', 
                                    size: 11, 
                                    weight: '700' 
                                },
                                boxWidth: 12,
                                boxHeight: 12,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                color: COLORS.navy,
                                padding: 16,
                                borderRadius: 4
                            }
                        },
                        tooltip: {
                            backgroundColor: COLORS.navy,
                            titleColor: COLORS.white,
                            bodyColor: COLORS.white,
                            titleFont: {
                                family: 'Montserrat',
                                size: 13,
                                weight: '700'
                            },
                            bodyFont: {
                                family: 'Lato',
                                size: 12
                            },
                            cornerRadius: 12,
                            padding: 14,
                            borderColor: COLORS.red,
                            borderWidth: 2,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed.y;
                                    if (!value) return 'No data';
                                    const status = getStatus(value, range);
                                    return `${range.label}: ${value} ${range.unit} ${status.emoji}`;
                                },
                                afterBody: function(tooltipItems) {
                                    const value = tooltipItems[0]?.parsed?.y;
                                    if (!value) return [];
                                    const status = getStatus(value, range);
                                    return [
                                        `━━━━━━━━━━━━━━━━`,
                                        `Status: ${status.emoji} ${status.label}`,
                                        `Normal Range: ${range.normal[0]} - ${range.normal[1]} ${range.unit}`
                                    ];
                                },
                                footer: function(tooltipItems) {
                                    const anomalies = detectAnomalies(
                                        tooltipItems.map(item => item.parsed.y), 
                                        range
                                    );
                                    if (anomalies.length > 0) {
                                        return `⚠️ ${anomalies.length} anomaly detected`;
                                    }
                                    return '✅ All values in range';
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { 
                                display: false,
                                drawBorder: false
                            },
                            ticks: { 
                                font: { 
                                    family: 'Lato', 
                                    size: 10, 
                                    weight: '600' 
                                }, 
                                color: COLORS.muted,
                                maxRotation: 45,
                                autoSkip: true,
                                maxTicksLimit: 7
                            },
                            border: {
                                color: COLORS.border
                            }
                        },
                        y: {
                            grid: { 
                                color: 'rgba(33, 21, 104, 0.06)',
                                drawBorder: false
                            },
                            ticks: { 
                                font: { 
                                    family: 'Lato', 
                                    size: 10, 
                                    weight: '600' 
                                }, 
                                color: COLORS.muted 
                            },
                            border: {
                                color: COLORS.border
                            }
                        }
                    },
                    elements: {
                        line: {
                            borderWidth: 2.5,
                            tension: 0.4
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });

            // Add anomaly markers if any
            if (hasAnomaly) {
                addAnomalyMarkers(chart, anomalies, data, range, color);
            }

            console.log(`✅ Chart ${canvasId} created successfully`);
            return chart;
        } catch (error) {
            console.error(`❌ Error creating chart ${canvasId}:`, error);
            return null;
        }
    }

    // ============================================
    // 5. ANOMALY MARKERS
    // ============================================
    
    function addAnomalyMarkers(chart, anomalies, data, range, color) {
        const canvas = chart.canvas;
        const ctx = canvas.getContext('2d');
        
        // Draw after chart is rendered
        chart.afterDraw = function() {
            const chartArea = this.chartArea;
            const meta = this.getDatasetMeta(0);
            
            anomalies.forEach(anomaly => {
                const index = anomaly.index;
                const value = anomaly.value;
                const severity = anomaly.severity;
                
                // Get position
                const x = meta.data[index].x;
                const y = meta.data[index].y;
                
                // Draw glow effect
                const gradient = ctx.createRadialGradient(x, y, 0, x, y, 20);
                const color_ = severity === 'critical' ? COLORS.critical : COLORS.warning;
                gradient.addColorStop(0, color_ + '40');
                gradient.addColorStop(1, color_ + '00');
                
                ctx.beginPath();
                ctx.arc(x, y, 20, 0, Math.PI * 2);
                ctx.fillStyle = gradient;
                ctx.fill();
                
                // Draw ring
                ctx.beginPath();
                ctx.arc(x, y, 12, 0, Math.PI * 2);
                ctx.strokeStyle = color_;
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Draw center dot
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fillStyle = color_;
                ctx.fill();
                ctx.strokeStyle = COLORS.white;
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Draw label
                ctx.fillStyle = COLORS.navy;
                ctx.font = 'bold 9px Montserrat';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(
                    severity === 'critical' ? '🚨' : '⚠️',
                    x,
                    chartArea.top - 10
                );
            });
        };
    }

    // ============================================
    // 6. EMPTY STATE
    // ============================================
    
    function showEmptyState(canvas) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        ctx.clearRect(0, 0, width, height);
        
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, width, height);
        
        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px Lato';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('📊 No data available', width / 2, height / 2);
        
        ctx.font = '12px Lato';
        ctx.fillStyle = '#cbd5e1';
        ctx.fillText('Start monitoring to see trends', width / 2, height / 2 + 28);
    }

    // ============================================
    // 7. CHART ANIMATIONS
    // ============================================
    
    function animateChartEntry(chart, delay = 0) {
        if (!chart) return;
        
        setTimeout(() => {
            const ctx = chart.canvas.getContext('2d');
            const chartArea = chart.chartArea;
            
            // Fade in animation
            let opacity = 0;
            const animate = () => {
                opacity += 0.02;
                if (opacity > 1) {
                    opacity = 1;
                }
                
                ctx.globalAlpha = opacity;
                chart.update();
                
                if (opacity < 1) {
                    requestAnimationFrame(animate);
                }
            };
            
            animate();
        }, delay);
    }

    // ============================================
    // 8. CHART UPDATE INTERVAL
    // ============================================
    
    let chartUpdateInterval = null;

    function startAutoRefresh(charts) {
        // Refresh charts every 60 seconds
        if (chartUpdateInterval) {
            clearInterval(chartUpdateInterval);
        }
        
        chartUpdateInterval = setInterval(() => {
            console.log('🔄 Auto-refreshing charts...');
            // Re-fetch data from window
            const chartData = window.CHART_DATA || {};
            // Update each chart with new data
            // This would need to be implemented based on your data structure
        }, 60000);
    }

    // ============================================
    // 9. INITIALIZATION
    // ============================================
    
    function initCharts() {
        console.log('🚀 Initializing Genesis Medevac charts...');
        
        // Get data from Django context
        const chartData = window.CHART_DATA || {};
        const labels = chartData.labels || [];
        const systolicData = chartData.systolic || [];
        const diastolicData = chartData.diastolic || [];
        const pulseData = chartData.pulse || [];
        const spo2Data = chartData.spo2 || [];
        const sugarData = chartData.sugar || [];

        console.log('📊 Chart data:', { 
            labels: labels.length,
            systolic: systolicData.length,
            diastolic: diastolicData.length,
            pulse: pulseData.length,
            spo2: spo2Data.length,
            sugar: sugarData.length
        });

        // Check if we have data
        const hasData = labels && labels.length > 0;

        if (!hasData) {
            console.warn('⚠️ No chart data available');
            const container = document.querySelector('.chart-grid');
            if (container) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-16">
                        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-[#fde8ea] mb-4">
                            <svg class="w-10 h-10 text-[#DC3545]" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                        </div>
                        <p class="text-lg font-bold text-[#211568] font-display">No Chart Data Available</p>
                        <p class="text-sm text-slate-400 mt-1">Start adding vital readings to see clinical trends here</p>
                    </div>
                `;
            }
            return;
        }

        // Create all charts
        const chartConfigs = [
            { 
                id: 'bpTrend', 
                data: systolicData, 
                range: CLINICAL_RANGES.systolic, 
                color: COLORS.chartColors.systolic,
                label: 'Systolic BP'
            },
            { 
                id: 'pulseTrend', 
                data: pulseData, 
                range: CLINICAL_RANGES.pulse, 
                color: COLORS.chartColors.pulse,
                label: 'Heart Rate'
            },
            { 
                id: 'spo2Trend', 
                data: spo2Data, 
                range: CLINICAL_RANGES.spo2, 
                color: COLORS.chartColors.spo2,
                label: 'SpO2'
            },
            { 
                id: 'sugarTrend', 
                data: sugarData, 
                range: CLINICAL_RANGES.glucose, 
                color: COLORS.chartColors.glucose,
                label: 'Blood Glucose'
            }
        ];

        const charts = [];
        chartConfigs.forEach((config, index) => {
            const chart = createAnomalyChart(
                config.id, 
                config.data, 
                config.range, 
                config.color, 
                labels
            );
            if (chart) {
                charts.push(chart);
                // Stagger animation
                animateChartEntry(chart, index * 300);
            }
        });

        // Start auto-refresh
        if (charts.length > 0) {
            startAutoRefresh(charts);
        }

        console.log(`✅ Initialized ${charts.length} charts successfully`);
    }

    // ============================================
    // 10. RESPONSIVE HANDLING
    // ============================================
    
    function handleResize() {
        // Chart.js handles resize automatically with responsive: true
        console.log('📱 Resize detected, charts will auto-adjust');
    }

    // ============================================
    // 11. EXPOSE TO GLOBAL SCOPE
    // ============================================
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCharts);
    } else {
        initCharts();
    }

    // Handle resize
    window.addEventListener('resize', handleResize);

    // Expose functions globally for debugging
    window.RGMS = {
        initCharts: initCharts,
        detectAnomalies: detectAnomalies,
        CLINICAL_RANGES: CLINICAL_RANGES,
        COLORS: COLORS,
        createChart: createAnomalyChart,
        version: '2.0.0'
    };

    console.log('✅ Genesis Medevac Dashboard JS v2.0 ready');

})();