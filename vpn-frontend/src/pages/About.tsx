import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouse } from "@fortawesome/free-solid-svg-icons"; // Home icon
import { auth, onAuthStateChanged, signOut } from "../firebase";

const About: React.FC = () => {
    const navigate = useNavigate();
    const [username, setUsername] = useState<string | null>(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    const email = user.email || "";
                    const extractedUsername = email.split("@")[0];
                    setUsername(extractedUsername);
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

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
            {/* Navbar */}
            <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
                <FontAwesomeIcon 
                    icon={faHouse} 
                    onClick={() => navigate("/home")}
                    className="text-2xl cursor-pointer absolute left-6" 
                />
                <h1 className="text-xl font-semibold align-self-center">About</h1>
                {username && username.length > 0 &&            
                <button 
                    onClick={handleLogout} 
                    className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
                >
                    Logout
                </button>
                }
            </nav>
    
            {/* About Section */}
            <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-xl text-center mx-4">
                <h2 className="text-2xl font-semibold mb-2">What is VPN Cloud Automation?</h2>
                <div className="ps-2 text-sm mb-2">
                    <b>Created by: </b>Alex Brodsky 
                    <br></br>
                    <a
                        href="https://github.com/Albro3459/VPN_Cloud_Automation/tree/main"
                        className="text-xs text-blue-600 underline hover:text-blue-800"
                        >
                        GitHub
                    </a>
                    <span> |   </span>
                    <a
                        href="https://www.linkedin.com/in/brodsky-alex22/"
                        className="text-xs text-blue-600 underline hover:text-blue-800"
                        >
                        LinkedIn
                    </a>
                    <span> |   </span>
                    <a
                        href="mailto:Brodsky.Alex22@gmail.com"
                        className="text-xs text-blue-600 underline hover:text-blue-800"
                        >
                        Email
                    </a>
                </div>
                <p className="text-gray-700 mb-4">
                    Instantly deploy a secure <b>WireGuard VPN</b> on an AWS EC2 instance in the region of your choice, 
                    pre-configured for both IPv4 and IPv6 connectivity.
                </p>
                <p className="text-gray-700 mb-4">
                    The entire deployment process is automated using <b>AWS Lambda</b>, ensuring a fast, efficient, 
                    and hassle-free setup.
                </p>
                <p className="text-gray-700 mb-4">
                    Generate your VPN configuration instantly, download the <b>.conf</b> file, or scan a QR code for easy setup on 
                    your devices—all in just a few clicks.
                </p>
                <p className="text-gray-700">
                    <b>Secure, simple, and instant.</b> Your personal cloud VPN, deployed on demand.
                </p>
            </div>
        </div>
    );    
};

export default About;
