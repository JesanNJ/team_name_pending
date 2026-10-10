import React from 'react';
import { AdminOrderSkeletonGrid } from '../../components/Skeleton/Skeleton';

export function OrdersSection({ orders, loading, handleMoveOrders }) {
    return (
        <div className="section active" id="orders">
            <div className="order-board">
                {loading ? (
                    <AdminOrderSkeletonGrid count={6} />
                ) : orders && orders.length > 0 ? (
                    orders.map((item) => {
                        return (
                            <div className="order-card" key={item.id}>
                                <strong>Order #{item.id}</strong>
                                <p className='canteen-name'>{item.canteen_name}</p>
                                <p className='items'>
                                    {item.items.map((item) => {
                                        return (`${item.product_name} x${item.quantity}`)
                                    }).join(", ")
                                    }
                                </p>
                                <button 
                                    className="btn btn-move" 
                                    onClick={()=> handleMoveOrders(item.id,"preparing")}>
                                        Move to Preparing
                                </button>
                            </div>
                        )
                    })
                ) : (
                    <p style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px 0', color: '#666' }}>
                        No pending orders.
                    </p>
                )}
            </div>
        </div>
    )
}