import { Link } from "react-router-dom";
import AmritaLogoCropped from "../assets/images/icons/amrita-logo-cropped.png";

export function Header() {
    return (
        <nav className="navbar">
            <div className="logo-div">
                <Link to="/home" style={{ display: "inline-block", height: "100%", width: "100%" }} title="Go to Home">
                    <img src={AmritaLogoCropped} alt="amrita-logo" style={{ cursor: "pointer" }} />
                </Link>
            </div>
        </nav>
    );
}