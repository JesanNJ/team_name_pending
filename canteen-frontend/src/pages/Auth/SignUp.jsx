import './auth.css';
import { Link,useNavigate } from 'react-router-dom';
import LogoContainerAuth from '../../components/LogoContainerAuth';
import { useState } from 'react';
import { API_BASE_URL } from '../../config/api';



export function SignUp() {

    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");

    const navigate = useNavigate(); 

    const handleSignup = async (e) => {
        e.preventDefault();
        setMessage("");

        const cleanUsername = username.trim();
        const cleanEmail = email.trim();

        try {
            const res = await fetch(`${API_BASE_URL}/api/register/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: cleanUsername, email: cleanEmail, password }),
            });

            const text = await res.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch {
                data = text;
            }

            if (res.ok) {
                // Save tokens in localStorage
                localStorage.setItem("access", data.access);
                localStorage.setItem("refresh", data.refresh);
                localStorage.setItem("username", data.username);
        
                setMessage("Signup & login successful!");
                navigate("/home",{ state: { username: data.username } }); // redirect to Home
            } else {
                if (typeof data === "object") {
                    if (data.username) setMessage(data.username[0]);
                    else if (data.email) setMessage(data.email[0]);
                    else if (data.detail) setMessage(data.detail);
                    else setMessage(JSON.stringify(data));
                } else {
                    setMessage(data);
                }
            }
        } catch (err) {
            console.error("Signup error:", err);
            setMessage("Something went wrong");
        }

    };
    


    return (
        <>
            <title>Signup</title>
            <section className='section-1-auth'>
                <div className="container">
                   <LogoContainerAuth />
                   
                    <div className="form-box">
                        {message ? <p className='message'>{message}</p> : null}
                        <h2>Sign Up</h2>
                        <form onSubmit={handleSignup}>
                            <input
                                type="text"
                                placeholder="Username / Full Name"
                                value={username}
                                autoCapitalize="none"
                                autoCorrect="off"
                                spellCheck="false"
                                onChange={(e) => setUsername(e.target.value)}
                                required 
                            />
                            <input
                                type="email"
                                placeholder="Email"
                                required 
                                autoCapitalize="none"
                                autoCorrect="off"
                                spellCheck="false"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                            <input
                                type="password"
                                placeholder="Password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            <button type="submit">Sign Up</button>
                        </form>

                        <div className="toggle">
                            <p id="toggle-text">Already have an account? <Link to="/login">Login</Link></p>
                        </div>
                    </div>

                </div>
            </section>
        </>
    );
};