import './admin.css';
import { Header } from '../../components/Header';
import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { OrdersSection } from './OrdersSection';
import { PreparingSection } from './PreparingSection';
import { PreparedSection } from './PreparedSection';
import { DeliveredSection } from './DeliveredSection';
import { CancelledSection } from './CancelledSection';
import { AdminAuthSkeleton } from '../../components/Skeleton/Skeleton';
import { supabase } from '../../supabaseClient';
import { API_BASE_URL } from '../../config/api';

async function getAccessToken() {
    let access = localStorage.getItem("access");
    const refresh = localStorage.getItem("refresh");

    if (!access || isExpired(access)) {
        const res = await fetch(`${API_BASE_URL}/api/token/refresh/`, {
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

export function Admin() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    // Use URL search query parameter for activeTab and selected canteen
    const validTabs = ["pending", "preparing", "prepared", "delivered", "cancelled"];
    const queryTab = searchParams.get("tab");
    const activeTab = validTabs.includes(queryTab) ? queryTab : "pending";
    const queryCanteen = searchParams.get("canteen");

    const [canteens, setCanteens] = useState([]);
    const [selectedCanteenId, setSelectedCanteenId] = useState(queryCanteen || "");

    const handleCanteenChange = (canteenId) => {
        setSelectedCanteenId(canteenId);
        setSearchParams({ tab: activeTab, canteen: canteenId });
    };

    const setActiveTab = (tab) => {
        setSearchParams({ tab, ...(selectedCanteenId ? { canteen: selectedCanteenId } : {}) });
    };

    const [orders, setOrders] = useState([]);
    const [loadingOrders, setLoadingOrders] = useState(true);
    const [authChecking, setAuthChecking] = useState(true);
    const [isAdmin, setIsAdmin] = useState(false);
    const [orderCounts, setOrderCounts] = useState({
        pending: 0,
        preparing: 0,
        prepared: 0,
        delivered: 0,
        cancelled: 0,
    });

    // Verify admin privileges on mount
    useEffect(() => {
        const checkAdminStatus = async () => {
            try {
                const access = await getAccessToken();
                const res = await axios.get(`${API_BASE_URL}/api/current-user/`, {
                    headers: { Authorization: `Bearer ${access}` }
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

    // Fetch list of canteens
    useEffect(() => {
        const fetchCanteens = async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/api/canteens/`);
                setCanteens(res.data);
                if (res.data.length > 0) {
                    if (!queryCanteen) {
                        setSelectedCanteenId(res.data[0].id);
                        setSearchParams({ tab: activeTab, canteen: res.data[0].id });
                    }
                }
            } catch (err) {
                console.error("Failed to fetch canteens:", err);
            }
        };
        fetchCanteens();
    }, []);

    // Fetch order counts by status for selected canteen
    const fetchOrderCounts = useCallback(async () => {
        if (!selectedCanteenId) return;
        try {
            const access = await getAccessToken();
            const res = await axios.get(`${API_BASE_URL}/api/orders/counts/`, {
                headers: { Authorization: `Bearer ${access}` },
                params: { canteen_id: selectedCanteenId },
            });
            setOrderCounts(res.data);
        } catch (err) {
            console.error("Error fetching order counts:", err);
        }
    }, [selectedCanteenId]);

    useEffect(() => {
        if (!isAdmin || !selectedCanteenId) return;
        fetchOrderCounts();
    }, [isAdmin, selectedCanteenId, fetchOrderCounts]);

    // Fetch orders for active tab and selected canteen
    const fetchOrders = useCallback(async (showLoading = true) => {
        if (!selectedCanteenId) return;
        if (showLoading) setLoadingOrders(true);
        try {
            const access = await getAccessToken();
            const res = await axios.get(
                `${API_BASE_URL}/api/orders/${activeTab}/`,
                {
                    headers: {
                        Authorization: `Bearer ${access}`,
                    },
                    params: { canteen_id: selectedCanteenId },
                }
            );
            setOrders(res.data);
        } catch (err) {
            console.error("Error fetching orders:", err);
        } finally {
            if (showLoading) setLoadingOrders(false);
        }
    }, [activeTab, selectedCanteenId]);

    useEffect(() => {
        if (!isAdmin || !selectedCanteenId) return;
        fetchOrders(true);
    }, [isAdmin, selectedCanteenId, fetchOrders]);

    // Supabase Realtime: instant updates for admin dashboard & badge counts
    useEffect(() => {
        if (!isAdmin || !selectedCanteenId) return;

        const channel = supabase
            .channel('orders-realtime-admin')
            .on(
                'postgres_changes',
                { event: '*', schema: 'public', table: 'Canteen_backend_order' },
                () => {
                    fetchOrders(false);
                    fetchOrderCounts();
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [isAdmin, selectedCanteenId, fetchOrders, fetchOrderCounts]);

    const handleMoveOrders = async (orderId, newStatus) => {
        try {
            const access = await getAccessToken();
            const res = await axios.post(
                `${API_BASE_URL}/api/orders/move/${newStatus}/${orderId}/`,
                {},
                {
                    headers: { Authorization: `Bearer ${access}` },
                }
            );
            alert(res.data.message);

            // Update local orders list
            setOrders((prevOrders) =>
                prevOrders.filter((order) => order.id !== orderId)
            );

            // Refresh order counts across all statuses
            fetchOrderCounts();
        } catch (err) {
            console.error("Failed to move order:", err);
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

    return (
        <>
            <Header />
            <header className="admin-header-bar">
                <span className="admin-header-title">Admin Management Portal</span>
                <nav className="admin-nav-segmented">
                    <button className="admin-nav-btn active" onClick={() => navigate("/admin")}>
                        Orders
                    </button>
                    <button className="admin-nav-btn" onClick={() => navigate("/admin/analytics")}>
                        Analytics
                    </button>
                    <button className="admin-nav-btn" onClick={() => navigate("/admin/menu")}>
                        Manage Menu
                    </button>
                </nav>
            </header>

            {/* Canteen Selector Bar */}
            <div className="admin-canteen-filter-bar">
                <span className="selector-label">Select Canteen:</span>
                <div className="canteen-pills">
                    {canteens.map((canteen) => (
                        <button
                            key={canteen.id}
                            type="button"
                            className={`canteen-pill ${selectedCanteenId === canteen.id ? "active" : ""}`}
                            onClick={() => handleCanteenChange(canteen.id)}
                        >
                            {canteen.name}
                        </button>
                    ))}
                </div>
            </div>

            <div className="tabs">
                <div
                    className={`tab ${activeTab === "pending" ? "active" : ""}`}
                    onClick={() => setActiveTab("pending")}>
                    Pending Orders
                    <span className="tab-count-badge">{orderCounts.pending ?? 0}</span>
                </div>
                <div
                    className={`tab ${activeTab === "preparing" ? "active" : ""}`}
                    onClick={() => setActiveTab("preparing")}>
                    Preparing
                    <span className="tab-count-badge preparing">{orderCounts.preparing ?? 0}</span>
                </div>
                <div
                    className={`tab ${activeTab === "prepared" ? "active" : ""}`}
                    onClick={() => setActiveTab("prepared")}>
                    Ready to Pickup
                    <span className="tab-count-badge prepared">{orderCounts.prepared ?? 0}</span>
                </div>
                <div
                    className={`tab ${activeTab === "delivered" ? "active" : ""}`}
                    onClick={() => setActiveTab("delivered")}>
                    Delivered
                    <span className="tab-count-badge delivered">{orderCounts.delivered ?? 0}</span>
                </div>
                <div
                    className={`tab ${activeTab === "cancelled" ? "active" : ""}`}
                    onClick={() => setActiveTab("cancelled")}>
                    Cancelled
                    <span className="tab-count-badge cancelled">{orderCounts.cancelled ?? 0}</span>
                </div>
            </div>

            {(() => {
                const sortedOrders = Array.isArray(orders) ? [...orders].sort((a, b) => {
                    const aPrio = a.priority ? 1 : 0;
                    const bPrio = b.priority ? 1 : 0;
                    if (bPrio !== aPrio) {
                        return bPrio - aPrio; // staff first
                    }
                    const aDate = a.created_at ? new Date(a.created_at).getTime() : (a.id || 0);
                    const bDate = b.created_at ? new Date(b.created_at).getTime() : (b.id || 0);
                    return aDate - bDate; // then created_at ascending
                }) : [];

                return (
                    <>
                        {activeTab === "pending" && <OrdersSection orders={sortedOrders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
                        {activeTab === "preparing" && <PreparingSection orders={sortedOrders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
                        {activeTab === "prepared" && <PreparedSection orders={sortedOrders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
                        {activeTab === "delivered" && <DeliveredSection orders={sortedOrders} loading={loadingOrders} />}
                        {activeTab === "cancelled" && <CancelledSection orders={sortedOrders} loading={loadingOrders} />}
                    </>
                );
            })()}
        </>
    );
}