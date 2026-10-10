import React from "react";

export function FilterMenu({ selectedType, setSelectedType }) {
    const categories = [
        { id: "All", label: "All Items" },
        { id: "Veg", label: "Pure Veg", isVeg: true },
        { id: "Non-Veg", label: "Non-Veg", isNonVeg: true },
        { id: "Beverages", label: "Beverages" },
        { id: "Meals", label: "Meals" },
        { id: "Snacks", label: "Snacks" },
    ];

    return (
        <div className="filter-chips-bar">
            {categories.map((cat) => {
                const isActive = selectedType === cat.id;
                return (
                    <button
                        key={cat.id}
                        type="button"
                        className={`filter-chip-pill ${
                            cat.isVeg ? "veg" : cat.isNonVeg ? "non-veg" : ""
                        } ${isActive ? "active" : ""}`}
                        onClick={() => setSelectedType(cat.id)}
                    >
                        {cat.isVeg && (
                            <span className="food-type-icon veg">
                                <span className="food-type-dot"></span>
                            </span>
                        )}
                        {cat.isNonVeg && (
                            <span className="food-type-icon non-veg">
                                <span className="food-type-dot"></span>
                            </span>
                        )}
                        <span>{cat.label}</span>
                    </button>
                );
            })}
        </div>
    );
}

export default FilterMenu;