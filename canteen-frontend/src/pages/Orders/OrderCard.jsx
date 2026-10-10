import dayjs from "dayjs";

export function OrderCard({ orders, openModal }) {
    return (

        <>
            {
                orders.map((order) => {
                    return (
                        <div className="order-card" key={order.id}>
                            <div className="order-header">
                                <span className="order-canteen">{order.canteen_name}</span>
                                <span className="order-id">Order #{order.id}</span>
                                <span className="order-date">{dayjs(order.created_at).format("MMM DD, YYYY")}</span>
                            </div>
                            <div className="order-items">
                                <p>
                                    {order.items.map((item) => {
                                        return(`${item.product_name} x${item.quantity}`)}).join(", ")
                                    }
                                </p>
                            </div>
                            <div className="order-footer">
                                <span className="order-total">Total: ₹  {order.total_price && order.total_price.toFixed(2)}</span>
                                <span className={`order-status ${order.status?.toLowerCase() || 'pending'}`}>
                                    {order.status === "prepared" || order.status === "ready"
                                        ? "Ready for Pickup"
                                        : order.status
                                        ? order.status.charAt(0).toUpperCase() + order.status.slice(1)
                                        : "Pending"}
                                </span>
                            </div>
                            <div className="order-actions">
                                <button className="view-btn" onClick={()=>openModal(order)}>View Details</button>
                            </div>
                        </div>
                    )

                })
            }

        </>

    )
}