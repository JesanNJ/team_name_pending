import './auth.css'
import LogoContainerAuth from '../../components/LogoContainerAuth';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { API_BASE_URL } from '../../config/api';


export function Login() {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage(""); // clear old message

    const cleanUsername = username.trim();

    try {
      const res = await fetch(`${API_BASE_URL}/api/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: cleanUsername, password }), // username can be email or username
      });

      const text = await res.text(); // read body once
      let data;
      try {
        data = JSON.parse(text); // try parse as JSON
      } catch {
        data = text; // fallback if not JSON
      }


      if (res.ok) {
        // Save tokens
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);

        setMessage("Login successful");
        navigate("/home");
      } else {
        // Backend returned an error
        if (typeof data === "object") {
          // Try to extract error messages
          if (data.username) setMessage(data.username[0]);
          else if (data.detail) setMessage(data.detail);
          else setMessage(JSON.stringify(data));
        } else {
          setMessage(data); // plain text or HTML error
        }
      }
    } catch (err) {
      console.error("Login error:", err);
      setMessage("Something went wrong");
    }
  };

  return (
    <>
      <title>Login</title>


      <section className='section-1-auth'>
        <div className="container">
          <LogoContainerAuth />


          <div className="form-box">
            {message && <p className="message">{message}</p>}
            <h2>Login</h2>
            <form onSubmit={handleLogin}>
              <input
                type="text"
                placeholder="Username or Email"
                required
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck="false"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <input
                type="password"
                placeholder="Password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button type="submit">Login</button>
            </form>

            <div className="toggle">
              <p id="toggle-text">Don't have an account? <Link to="/signup">SignUp</Link></p>
            </div>
          </div>
        </div>
      </section>
    </>
  );

}