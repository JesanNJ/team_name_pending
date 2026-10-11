import React from 'react';
import { AdminOrderSkeletonGrid } from '../../components/Skeleton/Skeleton';

export function DeliveredSection({ orders, loading }) {
    return (
        <div className="section active" id="orders">
            <div className="order-board">
                {loading ? (
                    <AdminOrderSkeletonGrid count={6} />
                ) : orders && orders.length > 0 ? (
                    orders.map((item) => {
                        return (
                            <div className="order-card" key={item.id}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                                    <strong style={{ margin: 0 }}>Order #{item.id}</strong>
                                    {item.priority && <span className="staff-priority-badge">STAFF</span>}
                                </div>
                                <p className='canteen-name'>{item.canteen_name}</p>
                                <p className='items'>
                                    {item.items.map((item) => {
                                        return (`${item.product_name} x${item.quantity}`)
                                    }).join(", ")
                                    }
                                </p>
                            </div>
                        )
                    })
                ) : (
                    <p style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px 0', color: '#666' }}>
                        No delivered orders.
                    </p>
                )}
            </div>
        </div>
    )
}