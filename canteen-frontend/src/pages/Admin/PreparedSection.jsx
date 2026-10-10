import React from 'react';
import { AdminOrderSkeletonGrid } from '../../components/Skeleton/Skeleton';

export function PreparedSection({ orders, loading, handleMoveOrders }) {
    return (
        <div className="section active" id="orders">
            <div className="order-board">
                {loading ? (
                    <AdminOrderSkeletonGrid count={6} />
                ) : orders && orders.length > 0 ? (
                    orders.map((item) => {
                        return (
                            <div className="order-card ready-pickup-card" key={item.id}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <strong>Order #{item.id}</strong>
                                    <span className="order-status-badge ready">Ready for Pickup</span>
                                </div>
                                <p className='canteen-name'>{item.canteen_name}</p>
                                <p className='items'>
                                    {item.items.map((item) => {
                                        return (`${item.product_name} x${item.quantity}`)
                                    }).join(", ")
                                    }
                                </p>
                                <button
                                    className="btn btn-move delivered-btn"
                                    onClick={() => handleMoveOrders(item.id, "delivered")}>
                                    ✓ Handover / Complete Delivery
                                </button>
                            </div>
                        )
                    })
                ) : (
                    <p style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px 0', color: '#666' }}>
                        No orders currently waiting for pickup.
                    </p>
                )}
            </div>
        </div>
    )
}
