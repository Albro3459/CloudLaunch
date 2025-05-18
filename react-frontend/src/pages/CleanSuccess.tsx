import React, { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHouse } from "@fortawesome/free-solid-svg-icons"; // Home icon
import { auth, onAuthStateChanged } from "../firebase";
import { logout } from "../helpers/firebaseDbHelper";

interface CleanSuccessState {
    region: string | null;
}

const CleanSuccess: React.FC = () => {
    const navigate = useNavigate();

    const location = useLocation();
    const { 
        region,
    } = (location.state || {}) as Partial<CleanSuccessState>;

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    if (!region || region.length <= 0) {
                        navigate("/home", { replace: true });
                    }
                } else {
                    await logout(navigate);
                }
            };
            fetchUserData();
        });
        return () => unsubscribe();
    }, [navigate, region]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
            {/* Navbar */}
            <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
                <FontAwesomeIcon 
                    icon={faHouse} 
                    onClick={() => navigate("/home")}
                    className="text-2xl cursor-pointer absolute left-6" 
                />
                <h1 className="text-xl font-semibold align-self-center">Success</h1>
                <button 
                onClick={async () => await logout(navigate)} 
                className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
                >
                Logout
                </button>
            </nav>

            <div className="bg-white p-6 xs:p-8 rounded-2xl shadow-lg w-full max-w-sm text-center">
                <h2 className="text-2xl font-semibold mb-4">{region && region.length > 0 ? "Cleaned Region 🎉" : "Failed to Clean Region ❌"}</h2>

                {region && region.length > 0 ? (
                    <p className="text-gray-700">
                        Region{" "}
                        { <b>{region}</b>} has been cleaned.
                    </p>
                ) : (
                    <p className="text-gray-700">No region was cleaned.</p>
                )}
                </div>

        </div>
    );
};

export default CleanSuccess;