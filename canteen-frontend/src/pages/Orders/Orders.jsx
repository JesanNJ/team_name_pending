import { Header } from "../../components/Header";
import { OrderCard } from "./OrderCard";
import "./orders.css";
import { useState, useEffect } from "react";
import { OrderSkeletonGrid } from "../../components/Skeleton/Skeleton";
import { supabase } from "../../supabaseClient";
import { API_BASE_URL } from "../../config/api";


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




export function Orders() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [cancellingId, setCancellingId] = useState(null);


    const openModal = (order) => {
        setSelectedOrder(order)
    }

    const closeModal = () => {
        setSelectedOrder(null);
    }

    const handleCancelOrder = async (orderId) => {
        if (!window.confirm(`Are you sure you want to cancel Order #${orderId}?`)) {
            return;
        }
        setCancellingId(orderId);
        try {
            const access = await getAccessToken();
            const res = await fetch(`${API_BASE_URL}/api/orders/cancel/${orderId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${access}`
                }
            });
            const data = await res.json();
            if (res.ok) {
                alert(data.message || `Order #${orderId} cancelled successfully.`);
                setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: "cancelled" } : o));
                if (selectedOrder && selectedOrder.id === orderId) {
                    setSelectedOrder(prev => ({ ...prev, status: "cancelled" }));
                }
            } else {
                alert(data.error || "Failed to cancel order");
            }
        } catch (err) {
            console.error("Cancel order error:", err);
            alert("Something went wrong while cancelling the order.");
        } finally {
            setCancellingId(null);
        }
    };

    useEffect(() => {
        let isMounted = true;

        const fetchOrders = async (isInitial = false) => {
            if (isInitial) setLoading(true);
            try {
                const access = await getAccessToken();
                const res = await fetch(`${API_BASE_URL}/api/orders/`, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${access}`
                    },
                });
                if (!res.ok) throw new Error("Failed to fetch orders");
                const data = await res.json();
                if (isMounted) {
                    setOrders(data);
                }
            } catch (error) {
                console.error(error);
                if (isInitial && isMounted) setOrders([]);
            } finally {
                if (isInitial && isMounted) setLoading(false);
            }
        };

        fetchOrders(true);

        // Supabase Realtime: instant order status & queue updates
        const channel = supabase
            .channel('orders-realtime-student')
            .on(
                'postgres_changes',
                { event: '*', schema: 'public', table: 'Canteen_backend_order' },
                () => {
                    if (isMounted) {
                        fetchOrders(false);
                    }
                }
            )
            .subscribe();

        // Polling fallback every 30 seconds for live order & queue updates
        const intervalId = setInterval(() => {
            fetchOrders(false);
        }, 30000);

        return () => {
            isMounted = false;
            clearInterval(intervalId);
            supabase.removeChannel(channel);
        };
    }, []);


    return (
        <>
            <title>Orders</title>
            <Header />
            <section className="orders-page">
                <h2>Your Orders</h2>
                <p style={{ fontSize: "13px", color: "#64748b", marginTop: "-12px", marginBottom: "18px" }}>
                    Staff orders may be served first during busy times.
                </p>

                <div className="orders-grid">
                    {loading ? (
                        <OrderSkeletonGrid count={6} />
                    ) : orders.length === 0 ? (
                        <div style={{
                            gridColumn: "1 / -1",
                            padding: "50px 20px",
                            textAlign: "center",
                            background: "#fff",
                            borderRadius: "12px",
                            color: "#666",
                            boxShadow: "0 2px 8px rgba(0,0,0,0.06)"
                        }}>
                            📦 You haven't placed any orders yet.
                        </div>
                    ) : (
                        <OrderCard 
                            orders={orders} 
                            openModal={openModal} 
                            handleCancelOrder={handleCancelOrder} 
                            cancellingId={cancellingId} 
                        />
                    )}
                </div>
            </section>




            {
                selectedOrder &&
                <div id="orderModal" className="modal">
                    <div className="modal-content">
                        <span className="close" onClick={closeModal}>&times;</span>
                        <h3>Order Details</h3>
                        <div id="order-details">
                            {selectedOrder && selectedOrder.items.map((item, id) => {
                                return (
                                    <p key={id}><span>{item.product_name} x{item.quantity}</span><span>₹  {(item.product_price * item.quantity).toFixed(2)}</span></p>
                                )
                            })}


                            <hr />
                            <p><strong>Total</strong><span>₹  {selectedOrder.total_price.toFixed(2)}</span></p>
                        </div>
                        <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
                            <button className="reorder-btn-modal" style={{ flex: 1 }}>Reorder</button>
                            {selectedOrder.status !== "delivered" && selectedOrder.status !== "cancelled" && (
                                <button 
                                    className="cancel-btn-modal" 
                                    style={{ 
                                        flex: 1, 
                                        background: "#e74c3c", 
                                        color: "#fff", 
                                        border: "none", 
                                        borderRadius: "6px", 
                                        padding: "10px", 
                                        cursor: "pointer", 
                                        fontWeight: "600" 
                                    }}
                                    onClick={() => handleCancelOrder(selectedOrder.id)}
                                    disabled={cancellingId === selectedOrder.id}
                                >
                                    {cancellingId === selectedOrder.id ? "Cancelling..." : "Cancel Order"}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            }



        </>
    )
}