import { useState, useEffect } from "react";
import axios from "axios";



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


export function CartCard({ cartData, canteenId, setCartData }) {



    const [quantity, setQuantity] = useState({});


    useEffect(() => {
        if (cartData.items) {
            const initialQuantities = {};
            cartData.items.forEach(item => {
                initialQuantities[item.product_id] = item.quantity;
            });
            setQuantity(initialQuantities);
        }
    }, [cartData]);


    const updateQuantityBackend = async (productId, newQty) => {
        try {
            const access = await getAccessToken(); // your token function
            console.log(productId)
            await axios.post(
                `http://127.0.0.1:8000/api/cart/update/${canteenId}/${productId}`,
                { quantity: newQty },
                { headers: { Authorization: `Bearer ${access}` } }
            );
            console.log(newQty)
        } catch (err) {
            console.error("Failed to update quantity:", err);
        }
    };


    // console.log(cartData)
    const handleIncrease = (id, maxStock) => {
        const currentQty = quantity[id] || 1;
        if (maxStock !== undefined && currentQty >= maxStock) {
            alert(`Cannot select more than available stock (${maxStock})`);
            return;
        }
        const newQty = currentQty + 1;
        setQuantity(prev => ({ ...prev, [id]: newQty }));
        updateQuantityBackend(id, newQty);
    };

    const handleDecrease = (id) => {
        const newQty = Math.max(1, (quantity[id] || 1) - 1);
        setQuantity(prev => ({ ...prev, [id]: newQty }));
        updateQuantityBackend(id, newQty);
    };

    const handleRemove = async (productId) => {
        const access = await getAccessToken();
        try {
            await axios.delete(
                `http://127.0.0.1:8000/api/cart/remove/${canteenId}/${productId}/`,
                { headers: { Authorization: `Bearer ${access}` } }
            );
            // Update UI after removal
            setCartData(prev => ({
                ...prev,
                items: prev.items.filter(item => item.product_id !== productId)
            }));
        } catch (err) {
            console.error(err);
        }
    };

    return (

        <>
            {
                cartData.items && cartData.items.map((item) => {
                    const isOverStock = item.stock !== undefined && (quantity[item.product_id] || 1) > item.stock;
                    return (
                        <div className="cart-card" key={item.product_id}>
                            <img src={item.url} alt={item.product_name}
                                className="cart-img" />
                            <div className="cart-info">
                                <h3 className="cart-title-item">{item.product_name}</h3>
                                <p className="cart-price">
                                    ₹ {item.price.toFixed(2)}
                                    {item.stock !== undefined && (
                                        <span style={{ fontSize: "12px", color: isOverStock ? "#e74c3c" : "#777", marginLeft: "10px", fontWeight: "normal" }}>
                                            (Available: {item.stock})
                                        </span>
                                    )}
                                </p>
                                <div className="cart-actions">
                                    <div className="qty">
                                        <button onClick={() => handleDecrease(item.product_id)}>-</button>
                                        <span>{quantity[item.product_id]}</span>
                                        <button onClick={() => handleIncrease(item.product_id, item.stock)}>+</button>
                                    </div>
                                    <button className="remove-btn" onClick={() => handleRemove(item.product_id)}>Remove</button>
                                </div>
                            </div>
                        </div>
                    )
                })
            }

        </>





    )
}