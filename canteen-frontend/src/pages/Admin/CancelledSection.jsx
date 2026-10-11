import React from 'react';
import { AdminOrderSkeletonGrid } from '../../components/Skeleton/Skeleton';

export function CancelledSection({ orders, loading }) {
    return (
        <div className="section active" id="orders">
            <div className="order-board">
                {loading ? (
                    <AdminOrderSkeletonGrid count={6} />
                ) : orders && orders.length > 0 ? (
                    orders.map((item) => {
                        return (
                            <div className="order-card cancelled-order-card" key={item.id}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                        <strong>Order #{item.id}</strong>
                                        {item.priority && <span className="staff-priority-badge">Staff</span>}
                                    </div>
                                    <span className="order-status-badge cancelled" style={{
                                        background: "#fde8e8",
                                        color: "#e74c3c",
                                        border: "1px solid #f8b4b4",
                                        fontSize: "11px",
                                        fontWeight: "600",
                                        padding: "3px 8px",
                                        borderRadius: "12px"
                                    }}>
                                        ✕ Cancelled
                                    </span>
                                </div>
                                <p className='canteen-name'>{item.canteen_name}</p>
                                <p className='items'>
                                    {item.items.map((item) => {
                                        return (`${item.product_name} x${item.quantity}`)
                                    }).join(", ")
                                    }
                                </p>
                                {item.total_price && (
                                    <p style={{ fontSize: "13px", color: "#666", marginTop: "8px" }}>
                                        Amount: ₹ {Number(item.total_price).toFixed(2)}
                                    </p>
                                )}
                            </div>
                        )
                    })
                ) : (
                    <p style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px 0', color: '#666' }}>
                        No cancelled orders found.
                    </p>
                )}
            </div>
        </div>
    )
}
