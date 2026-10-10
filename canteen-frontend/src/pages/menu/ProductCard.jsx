import axios from "axios";
import { useState } from "react";

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

export function ProductCard({ menu, canteenId, onAddToCartSuccess }) {
    const [quantity, setQuantity] = useState({});

    const handleAddToCart = async (product) => {
        if (Number(product.stock) <= 0) {
            alert("Sorry, this item is out of stock!");
            return;
        }
        const access = await getAccessToken();
        const itemQuantity = quantity[product.id] || 1;
        try {
            await axios.post(
                `http://127.0.0.1:8000/api/cart/add/${canteenId}/${Number(product.product_id)}`,
                { product_id: product.product_code, quantity: itemQuantity },
                { headers: { Authorization: `Bearer ${access}` } }
            );
            alert("Added to cart!");
            if (onAddToCartSuccess) {
                onAddToCartSuccess();
            }
        } catch (err) {
            console.error(err);
            const msg = err.response?.data?.error || "Failed to add to cart.";
            alert(msg);
        }
    };

    const handleIncrease = (id, maxStock) => {
        setQuantity((prev) => {
            const current = prev[id] || 1;
            if (maxStock !== undefined && current >= maxStock) {
                alert(`Cannot select more than available stock (${maxStock})`);
                return prev;
            }
            return {
                ...prev,
                [id]: current + 1,
            };
        });
    };

    const handleDecrease = (id) => {
        setQuantity((prev) => ({
            ...prev,
            [id]: Math.max(1, (prev[id] || 1) - 1),
        }));
    };

    return (
        <>
            {menu && menu.map((item) => {
                const stockNum = Number(item.stock);
                const isOutOfStock = stockNum <= 0;
                const isLowStock = stockNum > 0 && stockNum <= 10;
                const isVeg = item.product_type?.trim().toLowerCase() === "veg";
                const isNonVeg =
                    item.product_type?.trim().toLowerCase() === "non-veg" ||
                    item.product_type?.trim().toLowerCase() === "nonveg";

                return (
                    <div className="product-card" key={item.id}>
                        <div className="img-container">
                            <img
                                src={item.product_url}
                                alt={item.product_name}
                                className="product-img"
                            />

                            {/* Stock badge: ONLY displays when stock <= 10 */}
                            {stockNum <= 10 && (
                                <span
                                    className={`stock-badge ${isOutOfStock ? "out-of-stock" : "low-stock"}`}
                                >
                                    {isOutOfStock ? "Out of Stock" : `Only ${stockNum} left`}
                                </span>
                            )}

                            {/* Redesigned semi-transparent category badge with no square */}
                            {item.product_type && (
                                <span
                                    className={`diet-pill-badge ${
                                        isVeg ? "veg" : isNonVeg ? "non-veg" : "other"
                                    }`}
                                >
                                    {isVeg && <span className="diet-dot veg"></span>}
                                    {isNonVeg && <span className="diet-dot non-veg"></span>}
                                    <span>{item.product_type}</span>
                                </span>
                            )}
                        </div>

                        <div className="product-info">
                            <h3 className="product-title">{item.product_name}</h3>

                            <div className="price">₹ {Number(item.product_price).toFixed(2)}</div>

                            <div className="qty-editor">
                                <button
                                    className="qty-btn"
                                    onClick={() => handleDecrease(item.id)}
                                    disabled={isOutOfStock}
                                >
                                    -
                                </button>
                                <span className="qty-value">{quantity[item.id] || 1}</span>
                                <button
                                    className="qty-btn"
                                    onClick={() => handleIncrease(item.id, item.stock)}
                                    disabled={isOutOfStock}
                                >
                                    +
                                </button>
                            </div>

                            <button
                                className="add-btn"
                                onClick={() => handleAddToCart(item)}
                                disabled={isOutOfStock}
                                style={isOutOfStock ? { background: "#95a5a6", cursor: "not-allowed" } : {}}
                            >
                                {isOutOfStock ? "Out of Stock" : "Add to Cart"}
                            </button>
                        </div>
                    </div>
                );
            })}
        </>
    );
}

export default ProductCard;