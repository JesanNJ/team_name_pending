import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

export function CanteenSwitcher({ currentCanteenId, currentCanteenName, onSwitchCanteen }) {
    const [canteens, setCanteens] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        const fetchCanteens = async () => {
            try {
                const res = await axios.get("http://127.0.0.1:8000/api/canteens/");
                setCanteens(res.data);
            } catch (err) {
                console.error("Failed to load canteens:", err);
            }
        };
        fetchCanteens();
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        const handleOutsideClick = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleOutsideClick);
        return () => document.removeEventListener("mousedown", handleOutsideClick);
    }, []);

    // Find active canteen details
    const activeCanteen = canteens.find((c) => String(c.id) === String(currentCanteenId));
    const displayName = activeCanteen ? activeCanteen.name : (currentCanteenName || "Select Canteen");
    const displayLocation = activeCanteen?.location
        ? `${activeCanteen.location}, Amrita Campus`
        : "Amrita Vishwa Vidyapeetham, Ettimadai";

    return (
        <div className="canteen-location-header" ref={dropdownRef}>
            <button
                type="button"
                className="canteen-location-btn"
                onClick={() => setIsOpen((prev) => !prev)}
                title="Click to switch canteen"
                aria-expanded={isOpen}
            >
                <div className="canteen-text-group">
                    <div className="canteen-title-row">
                        <span className="canteen-main-title">{displayName}</span>
                        <svg
                            className={`canteen-chevron ${isOpen ? "open" : ""}`}
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </div>
                    <div className="canteen-subtitle">
                        {displayLocation}
                    </div>
                </div>
            </button>

            {isOpen && (
                <div className="canteen-switcher-dropdown">
                    <div className="switcher-header">
                        <span>Select Canteen</span>
                    </div>
                    <div className="switcher-list">
                        {canteens.map((canteen) => {
                            const isSelected = String(canteen.id) === String(currentCanteenId);
                            const locText = canteen.location
                                ? `${canteen.location}, Amrita Campus`
                                : "Amrita Vishwa Vidyapeetham";

                            return (
                                <button
                                    key={canteen.id}
                                    type="button"
                                    className={`switcher-item ${isSelected ? "selected" : ""}`}
                                    onClick={() => {
                                        setIsOpen(false);
                                        onSwitchCanteen(canteen);
                                    }}
                                >
                                    <div className="switcher-item-info">
                                        <span className="switcher-item-name">{canteen.name}</span>
                                        <span className="switcher-item-loc">{locText}</span>
                                    </div>
                                    {isSelected && <span className="switcher-check">✓</span>}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}

export default CanteenSwitcher;
