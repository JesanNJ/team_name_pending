import AmritaFullBackground from "../../assets/images/background.png";
import "./Home.css";
import { Header } from "../../components/Header";
import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom"
import jwt_decode from "jwt-decode";
import axios from "axios";
import { CanteenChoiceSkeleton } from "../../components/Skeleton/Skeleton";



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




export function Home() {

  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [canteens, setCanteens] = useState([]);
  const [loadingCanteens, setLoadingCanteens] = useState(true);
  let username = "";
  const location = useLocation();
  const usernameFromState = location.state?.username;
  const token = localStorage.getItem("access");
  username = usernameFromState || "";

  // for adminn 
  const [user, setUser] = useState(null);



  if (!username && token) {
    try {
      const decoded = jwt_decode(token);
      username = decoded.username;
    } catch {
      // Failed to decode token, username remains empty
    }
  }


  useEffect(() => {
    const fetchCanteens = async () => {
      setLoadingCanteens(true);
      try {
        const res = await fetch("http://127.0.0.1:8000/api/canteens/");
        const data = await res.json();
        setCanteens(data);
      } catch (err) {
        console.error("Failed to fetch canteens:", err);
      } finally {
        setLoadingCanteens(false);
      }
    };
    fetchCanteens();



    const fetchUser = async () => {
      try {
        const token = await getAccessToken(); // your JWT access token
        const res = await axios.get("http://127.0.0.1:8000/api/current-user/", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(res.data);
      } catch (err) {
        console.error("Failed to fetch user:", err);
      }
    };

    fetchUser();
  }, []);




  useEffect(() => {
    const token = localStorage.getItem("access");

    if (!token) navigate("/login");
  }, [navigate]);

  const handleLogout = async () => {
    setLoading(true);
    const refresh = localStorage.getItem("refresh");

    try {
      const res = await fetch("http://127.0.0.1:8000/api/logout/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access")}`, // optional
        },
        body: JSON.stringify({ refresh }),
      });

      const text = await res.text(); // ✅ read only once
      let data;
      try {
        data = JSON.parse(text); // try JSON
      } catch {
        data = text; // fallback plain text/HTML
      }

      if (res.ok) {
        console.log("Logout success:", data);
      } else {
        console.error("Logout failed:", data);
      }

      // Always clear tokens locally
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      navigate("/login");

    } catch (err) {
      console.error("Logout error:", err);
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      navigate("/login");
    } finally {
      setLoading(false);
    }
  };

  const handleCanteenClick = (canteen) => {
    // navigate to menu page and pass canteen ID
    navigate(`/canteen/${canteen.id}`, { state: { canteenName: canteen.name } });
  };

  const redirectToAdimin = () => {
    navigate('/admin')
  }



  console.log(user)

  return (
    <>
      <title>Home</title>

      <Header />

      <section className="section-1">
        <div className="name">
          <div>
            <h2>Welcome!</h2>
            <h4>{username ? username : "Guest"}</h4>
          </div>

          <div className="control-btns">
            {
              user && (user.profile?.role === "admin" || user.username?.toLowerCase() === "admin") && (
                <>
                  <button className="admin" onClick={redirectToAdimin}>Admin Orders</button>
                  <button className="admin" style={{ backgroundColor: "#27ae60" }} onClick={() => navigate('/admin/menu')}>Manage Menu</button>
                </>
              )
            }

            <button className="logout" onClick={handleLogout} disabled={loading}>
              {loading ? "Logging out..." : "Logout"}
            </button>
          </div>
        </div>


        <div className="intro-container">

          <div className="intro-box">
            <img src={AmritaFullBackground} alt="login" />
            <div className="title">
              <span>F</span>oodzy
            </div>

          </div>

          <div className="canteen-choices">
            <span>Choose your Canteen</span>
            <ul>
              {loadingCanteens ? (
                <CanteenChoiceSkeleton count={3} />
              ) : (
                canteens.map((canteen) => {
                  return (
                    <li key={canteen.id}>
                      <button
                        onClick={() => handleCanteenClick(canteen)}>
                        {canteen.name}
                      </button>
                    </li>
                  );
                })
              )}
            </ul>

          </div>


        </div>


      </section>

    </>
  );
};

export default Home;



