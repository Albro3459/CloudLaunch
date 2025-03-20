import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const Login: React.FC = () => {

    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
    
        // Basic validation (add actual authentication logic later)
        if (username === "admin" && password === "2222") {
            navigate("/home", { replace: true });
        } else {
            alert("Invalid username or password!");
        }
    };
    

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        {/* Navbar */}
        <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0">
            <h1 className="text-xl font-semibold text-center">VPN Deployment</h1>
        </nav>

        {/* Login Form */}
        <div className="bg-white p-8 rounded-2xl shadow-lg w-96 mt-10">
            <h2 className="text-2xl font-semibold text-center mb-6">Login</h2>

            <form onSubmit={handleSubmit}>
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
            </form>
        </div>
        </div>
    );
};

export default Login;
