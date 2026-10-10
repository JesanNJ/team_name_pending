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

export function Admin() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    // Use URL search query parameter for activeTab (nuqs / URL state)
    const validTabs = ["pending", "preparing", "prepared", "delivered", "cancelled"];
    const queryTab = searchParams.get("tab");
    const activeTab = validTabs.includes(queryTab) ? queryTab : "pending";

    const setActiveTab = (tab) => {
        setSearchParams({ tab });
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
                const res = await axios.get("http://127.0.0.1:8000/api/current-user/", {
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

    // Fetch order counts by status (numbers/counts for each tab)
    const fetchOrderCounts = useCallback(async () => {
        try {
            const access = await getAccessToken();
            const res = await axios.get("http://127.0.0.1:8000/api/orders/counts/", {
                headers: { Authorization: `Bearer ${access}` },
            });
            setOrderCounts(res.data);
        } catch (err) {
            console.error("Error fetching order counts:", err);
        }
    }, []);

    useEffect(() => {
        if (!isAdmin) return;
        fetchOrderCounts();
    }, [isAdmin, fetchOrderCounts]);

    // Fetch orders for active tab
    useEffect(() => {
        if (!isAdmin) return;

        const fetchOrders = async () => {
            setLoadingOrders(true);
            try {
                const access = await getAccessToken();
                const res = await axios.get(
                    `http://127.0.0.1:8000/api/orders/${activeTab}/`,
                    {
                        headers: {
                            Authorization: `Bearer ${access}`,
                        },
                    }
                );
                setOrders(res.data);
            } catch (err) {
                console.error("Error fetching orders:", err);
            } finally {
                setLoadingOrders(false);
            }
        };

        fetchOrders();
    }, [activeTab, isAdmin]);

    const handleMoveOrders = async (orderId, newStatus) => {
        try {
            const access = await getAccessToken();
            const res = await axios.post(
                `http://127.0.0.1:8000/api/orders/move/${newStatus}/${orderId}/`,
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
            </header>

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

            {activeTab === "pending" && <OrdersSection orders={orders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
            {activeTab === "preparing" && <PreparingSection orders={orders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
            {activeTab === "prepared" && <PreparedSection orders={orders} loading={loadingOrders} handleMoveOrders={handleMoveOrders} />}
            {activeTab === "delivered" && <DeliveredSection orders={orders} loading={loadingOrders} />}
            {activeTab === "cancelled" && <CancelledSection orders={orders} loading={loadingOrders} />}
        </>
    );
}