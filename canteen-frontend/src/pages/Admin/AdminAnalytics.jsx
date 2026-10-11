import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Header } from "../../components/Header";
import { AdminAuthSkeleton } from "../../components/Skeleton/Skeleton";
import "./admin.css";

async function getAccessToken() {
    let access = localStorage.getItem("access");
    const refresh = localStorage.getItem("refresh");

    if (!access || isExpired(access)) {
        const res = await fetch("http://127.0.0.1:8000/api/token/refresh/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh }),
        });

        if (res.ok) {
            const data = await res.json();
            localStorage.setItem("access", data.access);
            access = data.access;
        } else {
            localStorage.clear();
            throw new Error("Session expired. Please log in again.");
        }
    }

    return access;
}

function isExpired(token) {
    try {
        const [, payload] = token.split(".");
        const decoded = JSON.parse(atob(payload));
        return decoded.exp * 1000 < Date.now();
    } catch {
        return true;
    }
}

export function AdminAnalytics() {
    const navigate = useNavigate();
    const [authChecking, setAuthChecking] = useState(true);
    const [isAdmin, setIsAdmin] = useState(false);

    // Canteen Selection
    const [canteens, setCanteens] = useState([]);
    const [selectedCanteenId, setSelectedCanteenId] = useState("");

    // Date Range Filters
    const [preset, setPreset] = useState("last_30_days");
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");

    // Analytics Data & Loading
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // Chart Controls & Interaction
    const [chartMetric, setChartMetric] = useState("orders"); // "orders" | "revenue" | "both"
    const [hoveredPoint, setHoveredPoint] = useState(null);

    // Verify Admin Privileges
    useEffect(() => {
        const checkAdminStatus = async () => {
            try {
                const access = await getAccessToken();
                const res = await axios.get("http://127.0.0.1:8000/api/current-user/", {
                    headers: { Authorization: `Bearer ${access}` },
                });
                const role = res.data?.profile?.role;
                const username = res.data?.username;
                if (role === "admin" || username?.toLowerCase() === "admin") {
                    setIsAdmin(true);
                } else {
                    setIsAdmin(false);
                }
            } catch (err) {
                console.error("Admin verification error:", err);
                setIsAdmin(false);
            } finally {
                setAuthChecking(false);
            }
        };

        checkAdminStatus();
    }, []);

    // Fetch Canteens List
    useEffect(() => {
        const fetchCanteens = async () => {
            try {
                const res = await axios.get("http://127.0.0.1:8000/api/canteens/");
                setCanteens(res.data);
                if (res.data.length > 0) {
                    setSelectedCanteenId(res.data[0].id);
                }
            } catch (err) {
                console.error("Failed to load canteens:", err);
            }
        };
        fetchCanteens();
    }, []);

    // Fetch Analytics Data
    const fetchAnalyticsData = useCallback(async () => {
        if (!selectedCanteenId) return;
        setLoading(true);
        setError("");
        try {
            const access = await getAccessToken();
            const params = { canteen_id: selectedCanteenId };

            if (preset === "custom") {
                if (startDate) params.start_date = startDate;
                if (endDate) params.end_date = endDate;
            } else {
                params.preset = preset;
            }

            const res = await axios.get("http://127.0.0.1:8000/api/admin/analytics/", {
                headers: { Authorization: `Bearer ${access}` },
                params: params,
            });
            setAnalytics(res.data);
        } catch (err) {
            console.error("Failed to load analytics:", err);
            setError(err.response?.data?.error || "Failed to load analytics data.");
        } finally {
            setLoading(false);
        }
    }, [selectedCanteenId, preset, startDate, endDate]);

    useEffect(() => {
        if (!isAdmin || !selectedCanteenId) return;
        fetchAnalyticsData();
    }, [isAdmin, selectedCanteenId, preset, startDate, endDate, fetchAnalyticsData]);

    const handlePresetChange = (newPreset) => {
        setPreset(newPreset);
        if (newPreset !== "custom") {
            setStartDate("");
            setEndDate("");
        }
    };

    if (authChecking) {
        return (
            <>
                <Header />
                <header className="admin-header-bar">
                    <span className="admin-header-title">Admin Management Portal</span>
                </header>
                <AdminAuthSkeleton />
            </>
        );
    }

    if (!isAdmin) {
        return (
            <>
                <Header />
                <div className="admin-access-denied">
                    <div className="access-denied-box">
                        <h2>⚠️ Access Restricted</h2>
                        <p>This portal is exclusively accessible to administrators. Please log in with an administrator account.</p>
                        <button className="btn btn-move" onClick={() => navigate("/home")}>
                            Return to Home
                        </button>
                    </div>
                </div>
            </>
        );
    }

    const summary = analytics?.summary || {};
    const statusDist = analytics?.status_distribution || {};
    const timeline = analytics?.timeline || [];
    const topItems = analytics?.top_selling_items || [];
    const categoryBreakdown = analytics?.category_breakdown || [];
    const hourlyDist = analytics?.hourly_distribution || [];

    // Derived summary calculations
    const peakDay = timeline.length > 0
        ? timeline.reduce((prev, curr) => (curr.orders > (prev?.orders || 0) ? curr : prev), timeline[0])
        : null;
    const avgDailyOrders = timeline.length > 0 ? (summary.total_orders / timeline.length).toFixed(1) : 0;

    // Meal Shift Demand Window Calculation
    const mealShifts = [
        { id: "breakfast", name: "Breakfast", icon: "🌅", time: "7 AM – 11 AM", hours: [7, 8, 9, 10], color: "#f59e0b" },
        { id: "lunch", name: "Lunch Rush", icon: "☀️", time: "11 AM – 3 PM", hours: [11, 12, 13, 14], color: "#2563eb" },
        { id: "snacks", name: "Evening Snacks", icon: "☕", time: "3 PM – 7 PM", hours: [15, 16, 17, 18], color: "#10b981" },
        { id: "dinner", name: "Dinner", icon: "🌙", time: "7 PM – 11 PM", hours: [19, 20, 21, 22], color: "#8b5cf6" },
    ].map((shift) => {
        const shiftOrders = hourlyDist.filter((h) => shift.hours.includes(h.hour)).reduce((sum, h) => sum + (h.orders || 0), 0);
        return { ...shift, orders: shiftOrders };
    });
    const totalShiftOrders = mealShifts.reduce((sum, s) => sum + s.orders, 0);

    // Friendly Ticks Generator
    const calculateTicks = (maxVal, count = 4) => {
        if (maxVal <= 0) return [0, 1, 2, 3, 4];
        const rawStep = Math.max(1, Math.ceil(maxVal / count));
        const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
        const residual = rawStep / magnitude;
        let step;
        if (residual <= 1) step = 1 * magnitude;
        else if (residual <= 2) step = 2 * magnitude;
        else if (residual <= 5) step = 5 * magnitude;
        else step = 10 * magnitude;

        const ticks = [];
        for (let i = 0; i <= count; i++) {
            ticks.push(i * step);
        }
        return ticks;
    };

    // Calculate chart scales
    const maxValOrders = Math.max(4, ...timeline.map((d) => d.orders || 0));
    const maxValRevenue = Math.max(10, ...timeline.map((d) => d.revenue || 0));
    const maxHourOrders = Math.max(1, ...hourlyDist.map((h) => h.orders || 0));

    const orderTicks = calculateTicks(maxValOrders, 4);
    const revenueTicks = calculateTicks(maxValRevenue, 4);

    const topOrderTick = orderTicks[orderTicks.length - 1];
    const topRevenueTick = revenueTicks[revenueTicks.length - 1];

    const activeTicks = chartMetric === "revenue" ? revenueTicks : orderTicks;
    const activeTopTick = chartMetric === "revenue" ? topRevenueTick : topOrderTick;

    // SVG plotting dimensions
    const svgWidth = 700;
    const svgHeight = 230;
    const padLeft = 60;
    const padRight = 30;
    const padTop = 30;
    const padBottom = 35;
    const plotW = svgWidth - padLeft - padRight;
    const plotH = svgHeight - padTop - padBottom;
    const slotW = timeline.length > 0 ? plotW / timeline.length : plotW;
    const barW = Math.min(48, Math.max(20, slotW * 0.44));

    const activeCanteenName = canteens.find((c) => c.id === selectedCanteenId)?.name || "Canteen";

    return (
        <div className="admin-analytics-page">
            <Header />
            <header className="admin-header-bar">
                <div className="admin-header-brand">
                    <span className="admin-header-title">Admin Management Portal</span>
                </div>
                <nav className="admin-nav-segmented">
                    <button className="admin-nav-btn" onClick={() => navigate("/admin")}>
                        Orders
                    </button>
                    <button className="admin-nav-btn active" onClick={() => navigate("/admin/analytics")}>
                        Analytics
                    </button>
                    <button className="admin-nav-btn" onClick={() => navigate("/admin/menu")}>
                        Manage Menu
                    </button>
                </nav>
            </header>

            {/* Controls Bar: Canteen Selector & Filters */}
            <div className="analytics-controls-wrapper">
                {/* Single Canteen Selector Bar */}
                <div className="admin-canteen-filter-bar">
                    <span className="selector-label">
                         Selected Canteen:
                    </span>
                    <div className="canteen-pills">
                        {canteens.map((canteen) => (
                            <button
                                key={canteen.id}
                                type="button"
                                className={`canteen-pill ${selectedCanteenId === canteen.id ? "active" : ""}`}
                                onClick={() => setSelectedCanteenId(canteen.id)}
                            >
                                
                                {canteen.name}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Date Range Toolbar */}
                <div className="analytics-toolbar">
                    <div className="preset-pills">
                        <span className="selector-label">
                           Period:
                        </span>
                        {[
                            { id: "today", label: "Today" },
                            { id: "last_7_days", label: "Last 7 Days" },
                            { id: "last_30_days", label: "Last 30 Days" },
                            { id: "this_month", label: "This Month" },
                            { id: "all_time", label: "All Time" },
                        ].map((p) => (
                            <button
                                key={p.id}
                                type="button"
                                className={`preset-btn ${preset === p.id ? "active" : ""}`}
                                onClick={() => handlePresetChange(p.id)}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>

                    <div className="custom-date-group">
                        <span className="selector-label">Custom:</span>
                        <input
                            type="date"
                            className="date-input"
                            value={startDate}
                            onChange={(e) => {
                                setStartDate(e.target.value);
                                setPreset("custom");
                            }}
                        />
                        <span className="date-separator">to</span>
                        <input
                            type="date"
                            className="date-input"
                            value={endDate}
                            onChange={(e) => {
                                setEndDate(e.target.value);
                                setPreset("custom");
                            }}
                        />
                        <button
                            type="button"
                            className="btn-refresh-analytics"
                            title="Refresh analytics data"
                            onClick={fetchAnalyticsData}
                            disabled={loading}
                        >
                         {loading ? "Updating..." : "Refresh"}
                        </button>
                    </div>
                </div>
            </div>

            <main className="analytics-container">
                {error && <div className="error-banner">⚠️ {error}</div>}

                {loading ? (
                    <div className="analytics-loading-card">
                        <div className="spinner" />
                        <p>Generating real-time analytics for <strong>{activeCanteenName}</strong>...</p>
                    </div>
                ) : (
                    <>
                        {/* KPI Stat Cards Grid */}
                        <div className="kpi-grid">
                            <div className="kpi-card revenue-card">
                                <div className="kpi-icon-wrap">
                                    <svg className="kpi-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M6 3h12" />
                                        <path d="M6 8h12" />
                                        <path d="M6 13l8.5 8" />
                                        <path d="M6 13h3a4.5 4.5 0 0 0 0-9" />
                                    </svg>
                                </div>
                                <div className="kpi-info">
                                    <span className="kpi-label">Delivered Revenue</span>
                                    <span className="kpi-value">₹ {(summary.total_revenue || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                                    <div className="kpi-footer">
                                        <span className="kpi-tag success">{summary.completed_orders || 0} delivered</span>
                                    </div>
                                </div>
                            </div>

                            <div className="kpi-card orders-card">
                                <div className="kpi-icon-wrap">
                                    <svg className="kpi-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M16 11V7a4 4 0 0 0-8 0v4" />
                                        <path d="M5 9h14l1 12H4L5 9z" />
                                    </svg>
                                </div>
                                <div className="kpi-info">
                                    <span className="kpi-label">Total Orders</span>
                                    <span className="kpi-value">{summary.total_orders || 0}</span>
                                    <div className="kpi-footer">
                                        <span className="kpi-tag info">{summary.active_orders || 0} active</span>
                                    </div>
                                </div>
                            </div>

                            <div className="kpi-card aov-card">
                                <div className="kpi-icon-wrap">
                                    <svg className="kpi-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                                        <line x1="7" y1="7" x2="7.01" y2="7" />
                                    </svg>
                                </div>
                                <div className="kpi-info">
                                    <span className="kpi-label">Average Order Value</span>
                                    <span className="kpi-value">₹ {(summary.avg_order_value || 0).toFixed(2)}</span>
                                    <div className="kpi-footer">
                                        <span className="kpi-tag neutral">Per completed order</span>
                                    </div>
                                </div>
                            </div>

                            <div className="kpi-card completion-card">
                                <div className="kpi-icon-wrap">
                                    <svg className="kpi-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                        <polyline points="22 4 12 14.01 9 11.01" />
                                    </svg>
                                </div>
                                <div className="kpi-info">
                                    <span className="kpi-label">Completion Rate</span>
                                    <span className="kpi-value">{summary.completion_rate || 0}%</span>
                                    <div className="kpi-footer">
                                        <span className="kpi-tag warning">{summary.cancelled_orders || 0} cancelled</span>
                                    </div>
                                </div>
                            </div>

                            <div className="kpi-card active-card">
                                <div className="kpi-icon-wrap">
                                    <svg className="kpi-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
                                    </svg>
                                </div>
                                <div className="kpi-info">
                                    <span className="kpi-label">Live Kitchen Load</span>
                                    <span className="kpi-value">{summary.active_orders || 0}</span>
                                    <div className="kpi-footer">
                                        <span className="kpi-tag accent">Pending / Preparing</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Middle Visual Section: Trends and Status */}
                        <div className="analytics-charts-row">
                            {/* Interactive SVG Daily Trend Chart */}
                            <div className="chart-panel flex-2">
                                <div className="panel-header">
                                    <div>
                                        <h3>Daily Performance Trend</h3>
                                        <span className="panel-subtitle">Clear daily breakdown with numerical scale and metrics</span>
                                    </div>

                                    {/* Metric Switcher Controls */}
                                    <div className="chart-metric-pills">
                                        <button
                                            type="button"
                                            className={`metric-pill-btn ${chartMetric === "orders" ? "active" : ""}`}
                                            onClick={() => setChartMetric("orders")}
                                        >
                                            Orders
                                        </button>
                                        <button
                                            type="button"
                                            className={`metric-pill-btn ${chartMetric === "revenue" ? "active" : ""}`}
                                            onClick={() => setChartMetric("revenue")}
                                        >
                                            Revenue (₹)
                                        </button>
                                        <button
                                            type="button"
                                            className={`metric-pill-btn ${chartMetric === "both" ? "active" : ""}`}
                                            onClick={() => setChartMetric("both")}
                                        >
                                            Combined
                                        </button>
                                    </div>
                                </div>

                                {/* Contextual Summary Badges */}
                                <div className="chart-summary-strip">
                                    <div className="strip-item">
                                        <span className="strip-label">Daily Avg:</span>
                                        <strong>{avgDailyOrders} orders/day</strong>
                                    </div>
                                    <div className="strip-item">
                                        <span className="strip-label">Peak Volume:</span>
                                        <strong>{peakDay ? `${peakDay.date.slice(5)} (${peakDay.orders} orders)` : "None"}</strong>
                                    </div>
                                    <div className="strip-item">
                                        <span className="strip-label">Total in Window:</span>
                                        <strong>{summary.total_orders || 0} orders (₹{(summary.total_revenue || 0).toFixed(2)})</strong>
                                    </div>
                                </div>

                                {timeline.length === 0 ? (
                                    <div className="empty-chart">
                                        
                                        <p>No orders recorded in this date range.</p>
                                    </div>
                                ) : (
                                    <div className="svg-chart-wrapper">
                                        {/* Floating Interactive Tooltip */}
                                        {hoveredPoint && (
                                            <div className="chart-floating-tooltip">
                                                <span className="tooltip-date">{hoveredPoint.date}</span>
                                                <div className="tooltip-row">
                                                    <span>Orders:</span>
                                                    <strong>{hoveredPoint.orders}</strong>
                                                </div>
                                                <div className="tooltip-row">
                                                    <span>Delivered Revenue:</span>
                                                    <strong style={{ color: "#10b981" }}>₹{hoveredPoint.revenue.toFixed(2)}</strong>
                                                </div>
                                                <div className="tooltip-row">
                                                    <span>Avg Ticket:</span>
                                                    <strong>
                                                        ₹{hoveredPoint.orders > 0 ? (hoveredPoint.revenue / hoveredPoint.orders).toFixed(2) : "0.00"}
                                                    </strong>
                                                </div>
                                            </div>
                                        )}

                                        <svg
                                            className="svg-trend-canvas"
                                            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                                            preserveAspectRatio="xMidYMid meet"
                                        >
                                            <defs>
                                                <linearGradient id="blueBarGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="0%" stopColor="#3b82f6" />
                                                    <stop offset="100%" stopColor="#1d4ed8" />
                                                </linearGradient>
                                                <linearGradient id="greenBarGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="0%" stopColor="#10b981" />
                                                    <stop offset="100%" stopColor="#059669" />
                                                </linearGradient>
                                            </defs>

                                            {/* Horizontal Gridlines & Left Y-Axis Labels */}
                                            {activeTicks.map((tick) => {
                                                const y = padTop + plotH - (tick / activeTopTick) * plotH;
                                                return (
                                                    <g key={tick}>
                                                        <line
                                                            x1={padLeft}
                                                            y1={y}
                                                            x2={padLeft + plotW}
                                                            y2={y}
                                                            stroke="#e2e8f0"
                                                            strokeWidth="1"
                                                            strokeDasharray={tick === 0 ? "none" : "4 4"}
                                                        />
                                                        <text
                                                            x={padLeft - 10}
                                                            y={y + 4}
                                                            textAnchor="end"
                                                            fill="#64748b"
                                                            fontSize="11.5"
                                                            fontWeight="600"
                                                        >
                                                            {chartMetric === "revenue" ? `₹${tick}` : tick}
                                                        </text>
                                                    </g>
                                                );
                                            })}

                                            {/* X-Axis Baseline */}
                                            <line
                                                x1={padLeft}
                                                y1={padTop + plotH}
                                                x2={padLeft + plotW}
                                                y2={padTop + plotH}
                                                stroke="#cbd5e1"
                                                strokeWidth="1.5"
                                            />

                                            {/* Day Data Columns */}
                                            {timeline.map((point, idx) => {
                                                const centerX = padLeft + (idx + 0.5) * slotW;
                                                const isHovered = hoveredPoint?.date === point.date;

                                                if (chartMetric === "orders") {
                                                    const barH = Math.max(3, (point.orders / topOrderTick) * plotH);
                                                    const barY = padTop + plotH - barH;
                                                    return (
                                                        <g key={point.date} className="svg-day-group">
                                                            {/* Background slot track */}
                                                            <rect
                                                                x={centerX - barW / 2}
                                                                y={padTop}
                                                                width={barW}
                                                                height={plotH}
                                                                rx="2"
                                                                fill="#f8fafc"
                                                                stroke="#f1f5f9"
                                                                strokeWidth="1"
                                                            />
                                                            {/* Vertical highlight cursor on hover */}
                                                            {isHovered && (
                                                                <line
                                                                    x1={centerX}
                                                                    y1={padTop}
                                                                    x2={centerX}
                                                                    y2={padTop + plotH}
                                                                    stroke="#93c5fd"
                                                                    strokeWidth="1.5"
                                                                    strokeDasharray="3 3"
                                                                />
                                                            )}
                                                            {/* Standard Solid Bar */}
                                                            <rect
                                                                x={centerX - barW / 2}
                                                                y={barY}
                                                                width={barW}
                                                                height={barH}
                                                                rx="2"
                                                                fill="#2563eb"
                                                                className={`svg-bar ${isHovered ? "hovered" : ""}`}
                                                            />
                                                            <text
                                                                x={centerX}
                                                                y={barY - 6}
                                                                textAnchor="middle"
                                                                fill="#0f172a"
                                                                fontSize="12"
                                                                fontWeight="600"
                                                            >
                                                                {point.orders}
                                                            </text>
                                                            <text
                                                                x={centerX}
                                                                y={padTop + plotH + 20}
                                                                textAnchor="middle"
                                                                fill="#475569"
                                                                fontSize="11.5"
                                                                fontWeight="500"
                                                            >
                                                                {point.date.slice(5)}
                                                            </text>
                                                        </g>
                                                    );
                                                }

                                                if (chartMetric === "revenue") {
                                                    const barH = Math.max(3, (point.revenue / topRevenueTick) * plotH);
                                                    const barY = padTop + plotH - barH;
                                                    return (
                                                        <g key={point.date} className="svg-day-group">
                                                            {/* Background slot track */}
                                                            <rect
                                                                x={centerX - barW / 2}
                                                                y={padTop}
                                                                width={barW}
                                                                height={plotH}
                                                                rx="2"
                                                                fill="#f8fafc"
                                                                stroke="#f1f5f9"
                                                                strokeWidth="1"
                                                            />
                                                            {isHovered && (
                                                                <line
                                                                    x1={centerX}
                                                                    y1={padTop}
                                                                    x2={centerX}
                                                                    y2={padTop + plotH}
                                                                    stroke="#86efac"
                                                                    strokeWidth="1.5"
                                                                    strokeDasharray="3 3"
                                                                />
                                                            )}
                                                            {/* Standard Solid Bar */}
                                                            <rect
                                                                x={centerX - barW / 2}
                                                                y={barY}
                                                                width={barW}
                                                                height={barH}
                                                                rx="2"
                                                                fill="#16a34a"
                                                                className={`svg-bar ${isHovered ? "hovered" : ""}`}
                                                            />
                                                            <text
                                                                x={centerX}
                                                                y={barY - 6}
                                                                textAnchor="middle"
                                                                fill="#15803d"
                                                                fontSize="11.5"
                                                                fontWeight="600"
                                                            >
                                                                ₹{Math.round(point.revenue)}
                                                            </text>
                                                            <text
                                                                x={centerX}
                                                                y={padTop + plotH + 20}
                                                                textAnchor="middle"
                                                                fill="#475569"
                                                                fontSize="11.5"
                                                                fontWeight="500"
                                                            >
                                                                {point.date.slice(5)}
                                                            </text>
                                                        </g>
                                                    );
                                                }

                                                // "both" combined mode: dual side-by-side standard bars
                                                const subW = Math.max(8, (barW - 4) / 2);
                                                const orderH = Math.max(3, (point.orders / topOrderTick) * plotH);
                                                const revH = Math.max(3, (point.revenue / topRevenueTick) * plotH);

                                                return (
                                                    <g key={point.date} className="svg-day-group">
                                                        {/* Background slot track */}
                                                        <rect
                                                            x={centerX - barW / 2}
                                                            y={padTop}
                                                            width={barW}
                                                            height={plotH}
                                                            rx="2"
                                                            fill="#f8fafc"
                                                            stroke="#f1f5f9"
                                                            strokeWidth="1"
                                                        />
                                                        {isHovered && (
                                                            <line
                                                                x1={centerX}
                                                                y1={padTop}
                                                                x2={centerX}
                                                                y2={padTop + plotH}
                                                                stroke="#cbd5e1"
                                                                strokeWidth="1.5"
                                                                strokeDasharray="3 3"
                                                            />
                                                        )}
                                                        {/* Orders Sub-bar */}
                                                        <rect
                                                            x={centerX - subW - 1}
                                                            y={padTop + plotH - orderH}
                                                            width={subW}
                                                            height={orderH}
                                                            rx="2"
                                                            fill="#2563eb"
                                                            className={`svg-bar ${isHovered ? "hovered" : ""}`}
                                                        />
                                                        {/* Revenue Sub-bar */}
                                                        <rect
                                                            x={centerX + 1}
                                                            y={padTop + plotH - revH}
                                                            width={subW}
                                                            height={revH}
                                                            rx="2"
                                                            fill="#16a34a"
                                                            className={`svg-bar ${isHovered ? "hovered" : ""}`}
                                                        />
                                                        <text
                                                            x={centerX}
                                                            y={padTop + plotH + 20}
                                                            textAnchor="middle"
                                                            fill="#475569"
                                                            fontSize="11.5"
                                                            fontWeight="500"
                                                        >
                                                            {point.date.slice(5)}
                                                        </text>
                                                    </g>
                                                );
                                            })}

                                            {/* Transparent Hover Hitbox Columns */}
                                            {timeline.map((point, idx) => (
                                                <rect
                                                    key={`hitbox-${point.date}`}
                                                    x={padLeft + idx * slotW}
                                                    y={padTop}
                                                    width={slotW}
                                                    height={plotH + padBottom}
                                                    fill="transparent"
                                                    style={{ cursor: "pointer" }}
                                                    onMouseEnter={() => setHoveredPoint(point)}
                                                    onMouseLeave={() => setHoveredPoint(null)}
                                                />
                                            ))}
                                        </svg>
                                    </div>
                                )}
                            </div>

                            {/* Status Breakdown Panel */}
                            <div className="chart-panel flex-1">
                                <div className="panel-header">
                                    <div>
                                        <h3>Order Status Pipeline</h3>
                                        <span className="panel-subtitle">Lifecycle breakdown across stages</span>
                                    </div>
                                    <span className="panel-badge">{summary.total_orders || 0} Total</span>
                                </div>

                                {/* Multi-segment visual bar */}
                                {summary.total_orders > 0 && (
                                    <div className="lifecycle-stacked-bar" title="Orders lifecycle breakdown">
                                        <div style={{ width: `${((statusDist.delivered || 0) / summary.total_orders) * 100}%`, background: "#10b981" }} title={`Delivered: ${statusDist.delivered || 0}`} />
                                        <div style={{ width: `${((statusDist.preparing || 0) / summary.total_orders) * 100}%`, background: "#3b82f6" }} title={`Preparing: ${statusDist.preparing || 0}`} />
                                        <div style={{ width: `${((statusDist.prepared || 0) / summary.total_orders) * 100}%`, background: "#f59e0b" }} title={`Ready: ${statusDist.prepared || 0}`} />
                                        <div style={{ width: `${((statusDist.pending || 0) / summary.total_orders) * 100}%`, background: "#8b5cf6" }} title={`Pending: ${statusDist.pending || 0}`} />
                                        <div style={{ width: `${((statusDist.cancelled || 0) / summary.total_orders) * 100}%`, background: "#ef4444" }} title={`Cancelled: ${statusDist.cancelled || 0}`} />
                                    </div>
                                )}

                                <div className="status-meters">
                                    {[
                                        { label: "Delivered", count: statusDist.delivered || 0, color: "#10b981" },
                                        { label: "Preparing", count: statusDist.preparing || 0, color: "#3b82f6" },
                                        { label: "Ready to Pickup", count: statusDist.prepared || 0, color: "#f59e0b" },
                                        { label: "Pending", count: statusDist.pending || 0, color: "#8b5cf6" },
                                        { label: "Cancelled", count: statusDist.cancelled || 0, color: "#ef4444" },
                                    ].map((st) => {
                                        const pct = summary.total_orders > 0 ? Math.round((st.count / summary.total_orders) * 100) : 0;
                                        return (
                                            <div className="status-meter-row" key={st.label}>
                                                <div className="status-meter-labels">
                                                    <span className="status-label-with-dot">
                                                        <span className="status-color-dot" style={{ background: st.color }} />
                                                        {st.label}
                                                    </span>
                                                    <span className="status-count-tag">
                                                        <strong>{st.count}</strong>
                                                        <span className="status-pct-small">({pct}%)</span>
                                                    </span>
                                                </div>
                                                <div className="status-meter-track">
                                                    <div
                                                        className="status-meter-fill"
                                                        style={{ width: `${pct}%`, background: st.color }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        {/* Demand Distribution Row: Meal Window Shifts & 24h Hourly Rush */}
                        <div className="analytics-charts-row">
                            {/* Meal Shift Demand Window Chart */}
                            <div className="chart-panel flex-1">
                                <div className="panel-header">
                                    <div>
                                        <h3>Meal Rush Demand Distribution</h3>
                                        <span className="panel-subtitle">Orders grouped by canteen meal service shifts</span>
                                    </div>
                                  
                                </div>
                                <div className="meal-shifts-container">
                                    {mealShifts.map((shift) => {
                                        const pct = totalShiftOrders > 0 ? Math.round((shift.orders / totalShiftOrders) * 100) : 0;
                                        return (
                                            <div className="meal-shift-row" key={shift.id}>
                                                <div className="shift-row-header">
                                                    <div className="shift-info">
                                                        
                                                        <div className="shift-text-group">
                                                            <span className="shift-name">{shift.name}</span>
                                                            <span className="shift-time">{shift.time}</span>
                                                        </div>
                                                    </div>
                                                    <div className="shift-orders-badge">
                                                        <strong>{shift.orders} orders</strong>
                                                        <span className="shift-pct">({pct}%)</span>
                                                    </div>
                                                </div>
                                                <div className="shift-progress-track">
                                                    <div
                                                        className="shift-progress-fill"
                                                        style={{ width: `${pct}%`, background: shift.color }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                            {/* Peak Rush Hours Chart */}
                            <div className="chart-panel flex-1">
                                <div className="panel-header">
                                    <div>
                                        <h3>24-Hour Peak Rush Analysis</h3>
                                        <span className="panel-subtitle">Order volume distributed by hour of day</span>
                                    </div>
                                </div>
                                <div className="rush-hours-grid">
                                    {hourlyDist.map((h) => {
                                        const intensityPct = Math.round((h.orders / maxHourOrders) * 100);
                                        const isPeak = intensityPct >= 65 && h.orders > 0;
                                        return (
                                            <div
                                                className={`rush-cell ${isPeak ? "peak-rush" : ""}`}
                                                key={h.hour}
                                                title={`${h.label}: ${h.orders} orders`}
                                            >
                                                <span className="rush-hour-tag">{h.label}</span>
                                                <div className="rush-bar-mini" style={{ height: `${Math.max(6, intensityPct * 0.45)}px` }} />
                                                <strong className="rush-count">{h.orders}</strong>
                                                {isPeak && <span className="rush-fire-badge" title="High Rush Hour">🔥</span>}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Category Sales Breakdown */}
                            <div className="chart-panel flex-1">
                                <div className="panel-header">
                                    <div>
                                        <h3>Sales by Category</h3>
                                        <span className="panel-subtitle">Category performance overview</span>
                                    </div>
                                </div>
                                <div className="category-meters-list">
                                    {categoryBreakdown.length === 0 ? (
                                        <div className="empty-chart">No category sales data.</div>
                                    ) : (
                                        categoryBreakdown.map((cat) => (
                                            <div className="category-card" key={cat.category}>
                                                <div className="cat-top">
                                                    <span className="cat-name">{cat.category}</span>
                                                    <span className="cat-revenue">₹ {cat.revenue.toFixed(2)}</span>
                                                </div>
                                                <div className="cat-bottom">
                                                    <span className="cat-qty">{cat.quantity} units sold</span>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Top Selling Products Leaderboard */}
                        <div className="chart-panel">
                            <div className="panel-header">
                                <div>
                                    <h3>Top Selling Dishes & Best Sellers</h3>
                                    <span className="panel-subtitle">Ranked by volume sold in current filter</span>
                                </div>
                                <span className="panel-badge">Leaderboard</span>
                            </div>
                            <div className="table-responsive">
                                <table className="analytics-table">
                                    <thead>
                                        <tr>
                                            <th>Rank</th>
                                            <th>Item Name</th>
                                            <th>Product Code</th>
                                            <th>Units Sold</th>
                                            <th>Total Revenue</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {topItems.length === 0 ? (
                                            <tr>
                                                <td colSpan="6" style={{ textAlign: "center", padding: "36px", color: "#888" }}>
                                                    No product sales data in this date range.
                                                </td>
                                            </tr>
                                        ) : (
                                            topItems.map((item, idx) => (
                                                <tr key={item.code || idx}>
                                                    <td>
                                                        <span className={`rank-badge rank-${idx + 1}`}>
                                                            {idx === 0 ? "#1" : idx === 1 ? "#2" : idx === 2 ? "#3" : `#${idx + 1}`}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <strong className="item-name-cell">{item.name}</strong>
                                                    </td>
                                                    <td><code className="item-code-cell">{item.code}</code></td>
                                                   
                                                    <td><strong className="item-qty-cell">{item.quantity}</strong></td>
                                                    <td><strong className="item-rev-cell">₹ {item.revenue.toFixed(2)}</strong></td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </>
                )}
            </main>
        </div>
    );
}
