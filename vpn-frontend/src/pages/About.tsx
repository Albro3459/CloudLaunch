import React from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouse } from "@fortawesome/free-solid-svg-icons"; // Home icon

const About: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        {/* Navbar */}
        <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
            <FontAwesomeIcon 
                icon={faHouse} 
                onClick={() => navigate("/home")}
                className="text-2xl cursor-pointer absolute left-6" 
            />
            <h1 className="text-xl font-semibold align-self-center">About</h1>
            <button 
            onClick={() => navigate("/")} 
            className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
            >
            Logout
            </button>
        </nav>

        {/* About Section */}
        <div className="bg-white p-8 rounded-2xl shadow-lg w-128 text-center">
            <h2 className="text-2xl font-semibold mb-4">What is VPN Cloud Automation?</h2>
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
