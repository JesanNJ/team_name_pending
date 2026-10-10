import React, { useState, useEffect } from "react";
import axios from "axios";
import { AdminMenuSkeletonGrid } from "../../components/Skeleton/Skeleton";

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

const DEFAULT_IMAGE = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=400&q=80";

export function AdminMenuSection() {
    const [canteens, setCanteens] = useState([]);
    const [selectedCanteenId, setSelectedCanteenId] = useState("");
    const [menuItems, setMenuItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [feedback, setFeedback] = useState({ message: "", type: "" });

    // Search and filters
    const [searchTerm, setSearchTerm] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("All");
    const [statusFilter, setStatusFilter] = useState("All"); // "All", "Active", "Inactive"

    // Modal state for Add Item
    const [showAddModal, setShowAddModal] = useState(false);
    const [addForm, setAddForm] = useState({
        name: "",
        product_code: "",
        price: "",
        stock: 25,
        type: "Veg",
        url: "",
    });

    // Modal state for Edit Item
    const [editingItem, setEditingItem] = useState(null);
    const [editForm, setEditForm] = useState({
        name: "",
        price: "",
        stock: 0,
        type: "Veg",
        url: "",
        is_active: true,
    });

    // Inline stock changes tracking
    const [stockEdits, setStockEdits] = useState({});

    // Fetch all canteens on mount
    useEffect(() => {
        const fetchCanteens = async () => {
            try {
                const res = await axios.get("http://127.0.0.1:8000/api/canteens/");
                setCanteens(res.data);
                if (res.data.length > 0) {
                    setSelectedCanteenId(res.data[0].id);
                } else {
                    setLoading(false);
                }
            } catch (err) {
                console.error("Failed to fetch canteens:", err);
                showToast("Failed to load canteens", "error");
                setLoading(false);
            }
        };
        fetchCanteens();
    }, []);

    // Fetch menu items whenever selected canteen changes
    useEffect(() => {
        if (!selectedCanteenId) return;
        fetchMenu(selectedCanteenId);
    }, [selectedCanteenId]);

    const showToast = (message, type = "success") => {
        setFeedback({ message, type });
        setTimeout(() => setFeedback({ message: "", type: "" }), 4000);
    };

    const fetchMenu = async (canteenId) => {
        setLoading(true);
        try {
            const token = await getAccessToken();
            const res = await axios.get(`http://127.0.0.1:8000/api/admin/menu/${canteenId}/`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            setMenuItems(res.data);
            setStockEdits({});
        } catch (err) {
            console.error("Failed to fetch menu:", err);
            showToast("Failed to load menu for selected canteen", "error");
        } finally {
            setLoading(false);
        }
    };

    // Toggle Active / Deactivated status (soft delete alternative)
    const handleToggleStatus = async (item) => {
        const actionWord = item.is_active ? "deactivate" : "activate";
        const confirmMsg = item.is_active
            ? `Deactivate "${item.product_name}"?\n\nThis will temporarily hide the item from students on the canteen menu without deleting it.`
            : `Activate "${item.product_name}"?\n\nThis will make the item visible to students again on the canteen menu.`;

        if (!window.confirm(confirmMsg)) return;

        try {
            const token = await getAccessToken();
            const res = await axios.post(
                `http://127.0.0.1:8000/api/admin/menu/toggle/${item.id}/`,
                {},
                { headers: { Authorization: `Bearer ${token}` } }
            );

            showToast(res.data.message || `Item ${actionWord}d!`, "success");
            setMenuItems((prev) =>
                prev.map((m) =>
                    m.id === item.id ? { ...m, is_active: !m.is_active } : m
                )
            );
        } catch (err) {
            console.error("Failed to toggle status:", err);
            showToast(`Failed to ${actionWord} item`, "error");
        }
    };

    // Quick stock edit handlers
    const handleStockChange = (menuId, newStock) => {
        const val = Math.max(0, parseInt(newStock) || 0);
        setStockEdits((prev) => ({ ...prev, [menuId]: val }));
    };

    const handleSaveStock = async (item) => {
        const newStock = stockEdits[item.id] !== undefined ? stockEdits[item.id] : item.stock;
        try {
            const token = await getAccessToken();
            await axios.post(
                `http://127.0.0.1:8000/api/admin/menu/update/${item.id}/`,
                { stock: newStock },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            showToast(`Updated stock for ${item.product_name} to ${newStock}`, "success");
            setMenuItems((prev) =>
                prev.map((m) => (m.id === item.id ? { ...m, stock: newStock } : m))
            );
            setStockEdits((prev) => {
                const updated = { ...prev };
                delete updated[item.id];
                return updated;
            });
        } catch (err) {
            console.error("Failed to update stock:", err);
            showToast("Failed to update stock", "error");
        }
    };

    // Permanent delete handler (optional fallback)
    const handleDeleteItem = async (item) => {
        const confirmed = window.confirm(
            `Permanently delete "${item.product_name}" from this canteen's menu?\n\nTip: You can deactivate it instead to hide it temporarily.`
        );
        if (!confirmed) return;

        try {
            const token = await getAccessToken();
            await axios.delete(`http://127.0.0.1:8000/api/admin/menu/delete/${item.id}/`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            showToast(`"${item.product_name}" removed from menu`, "success");
            setMenuItems((prev) => prev.filter((m) => m.id !== item.id));
        } catch (err) {
            console.error("Failed to delete item:", err);
            showToast("Failed to remove item", "error");
        }
    };

    // Open Add Modal
    const handleOpenAddModal = () => {
        const randomCode = `P${Math.floor(100 + Math.random() * 900)}`;
        setAddForm({
            name: "",
            product_code: randomCode,
            price: "",
            stock: 25,
            type: "Veg",
            url: "",
        });
        setShowAddModal(true);
    };

    // Submit Add Item
    const handleAddSubmit = async (e) => {
        e.preventDefault();
        if (!addForm.name.trim() || !addForm.price) {
            alert("Please provide both item name and price.");
            return;
        }

        try {
            const token = await getAccessToken();
            const res = await axios.post(
                "http://127.0.0.1:8000/api/admin/menu/add/",
                {
                    canteen_id: selectedCanteenId,
                    name: addForm.name.trim(),
                    product_code: addForm.product_code.trim(),
                    price: parseFloat(addForm.price),
                    stock: parseInt(addForm.stock) || 0,
                    type: addForm.type,
                    url: addForm.url.trim() || DEFAULT_IMAGE,
                },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            showToast(res.data.message || "Item added successfully!", "success");
            setShowAddModal(false);
            fetchMenu(selectedCanteenId);
        } catch (err) {
            console.error("Failed to add menu item:", err);
            const msg = err.response?.data?.error || "Failed to add menu item";
            showToast(msg, "error");
        }
    };

    // Open Edit Modal
    const handleOpenEditModal = (item) => {
        setEditingItem(item);
        setEditForm({
            name: item.product_name,
            price: item.product_price,
            stock: item.stock,
            type: item.product_type || "Veg",
            url: item.product_url || "",
            is_active: item.is_active !== undefined ? item.is_active : true,
        });
    };

    // Submit Edit Item
    const handleEditSubmit = async (e) => {
        e.preventDefault();
        if (!editingItem) return;

        try {
            const token = await getAccessToken();
            const res = await axios.post(
                `http://127.0.0.1:8000/api/admin/menu/update/${editingItem.id}/`,
                {
                    name: editForm.name.trim(),
                    price: parseFloat(editForm.price),
                    stock: parseInt(editForm.stock) || 0,
                    type: editForm.type,
                    url: editForm.url.trim(),
                    is_active: editForm.is_active,
                },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            showToast(res.data.message || "Item updated successfully!", "success");
            setEditingItem(null);
            fetchMenu(selectedCanteenId);
        } catch (err) {
            console.error("Failed to update menu item:", err);
            showToast("Failed to update menu item", "error");
        }
    };

    // Filter items by search, category, and status (active vs inactive)
    const filteredItems = menuItems.filter((item) => {
        const matchesCategory =
            categoryFilter === "All" || item.product_type === categoryFilter;

        const matchesStatus =
            statusFilter === "All"
                ? true
                : statusFilter === "Active"
                ? item.is_active
                : !item.is_active;

        const matchesSearch =
            item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (item.product_code && item.product_code.toLowerCase().includes(searchTerm.toLowerCase()));

        return matchesCategory && matchesStatus && matchesSearch;
    });

    const activeCanteenObj = canteens.find((c) => c.id === selectedCanteenId);
    const activeCount = menuItems.filter((i) => i.is_active).length;
    const inactiveCount = menuItems.filter((i) => !i.is_active).length;

    return (
        <section className="section active admin-menu-section">
            {feedback.message && (
                <div className={`admin-toast ${feedback.type}`}>
                    <span>{feedback.message}</span>
                </div>
            )}

            {/* Top Toolbar: Canteen Selector and Add Item CTA */}
            <div className="admin-menu-header">
                <div className="canteen-selector-group">
                    <span className="selector-label">Select Canteen:</span>
                    <div className="canteen-pills">
                        {canteens.length === 0 ? (
                            <div style={{ display: "flex", gap: "8px" }}>
                                <div className="skeleton-box skeleton-shimmer" style={{ width: "90px", height: "34px", borderRadius: "20px" }} />
                                <div className="skeleton-box skeleton-shimmer" style={{ width: "90px", height: "34px", borderRadius: "20px" }} />
                                <div className="skeleton-box skeleton-shimmer" style={{ width: "90px", height: "34px", borderRadius: "20px" }} />
                            </div>
                        ) : (
                            canteens.map((canteen) => (
                                <button
                                    key={canteen.id}
                                    type="button"
                                    className={`canteen-pill ${selectedCanteenId === canteen.id ? "active" : ""}`}
                                    onClick={() => {
                                        if (selectedCanteenId !== canteen.id) {
                                            setLoading(true);
                                            setSelectedCanteenId(canteen.id);
                                        }
                                    }}
                                >
                                    {canteen.name}
                                </button>
                            ))
                        )}
                    </div>
                </div>

                <button
                    type="button"
                    className="btn-add-item"
                    onClick={handleOpenAddModal}
                >
                    + Add New Menu Item
                </button>
            </div>

            {/* Sub-bar: Search, Status Toggles, and Category Filter */}
            <div className="admin-menu-filters">
                <div className="menu-search-box">
                    <input
                        type="text"
                        placeholder="Search items by name or code..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    {searchTerm && (
                        <button
                            type="button"
                            className="clear-search"
                            onClick={() => setSearchTerm("")}
                        >
                            ✕
                        </button>
                    )}
                </div>

                {/* Status Filter (All, Active, Inactive) */}
                <div className="status-filter-pills">
                    <button
                        type="button"
                        className={`status-pill ${statusFilter === "All" ? "active" : ""}`}
                        onClick={() => setStatusFilter("All")}
                    >
                        All ({menuItems.length})
                    </button>
                    <button
                        type="button"
                        className={`status-pill active-pill ${statusFilter === "Active" ? "active" : ""}`}
                        onClick={() => setStatusFilter("Active")}
                    >
                        Active ({activeCount})
                    </button>
                    <button
                        type="button"
                        className={`status-pill inactive-pill ${statusFilter === "Inactive" ? "active" : ""}`}
                        onClick={() => setStatusFilter("Inactive")}
                    >
                        Deactivated ({inactiveCount})
                    </button>
                </div>

                {/* Category Chips */}
                <div className="category-filter-chips">
                    {["All", "Veg", "Non-Veg", "Beverages", "Snacks", "Meals"].map((cat) => (
                        <button
                            key={cat}
                            type="button"
                            className={`category-chip ${categoryFilter === cat ? "active" : ""}`}
                            onClick={() => setCategoryFilter(cat)}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Stats Summary Banner */}
            <div className="menu-stats-banner">
                <span>
                    Showing <strong>{filteredItems.length}</strong> items for{" "}
                    <strong>{activeCanteenObj ? activeCanteenObj.name : "Canteen"}</strong>
                    {inactiveCount > 0 && (
                        <span className="inactive-counter-tag">
                            {" "}({inactiveCount} item{inactiveCount > 1 ? "s" : ""} currently deactivated)
                        </span>
                    )}
                </span>
            </div>

            {/* Items Grid */}
            {loading ? (
                <AdminMenuSkeletonGrid count={6} />
            ) : filteredItems.length === 0 ? (
                <div className="admin-menu-empty">
                    <p>No menu items found matching the selected filters.</p>
                    {statusFilter !== "All" && (
                        <button
                            type="button"
                            className="canteen-pill"
                            onClick={() => setStatusFilter("All")}
                        >
                            Show All Items
                        </button>
                    )}
                </div>
            ) : (
                <div className="admin-menu-grid">
                    {filteredItems.map((item) => {
                        const currentStock =
                            stockEdits[item.id] !== undefined ? stockEdits[item.id] : item.stock;
                        const isStockModified =
                            stockEdits[item.id] !== undefined && stockEdits[item.id] !== item.stock;

                        const stockBadgeClass =
                            currentStock === 0
                                ? "stock-out"
                                : currentStock <= 10
                                ? "stock-low"
                                : "stock-ok";

                        return (
                            <div
                                className={`admin-menu-card ${!item.is_active ? "card-inactive" : ""}`}
                                key={item.id}
                            >
                                <div className="card-top-image">
                                    <img
                                        src={item.product_url || DEFAULT_IMAGE}
                                        alt={item.product_name}
                                        onError={(e) => {
                                            e.target.onerror = null;
                                            e.target.src = DEFAULT_IMAGE;
                                        }}
                                    />
                                    <span className={`category-tag ${item.product_type?.toLowerCase()}`}>
                                        {item.product_type || "Item"}
                                    </span>

                                    {/* Active / Inactive Badge */}
                                    <span
                                        className={`status-pill-badge ${
                                            item.is_active ? "badge-active" : "badge-inactive"
                                        }`}
                                    >
                                        <span className="status-dot"></span>
                                        {item.is_active ? "Active" : "Deactivated"}
                                    </span>

                                    <span className={`stock-status-pill ${stockBadgeClass}`}>
                                        {currentStock === 0
                                            ? "Out of Stock"
                                            : currentStock <= 10
                                            ? `Low (${currentStock})`
                                            : `In Stock (${currentStock})`}
                                    </span>
                                </div>

                                <div className="card-body">
                                    <div className="card-title-row">
                                        <h4 className="item-title">{item.product_name}</h4>
                                        <span className="item-code">{item.product_code}</span>
                                    </div>

                                    {!item.is_active && (
                                        <div className="deactivated-notice">
                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                <circle cx="12" cy="12" r="10"></circle>
                                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                            </svg>
                                            <span>Hidden from student menu</span>
                                        </div>
                                    )}

                                    <div className="item-price">
                                        ₹ {Number(item.product_price).toFixed(2)}
                                    </div>

                                    {/* Stock management row */}
                                    <div className="stock-control-row">
                                        <span className="stock-label">Stock:</span>
                                        <div className="stock-stepper">
                                            <button
                                                type="button"
                                                onClick={() => handleStockChange(item.id, currentStock - 5)}
                                            >
                                                -5
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleStockChange(item.id, currentStock - 1)}
                                            >
                                                -
                                            </button>
                                            <input
                                                type="number"
                                                min="0"
                                                value={currentStock}
                                                onChange={(e) => handleStockChange(item.id, e.target.value)}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => handleStockChange(item.id, currentStock + 1)}
                                            >
                                                +
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleStockChange(item.id, currentStock + 5)}
                                            >
                                                +5
                                            </button>
                                        </div>

                                        {isStockModified && (
                                            <button
                                                type="button"
                                                className="btn-save-stock"
                                                onClick={() => handleSaveStock(item)}
                                            >
                                                Save
                                            </button>
                                        )}
                                    </div>

                                    {/* Action Buttons: Deactivate / Activate, Edit, Delete */}
                                    <div className="card-actions-modern">
                                        <button
                                            type="button"
                                            className={`action-btn action-toggle ${
                                                item.is_active ? "btn-deactivate" : "btn-activate"
                                            }`}
                                            onClick={() => handleToggleStatus(item)}
                                            title={item.is_active ? "Deactivate item to hide from student menu" : "Activate item to show on student menu"}
                                        >
                                            <span className="action-icon">
                                                {item.is_active ? (
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                                                        <line x1="1" y1="1" x2="23" y2="23"></line>
                                                    </svg>
                                                ) : (
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                                        <circle cx="12" cy="12" r="3"></circle>
                                                    </svg>
                                                )}
                                            </span>
                                            <span className="action-text">{item.is_active ? "Deactivate" : "Activate"}</span>
                                        </button>

                                        <button
                                            type="button"
                                            className="action-btn action-edit"
                                            onClick={() => handleOpenEditModal(item)}
                                            title="Edit item price, stock, and details"
                                        >
                                            <span className="action-icon">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                                </svg>
                                            </span>
                                            <span className="action-text">Edit</span>
                                        </button>

                                        <button
                                            type="button"
                                            className="action-btn action-delete"
                                            onClick={() => handleDeleteItem(item)}
                                            title="Delete item permanently"
                                        >
                                            <span className="action-icon">
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                                                    <polyline points="3 6 5 6 21 6"></polyline>
                                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                                    <line x1="10" y1="11" x2="10" y2="17"></line>
                                                    <line x1="14" y1="11" x2="14" y2="17"></line>
                                                </svg>
                                            </span>
                                            <span className="action-text">Delete</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal: Add Menu Item */}
            {showAddModal && (
                <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Add New Menu Item</h3>
                            <button
                                type="button"
                                className="modal-close"
                                onClick={() => setShowAddModal(false)}
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleAddSubmit} className="modal-form">
                            <div className="form-group">
                                <label>Canteen:</label>
                                <input
                                    type="text"
                                    value={activeCanteenObj ? activeCanteenObj.name : ""}
                                    disabled
                                    className="input-disabled"
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group flex-2">
                                    <label>Product Name *</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. Masala Dosa, Cold Coffee"
                                        value={addForm.name}
                                        onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                                    />
                                </div>
                                <div className="form-group flex-1">
                                    <label>Product Code</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. A008"
                                        value={addForm.product_code}
                                        onChange={(e) =>
                                            setAddForm({ ...addForm, product_code: e.target.value })
                                        }
                                    />
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group flex-1">
                                    <label>Category</label>
                                    <select
                                        value={addForm.type}
                                        onChange={(e) => setAddForm({ ...addForm, type: e.target.value })}
                                    >
                                        <option value="Veg">Veg</option>
                                        <option value="Non-Veg">Non-Veg</option>
                                        <option value="Beverages">Beverages</option>
                                        <option value="Snacks">Snacks</option>
                                        <option value="Meals">Meals</option>
                                    </select>
                                </div>
                                <div className="form-group flex-1">
                                    <label>Price (₹) *</label>
                                    <input
                                        type="number"
                                        step="0.5"
                                        min="1"
                                        required
                                        placeholder="e.g. 40"
                                        value={addForm.price}
                                        onChange={(e) => setAddForm({ ...addForm, price: e.target.value })}
                                    />
                                </div>
                                <div className="form-group flex-1">
                                    <label>Initial Stock</label>
                                    <input
                                        type="number"
                                        min="0"
                                        placeholder="e.g. 30"
                                        value={addForm.stock}
                                        onChange={(e) => setAddForm({ ...addForm, stock: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Image URL (Optional)</label>
                                <input
                                    type="url"
                                    placeholder="https://example.com/image.jpg"
                                    value={addForm.url}
                                    onChange={(e) => setAddForm({ ...addForm, url: e.target.value })}
                                />
                            </div>

                            {addForm.url && (
                                <div className="image-preview-box">
                                    <span>Image Preview:</span>
                                    <img
                                        src={addForm.url}
                                        alt="preview"
                                        onError={(e) => (e.target.style.display = "none")}
                                    />
                                </div>
                            )}

                            <div className="modal-actions">
                                <button
                                    type="button"
                                    className="btn-modal-cancel"
                                    onClick={() => setShowAddModal(false)}
                                >
                                    Cancel
                                </button>
                                <button type="submit" className="btn-modal-submit">
                                    Add Item
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal: Edit Menu Item */}
            {editingItem && (
                <div className="modal-backdrop" onClick={() => setEditingItem(null)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Edit Item: {editingItem.product_name}</h3>
                            <button
                                type="button"
                                className="modal-close"
                                onClick={() => setEditingItem(null)}
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleEditSubmit} className="modal-form">
                            <div className="form-group">
                                <label>Item Name</label>
                                <input
                                    type="text"
                                    required
                                    value={editForm.name}
                                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group flex-1">
                                    <label>Category</label>
                                    <select
                                        value={editForm.type}
                                        onChange={(e) => setEditForm({ ...editForm, type: e.target.value })}
                                    >
                                        <option value="Veg">Veg</option>
                                        <option value="Non-Veg">Non-Veg</option>
                                        <option value="Beverages">Beverages</option>
                                        <option value="Snacks">Snacks</option>
                                        <option value="Meals">Meals</option>
                                    </select>
                                </div>
                                <div className="form-group flex-1">
                                    <label>Price (₹)</label>
                                    <input
                                        type="number"
                                        step="0.5"
                                        min="1"
                                        required
                                        value={editForm.price}
                                        onChange={(e) => setEditForm({ ...editForm, price: e.target.value })}
                                    />
                                </div>
                                <div className="form-group flex-1">
                                    <label>Stock</label>
                                    <input
                                        type="number"
                                        min="0"
                                        required
                                        value={editForm.stock}
                                        onChange={(e) => setEditForm({ ...editForm, stock: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Image URL</label>
                                <input
                                    type="url"
                                    value={editForm.url}
                                    onChange={(e) => setEditForm({ ...editForm, url: e.target.value })}
                                />
                            </div>

                            {/* Active Status Checkbox */}
                            <div className="form-group checkbox-form-group">
                                <label className="custom-checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={editForm.is_active}
                                        onChange={(e) =>
                                            setEditForm({ ...editForm, is_active: e.target.checked })
                                        }
                                    />
                                    <span>
                                        <strong>Active Item</strong> (When checked, students can view and order this item)
                                    </span>
                                </label>
                            </div>

                            {editForm.url && (
                                <div className="image-preview-box">
                                    <span>Image Preview:</span>
                                    <img
                                        src={editForm.url}
                                        alt="preview"
                                        onError={(e) => (e.target.style.display = "none")}
                                    />
                                </div>
                            )}

                            <div className="modal-actions">
                                <button
                                    type="button"
                                    className="btn-modal-cancel"
                                    onClick={() => setEditingItem(null)}
                                >
                                    Cancel
                                </button>
                                <button type="submit" className="btn-modal-submit">
                                    Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </section>
    );
}
export default AdminMenuSection;
