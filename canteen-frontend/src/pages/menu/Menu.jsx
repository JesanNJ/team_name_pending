import { Header } from "../../components/Header";

import SearchIcon from "../../assets/images/icons/search.svg";
import CartIcon from "../../assets/images/icons/cart.svg";
import OrderIcon from "../../assets/images/icons/orders.svg";
import { ProductCard } from "./ProductCard";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import "./menu.css";
import FilterMenu from "./FilterMenu";
import axios from "axios";
import { ProductSkeletonGrid } from "../../components/Skeleton/Skeleton";


export function Menu() {
    const { canteenId } = useParams();
    const [menu, setMenu] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedType, setSelectedType] = useState("All");
    // 🆕 For search results
    const [searchResults, setSearchResults] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        if (!canteenId) return;

        setLoading(true);
        axios
            .get(`http://127.0.0.1:8000/api/canteens/${canteenId}/menu/`)
            .then((res) => {
                setMenu(res.data);
            })
            .catch((err) => {
                setError("Failed to load menu", err);
            })
            .finally(() => {
                setLoading(false);
            });
    }, [canteenId]);


    if (error) {
        console.log(error)
    };


    useEffect(() => {
        if (searchTerm.trim() === "") {
            setSearchResults([]); // Empty search, reset results
            return;
        }

        // Simple frontend search filter
        const filtered = menu.filter((item) =>
            item.product_name.toLowerCase().includes(searchTerm.toLowerCase())
        );

        setSearchResults(filtered);
    }, [searchTerm, menu]);






    return (
        <>

            <Header />
            <section className="section-1">
                <div className="top-container">
                    <FilterMenu setSelectedType={setSelectedType} />
                    <div className="search">
                        <input type="text" placeholder="Search your Meal,Beverages,Desserts"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)} />
                        <span><img src={SearchIcon} alt="search" /></span>
                    </div>

                    <div className="orders">
                        <Link to="/orders"><img src={OrderIcon} alt="orders" /></Link>
                    </div>

                    <div className="cart">
                        <Link to={`/cart/${canteenId}`}><img src={CartIcon} alt="cart" /></Link>
                    </div>
                </div>
            </section>

            <section className="section-2">
                <div className="products-container">

                    {loading ? (
                        <ProductSkeletonGrid count={8} />
                    ) : searchResults.length > 0 ? (
                        <ProductCard menu={searchResults} canteenId={canteenId} selectedType={selectedType} />
                    ) : searchTerm.trim() !== "" ? (
                        <p style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px 0", color: "#666" }}>
                            No items found for "{searchTerm}"
                        </p>
                    ) : menu.length === 0 ? (
                        <p style={{ gridColumn: "1 / -1", textAlign: "center", padding: "40px 0", color: "#666" }}>
                            No menu items available at the moment.
                        </p>
                    ) : (
                        <ProductCard menu={menu} canteenId={canteenId} selectedType={selectedType} />
                    )}


                    {/* <ProductCard menu={menu} canteenId={canteenId} selectedType={selectedType} /> */}

                </div>

            </section>
        </>
    )
}