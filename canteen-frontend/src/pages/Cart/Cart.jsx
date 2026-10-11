import './cart.css';
import { Header } from '../../components/Header';
import { CartCard } from './CartCard';
import { PaymentSummary } from './PaymentSummary';
import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { CartSkeletonList, CartSummarySkeleton } from '../../components/Skeleton/Skeleton';
import { API_BASE_URL } from '../../config/api';



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


export function Cart() {
    const { canteenId } = useParams();
    const [cartData, setCartData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const getCartData = async () => {
            setLoading(true);
            try {
                const access = await getAccessToken();
                const response = await axios.get(`${API_BASE_URL}/api/cart/view/${canteenId}`,
                    { headers: { Authorization: `Bearer ${access}` } });
                setCartData(response.data);
            } catch (err) {
                console.error("Failed to load cart:", err);
            } finally {
                setLoading(false);
            }
        };
        getCartData();
    }, [canteenId]);


    return (
        <>
            <title>Cart</title>
            <Header />

            <section className="cart-section">
                <h2 className="cart-title">Your Cart</h2>
                <div className="cart-layout">
                    <div className="cart-row-container">
                        {loading ? (
                            <CartSkeletonList count={3} />
                        ) : !cartData.items || cartData.items.length === 0 ? (
                            <div style={{
                                gridColumn: "1 / -1",
                                padding: "40px 20px",
                                textAlign: "center",
                                background: "#fff",
                                borderRadius: "10px",
                                color: "#666",
                                boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
                            }}>
                                🛒 Your cart is empty. Add some delicious items from the menu!
                            </div>
                        ) : (
                            <CartCard canteenId={canteenId} cartData={cartData} setCartData={setCartData} />
                        )}
                    </div>

                    {loading ? (
                        <CartSummarySkeleton />
                    ) : (
                        <PaymentSummary cartData={cartData} setCartData={setCartData} canteenId={canteenId} getAccessToken={getAccessToken} />
                    )}

                    


                </div>
            </section>

        </>
    )
}