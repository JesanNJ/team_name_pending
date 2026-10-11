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
        setMessage("")

        try {
            const res = await fetch(`${API_BASE_URL}/api/register/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password }),
            });

            const data = await res.json();

            if (res.ok) {
                // Save tokens in localStorage
                localStorage.setItem("access", data.access);
                localStorage.setItem("refresh", data.refresh);
                localStorage.setItem("username", data.username);
        
                setMessage("Signup & login successful!");
                navigate("/home",{ state: { username: data.username } }); // redirect to Home
            } else {
                if(data.username){
                    setMessage(data.username[0])
                }else{
                    const errorData = await res.json();
                    setMessage("Error: " + JSON.stringify(errorData));
                }
                
            }
        } catch (err) {
              setMessage("Something went wrong",err);
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
                            <input type="text" placeholder="Full Name" value={username}
                                onChange={(e) => setUsername(e.target.value)} required 
                            />
                            <input type="email" placeholder="Email" required 
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}/>
                            <input type="password" placeholder="Password" required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)} />
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