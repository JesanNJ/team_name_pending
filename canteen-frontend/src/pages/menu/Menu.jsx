import { Header } from "../../components/Header";
import SearchIcon from "../../assets/images/icons/search.svg";
import CartIcon from "../../assets/images/icons/cart.svg";
import OrderIcon from "../../assets/images/icons/orders.svg";
import { ProductCard } from "./ProductCard";
import { Link, useParams, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState, useCallback } from "react";
import "./menu.css";
import FilterMenu from "./FilterMenu";
import { CanteenSwitcher } from "./CanteenSwitcher";
import axios from "axios";
import { ProductSkeletonGrid } from "../../components/Skeleton/Skeleton";

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

export function Menu() {
    const { canteenId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    const [canteenName, setCanteenName] = useState(location.state?.canteenName || "");
    const [menu, setMenu] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedType, setSelectedType] = useState("All");
    const [cartCount, setCartCount] = useState(0);

    // Search results state
    const [searchResults, setSearchResults] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");

    // Fetch total cart items count for current canteen
    const fetchCartCount = useCallback(async () => {
        try {
            const token = await getAccessToken();
            const res = await axios.get(`http://127.0.0.1:8000/api/cart/view/${canteenId}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const total = res.data?.items
                ? res.data.items.reduce((sum, item) => sum + (item.quantity || 1), 0)
                : 0;
            setCartCount(total);
        } catch {
            setCartCount(0);
        }
    }, [canteenId]);

    useEffect(() => {
        if (canteenId) {
            fetchCartCount();
        }
    }, [canteenId, fetchCartCount]);

    // Fetch menu filtered directly through backend API call
    useEffect(() => {
        if (!canteenId) return;

        if (location.state?.canteenName) {
            setCanteenName(location.state.canteenName);
        }

        setLoading(true);
        const params = {};
        if (selectedType && selectedType !== "All") {
            params.category = selectedType;
        }

        axios
            .get(`http://127.0.0.1:8000/api/canteens/${canteenId}/menu/`, { params })
            .then((res) => {
                setMenu(res.data);
            })
            .catch((err) => {
                console.error("Failed to load menu", err);
            })
            .finally(() => {
                setLoading(false);
            });
    }, [canteenId, selectedType, location.state]);

    // Search query filtering
    useEffect(() => {
        if (searchTerm.trim() === "") {
            setSearchResults([]);
            return;
        }

        const filtered = menu.filter((item) =>
            item.product_name.toLowerCase().includes(searchTerm.toLowerCase())
        );

        setSearchResults(filtered);
    }, [searchTerm, menu]);

    const handleSwitchCanteen = (canteen) => {
        setCanteenName(canteen.name);
        setSelectedType("All");
        setSearchTerm("");
        navigate(`/canteen/${canteen.id}`, { state: { canteenName: canteen.name } });
    };

    return (
        <>
            <Header />
            <section className="section-1">
                <div className="top-container">
                    {/* Canteen Switcher */}
                    <CanteenSwitcher
                        currentCanteenId={canteenId}
                        currentCanteenName={canteenName}
                        onSwitchCanteen={handleSwitchCanteen}
                    />

                    {/* Redesigned Search Bar */}
                    <div className="search-bar-container">
                        <span className="search-icon-left">
                            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            </svg>
                        </span>
                        <input
                            type="text"
                            className="search-input-field"
                            placeholder="Search dishes, snacks, beverages..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                        {searchTerm && (
                            <button
                                type="button"
                                className="search-clear-btn"
                                onClick={() => setSearchTerm("")}
                                aria-label="Clear search"
                                title="Clear"
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    <div className="orders">
                        <Link to="/orders"><img src={OrderIcon} alt="orders" /></Link>
                    </div>

                    {/* Cart with Live Count Badge */}
                    <div className="cart">
                        <Link to={`/cart/${canteenId}`} className="cart-icon-link">
                            <img src={CartIcon} alt="cart" />
                            {cartCount > 0 && (
                                <span className="cart-badge-count">{cartCount}</span>
                            )}
                        </Link>
                    </div>
                </div>

                {/* Category Filters in new position (Triggers API call) */}
                <FilterMenu selectedType={selectedType} setSelectedType={setSelectedType} />
            </section>

            <section className="section-2">
                <div className="products-container">
                    {loading ? (
                        <ProductSkeletonGrid count={8} />
                    ) : searchResults.length > 0 ? (
                        <ProductCard
                            menu={searchResults}
                            canteenId={canteenId}
                            onAddToCartSuccess={fetchCartCount}
                        />
                    ) : searchTerm.trim() !== "" ? (
                        <p style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px 0", color: "#666" }}>
                            No items found for "{searchTerm}"
                        </p>
                    ) : menu.length === 0 ? (
                        <p style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px 0", color: "#666" }}>
                            No menu items available for this selection.
                        </p>
                    ) : (
                        <ProductCard
                            menu={menu}
                            canteenId={canteenId}
                            onAddToCartSuccess={fetchCartCount}
                        />
                    )}
                </div>
            </section>
        </>
    );
}

export default Menu;