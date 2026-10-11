import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../../config/api";

export function PaymentSummary({ cartData, setCartData, canteenId, getAccessToken }) {
    const navigate = useNavigate();
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [loadingOrder, setLoadingOrder] = useState(false);
    const [orderError, setOrderError] = useState("");
    const [waitEstimate, setWaitEstimate] = useState(null);

    const hasItems = cartData?.items && cartData.items.length > 0;

    // Fetch wait estimate when canteen or cart items update
    useEffect(() => {
        if (!canteenId) return;
        let isCurrent = true;

        const fetchWaitEstimate = async () => {
            try {
                const token = await getAccessToken().catch(() => null);
                const headers = token ? { "Authorization": `Bearer ${token}` } : {};
                const res = await fetch(`${API_BASE_URL}/api/canteens/${canteenId}/wait-time/`, { headers });
                if (res.ok) {
                    const data = await res.json();
                    if (isCurrent) setWaitEstimate(data);
                }
            } catch (err) {
                console.error("Failed to fetch wait time:", err);
            }
        };

        fetchWaitEstimate();
        return () => { isCurrent = false; };
    }, [canteenId, cartData]);

    const handleOpenConfirmModal = () => {
        if (!hasItems) {
            alert("Your cart is empty! Please add items before placing an order.");
            return;
        }
        setOrderError("");
        setShowConfirmModal(true);
    };

    const handleCloseModal = () => {
        if (!loadingOrder) {
            setShowConfirmModal(false);
            setOrderError("");
        }
    };

    const handleConfirmOrder = async () => {
        setLoadingOrder(true);
        setOrderError("");
        try {
            const token = await getAccessToken();
            const response = await fetch(`${API_BASE_URL}/api/place_order/${canteenId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
            });

            const data = await response.json();

            if (response.ok) {
                setShowConfirmModal(false);
                alert("Order placed successfully! Stock has been reserved.");
                setCartData({ items: [], total_price: 0 }); // clear cart state
                navigate("/orders"); // redirect to Orders page
            } else {
                setOrderError(data.error || "Failed to place order. Please try again.");
            }
        } catch (err) {
            console.error(err);
            setOrderError("A network error occurred. Please try again.");
        } finally {
            setLoadingOrder(false);
        }
    };

    return (
        <>
            <div className="cart-summary">
                <h3>Order Summary</h3>

                {hasItems && cartData.items.map((item) => (
                    <div className="summary-item" key={item.product_id}>
                        <span>{item.product_name} (x{item.quantity})</span>
                        <span>₹ {(item.total || 0).toFixed(2)}</span>
                    </div>
                ))}

                <hr />

                <div className="summary-row">
                    <span>Subtotal</span>
                    <span>₹ {(cartData?.total_price || 0).toFixed(2)}</span>
                </div>

                <div className="summary-row">
                    <span>Delivery</span>
                    <span>₹ 0.00</span>
                </div>

                <div className="summary-row total">
                    <span>Total</span>
                    <span>₹ {(cartData?.total_price || 0).toFixed(2)}</span>
                </div>

                {waitEstimate && (
                    <div style={{
                        marginTop: "12px",
                        padding: "10px 12px",
                        background: "#f0fdf4",
                        border: "1px solid #bbf7d0",
                        borderRadius: "8px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        fontSize: "13px",
                        color: "#166534"
                    }}>
                        <span>⏱️ Est. Waiting Time:</span>
                        <strong style={{ background: "#dcfce7", padding: "2px 8px", borderRadius: "6px" }}>
                            {waitEstimate.range || `${waitEstimate.wait_minutes} min`}
                        </strong>
                    </div>
                )}

                <button
                    className="checkout-btn"
                    id="checkoutBtn"
                    onClick={handleOpenConfirmModal}
                    disabled={!hasItems}
                >
                    Place Order
                </button>
                <div style={{ fontSize: "12px", color: "#718096", marginTop: "10px", textAlign: "center" }}>
                    Staff orders may be served first during busy times.
                </div>
            </div>

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="confirm-modal-overlay" onClick={handleCloseModal}>
                    <div className="confirm-modal-box" onClick={(e) => e.stopPropagation()}>
                        <div className="confirm-modal-header">
                            <h3>Confirm Order</h3>
                            <button
                                className="modal-close-icon"
                                onClick={handleCloseModal}
                                disabled={loadingOrder}
                                aria-label="Close"
                            >
                                &times;
                            </button>
                        </div>

                        <p className="confirm-modal-subtitle">
                            Please review your order before confirming. Stock will be reserved upon confirmation.
                        </p>

                        {waitEstimate && (
                            <div style={{
                                background: "#ecfdf5",
                                border: "1px solid #a7f3d0",
                                padding: "10px 14px",
                                borderRadius: "8px",
                                marginBottom: "12px",
                                fontSize: "13px",
                                color: "#065f46"
                            }}>
                                ⏱️ <strong>Estimated Kitchen Time:</strong> ~{waitEstimate.range || `${waitEstimate.wait_minutes} min`}
                                {waitEstimate.queue_position ? ` (Queue #${waitEstimate.queue_position})` : ""}
                            </div>
                        )}

                        {orderError && (
                            <div className="confirm-error-banner">
                                ⚠️ {orderError}
                            </div>
                        )}

                        <div className="confirm-items-scroll">
                            {cartData?.items?.map((item) => (
                                <div className="confirm-item-row" key={item.product_id}>
                                    <div className="confirm-item-info">
                                        <span className="confirm-item-title">{item.product_name}</span>
                                        <span className="confirm-item-qty">Qty: {item.quantity} × ₹{(item.price || 0).toFixed(2)}</span>
                                    </div>
                                    <span className="confirm-item-amount">₹{(item.total || 0).toFixed(2)}</span>
                                </div>
                            ))}
                        </div>

                        <div className="confirm-total-banner">
                            <span>Total Amount:</span>
                            <strong>₹ {(cartData?.total_price || 0).toFixed(2)}</strong>
                        </div>

                        <div className="confirm-modal-actions">
                            <button
                                className="btn-cancel-modal"
                                onClick={handleCloseModal}
                                disabled={loadingOrder}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn-confirm-modal"
                                onClick={handleConfirmOrder}
                                disabled={loadingOrder}
                            >
                                {loadingOrder ? "Placing Order..." : "Confirm & Place Order"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}