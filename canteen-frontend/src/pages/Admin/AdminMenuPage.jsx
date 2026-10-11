import './admin.css';
import { Header } from '../../components/Header';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AdminMenuSection } from './AdminMenuSection';
import { AdminAuthSkeleton } from '../../components/Skeleton/Skeleton';

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

export function AdminMenuPage() {
    const navigate = useNavigate();
    const [authChecking, setAuthChecking] = useState(true);
    const [isAdmin, setIsAdmin] = useState(false);

    useEffect(() => {
        const checkAdminStatus = async () => {
            try {
                const access = await getAccessToken();
                const res = await axios.get("http://127.0.0.1:8000/api/current-user/", {
                    headers: { Authorization: `Bearer ${access}` }
                });
                const role = res.data?.profile?.role;
                const username = res.data?.username;
                if (role === "admin" || username?.toLowerCase() === "admin") {
                    setIsAdmin(true);
                } else {
                    setIsAdmin(false);
                }
            } catch (err) {
                console.error("Admin verification error:", err);
                setIsAdmin(false);
            } finally {
                setAuthChecking(false);
            }
        };

        checkAdminStatus();
    }, []);

    if (authChecking) {
        return (
            <>
                <Header />
                <header className="admin-header-bar">
                    <span className="admin-header-title">Admin Management Portal</span>
                </header>
                <AdminAuthSkeleton />
            </>
        );
    }

    if (!isAdmin) {
        return (
            <>
                <Header />
                <div className="admin-access-denied">
                    <div className="access-denied-box">
                        <h2>⚠️ Access Restricted</h2>
                        <p>This portal is exclusively accessible to administrators. Please log in with an administrator account.</p>
                        <button className="btn btn-move" onClick={() => navigate("/home")}>
                            Return to Home
                        </button>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <Header />
            <header className="admin-header-bar">
                <span className="admin-header-title">Admin Management Portal</span>
                <nav className="admin-nav-segmented">
                    <button className="admin-nav-btn" onClick={() => navigate("/admin")}>
                         Orders
                    </button>
                    <button className="admin-nav-btn" onClick={() => navigate("/admin/analytics")}>
                        Analytics
                    </button>
                    <button className="admin-nav-btn active" onClick={() => navigate("/admin/menu")}>
                        Manage Menu
                    </button>
                </nav>
            </header>

            <AdminMenuSection />
        </>
    );
}
