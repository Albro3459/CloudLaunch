import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getIdToken, onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "../firebase";
import { createUser, getUserRole } from "../helpers/APIHelper";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouse } from "@fortawesome/free-solid-svg-icons";

const CreateUser: React.FC = () => {
    const navigate = useNavigate();
    const [jwtToken, setJwtToken] = useState<string | null>(null);

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    const role  = await getUserRole(user);
                    if (role !== "admin") {
                        navigate("/", { replace: true });
                    }
                    try {
                        const token = await getIdToken(user);
                        setJwtToken(token);
                    } catch (error) {
                        console.error("Error fetching JWT token:", error);
                    }
                } else {
                    await signOut(auth);
                    navigate("/", { replace: true });
                }
            };
            fetchUserData();
        });
        return () => unsubscribe();
    }, [navigate]);

    const handleLogout = async () => {
        await signOut(auth);
        navigate("/", { replace: true });
    };

    const handleCreateAccount = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setErrorMessage(null);
        setSuccessMessage(null);

        try {
            password.trim();
            if (password.length < 6) {
                setLoading(false);
                setErrorMessage("Error: Password must be > 6 characters long");
                return;
            }
            confirmPassword.trim();
            if (password !== confirmPassword) {
                setLoading(false);
                setErrorMessage("Error: Passwords don't match");
                return;
            }

            if (!jwtToken) {
                setLoading(false);
                setErrorMessage("Error: JWT token not found");
                return;
            }
            else {
                username.trim();
                const result = await createUser(username, password, jwtToken);
                setLoading(false);
                if (result.success) {
                    setSuccessMessage(`Created user: ${username}`);
                    setUsername(""); setPassword(""); setConfirmPassword("");
                    navigate("/CreateUserSuccess", {
                        replace: true,
                        state: { username: username, password: password }
                    });
                }
                else {
                    setErrorMessage(result.error);
                }
            }
        } catch (error: any) {
            console.error("Account creation failed:", error);
            setErrorMessage(error.message || "An error occurred");
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
            {/* Navbar */}
            <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
                <FontAwesomeIcon 
                    icon={faHouse} 
                    onClick={() => navigate("/home")}
                    className="text-2xl cursor-pointer absolute left-6" 
                />
                <h1 className="text-xl font-semibold align-self-center">Create User</h1>
                <button 
                onClick={handleLogout} 
                className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
                >
                Logout
                </button>
            </nav>

            {/* Error or Success */}
            {(errorMessage || successMessage) && (
                <div className="fixed top-20 w-full flex justify-center z-50">
                <div className={`px-6 py-3 rounded-xl shadow-md w-full max-w-md flex justify-between items-center ${
                    errorMessage ? "bg-red-500 text-white" : "bg-green-500 text-white"
                }`}>
                    <span className="text-sm">
                    {errorMessage || successMessage}
                    </span>
                    <button
                    className="ml-4 font-bold hover:text-gray-200 transition"
                    onClick={() => {
                        setErrorMessage(null);
                        setSuccessMessage(null);
                    }}
                    >
                    ✕
                    </button>
                </div>
                </div>
            )}

            {/* Form */}
            <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-md mt-24">
                <h2 className="text-2xl font-semibold text-center mb-6">Create New User</h2>

                <form onSubmit={handleCreateAccount}>
                {/* Username */}
                <div className="mb-6">
                    <label className="block text-gray-700 font-medium mb-2">Username</label>
                    <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="Username"
                    />
                </div>
                {/* Password */}
                <div className="mb-6">
                    <label className="block text-gray-700 font-medium mb-2">Password</label>
                    <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="At least 6 characters"
                    required
                    />
                </div>
                {/* Confirm Password */}
                <div className="mb-6">
                    <label className="block text-gray-700 font-medium mb-2">Confirm Password</label>
                    <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="Passwords Must Match"
                    required
                    />
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    className={`w-full p-3 rounded-lg transition ${
                    username && password
                        ? "cursor-pointer bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-400 text-gray-200 cursor-not-allowed"
                    }`}
                    disabled={!username || !password}
                >
                    Create Account
                </button>
                </form>
            </div>

            {/* Loading Overlay (Blocks clicks and dims background) */}
            {loading && (
                <div className="fixed inset-0 w-full h-full bg-black/50 flex items-center justify-center z-50">
                <div className="border-t-4 border-white border-solid rounded-full w-16 h-16 animate-spin"></div>
                </div>
            )}
        </div>
    );
};

export default CreateUser;
