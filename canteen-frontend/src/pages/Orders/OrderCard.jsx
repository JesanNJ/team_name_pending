import dayjs from "dayjs";

export function OrderCard({ orders, openModal, handleCancelOrder, cancellingId }) {
    return (
        <>
            {orders.map((order) => {
                const statusLower = order.status?.toLowerCase();
                const canCancel = statusLower !== "delivered" && statusLower !== "cancelled";

                return (
                    <div className="order-card" key={order.id}>
                        <div className="order-header">
                            <span className="order-canteen">{order.canteen_name}</span>
                            <span className="order-id">Order #{order.id}</span>
                            <span className="order-date">{dayjs(order.created_at).format("MMM DD, YYYY")}</span>
                        </div>
                        <div className="order-items">
                            <p>
                                {order.items.map((item) => `${item.product_name} x${item.quantity}`).join(", ")}
                            </p>
                        </div>
                        <div className="order-footer">
                            <span className="order-total">Total: ₹  {order.total_price && order.total_price.toFixed(2)}</span>
                            <span className={`order-status ${statusLower || 'pending'}`}>
                                {statusLower === "prepared" || statusLower === "ready"
                                    ? "Ready for Pickup"
                                    : statusLower === "cancelled"
                                    ? "Cancelled"
                                    : order.status
                                    ? order.status.charAt(0).toUpperCase() + order.status.slice(1)
                                    : "Pending"}
                            </span>
                        </div>
                        <div className="order-actions">
                            <button className="view-btn" onClick={() => openModal(order)}>View Details</button>
                            {canCancel && handleCancelOrder && (
                                <button 
                                    className="cancel-btn"
                                    onClick={() => handleCancelOrder(order.id)}
                                    disabled={cancellingId === order.id}
                                >
                                    {cancellingId === order.id ? "Cancelling..." : "Cancel"}
                                </button>
                            )}
                        </div>
                    </div>
                );
            })}
        </>
    );
}