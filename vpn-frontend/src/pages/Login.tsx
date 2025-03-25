import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth, onAuthStateChanged, signInWithEmailAndPassword } from "../firebase";

const Login: React.FC = () => {

    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const email = username + "@example.com";
            await signInWithEmailAndPassword(auth, email, password);
            navigate("/home", { replace: true });
        } catch (err) {
            // alert("Invalid username or password!");
            setError("Invalid email or password.");
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    navigate("/home", { replace: true });
                }
            };
            fetchUserData();
        });
        return () => unsubscribe();
    }, [navigate]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
        {/* Navbar */}
        <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
            <button 
                onClick={() => navigate("/about", { replace: true })} 
                className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute left-6"
            >
                About
            </button>
            <h1 className="text-xl font-semibold align-self-center">VPN Deployment</h1>
        </nav>

        {error && <p>{error}</p>}

        {/* Login Form */}
        <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-sm mt-10">
            <h2 className="text-2xl font-semibold text-center mb-6">Login</h2>

            <form onSubmit={handleLogin}>
                <div className="mb-4">
                    <label className="block text-gray-700 font-medium mb-2">Username</label>
                    <input
                        type="text"
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        placeholder="Enter your username"
                        value={username}
                        onChange={(x) => setUsername(x.target.value)}
                    />
                </div>

                <div className="mb-4">
                    <label className="block text-gray-700 font-medium mb-2">Password</label>
                    <input
                        type="password"
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        placeholder="Enter your password"
                        value={password}
                        onChange={(x) => setPassword(x.target.value)}
                    />
                </div>

                <button
                    type="submit"
                    className="cursor-pointer w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition"
                >
                    Login
                </button>

                <div className="ps-2 mt-2 text-xs">
                    <a
                    href="mailto:Brodsky.Alex22@gmail.com"
                    className="text-blue-600 underline hover:text-blue-800"
                    >
                    Email me for a test account
                    </a>
                </div>
            </form>
        </div>
        </div>
    );
};

export default Login;
