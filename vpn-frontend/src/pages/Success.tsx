import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { generateConfig } from "../helpers/confHelper";
import QRCode from "qrcode";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHouse } from "@fortawesome/free-solid-svg-icons"; // Home icon
import { saveAs } from "file-saver";
import { auth, onAuthStateChanged, signOut } from "../firebase";

const Success: React.FC = () => {
    const navigate = useNavigate();
    // const [username, setUsername] = useState<string | null>(null);

    const location = useLocation();
    const { 
        instanceName = "instanceName", 
        region = "region", 
        ip = "0.0.0.0",
        client_private_key = "client_private_key", 
        server_public_key = "server_public_key"
    } = location.state || {};
    
    const [configData, setConfigData] = useState<string | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    useEffect(() => {
        if (client_private_key && server_public_key && ip) {
        const config = generateConfig(client_private_key, server_public_key, ip);
        setConfigData(config);
        }
    }, [client_private_key, server_public_key, ip]);

    useEffect(() => {
        if (configData && canvasRef.current) {
            QRCode.toCanvas(canvasRef.current, configData, {
                width: 250,
            }, (error) => {
                if (error) console.error("QR Code generation failed:", error);
            });
        }
    }, [configData]);

    const handleDownload = () => {
        if (configData) {
        const blob = new Blob([configData], { type: "text/plain;charset=utf-8" });
        saveAs(blob, `wg-${instanceName}.conf`);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    // const email = user.email || "";
                    // const extractedUsername = email.split("@")[0];
                    // setUsername(extractedUsername);
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

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        {/* Navbar */}
        <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
            <FontAwesomeIcon 
                icon={faHouse} 
                onClick={() => navigate("/home")}
                className="text-2xl cursor-pointer absolute left-6" 
            />
            <h1 className="text-xl font-semibold align-self-center">VPN Deployment</h1>
            <button 
            onClick={handleLogout} 
            className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
            >
            Logout
            </button>
        </nav>

        <div className="bg-white p-8 rounded-2xl shadow-lg w-114 text-center">
            <h2 className="text-2xl font-semibold mb-4">Deployment Successful 🎉</h2>
            <p className="text-gray-700">
            Instance <b>{instanceName}</b> has been deployed in <b>{region}</b>.
            </p>
            <p className="pt-1 text-gray-700">IP Address: <b>{ip}</b></p>

            {/* QR Code Canvas */}
            <canvas ref={canvasRef} className="mt-4 mx-auto"></canvas>

            {/* Download Config Button */}
            <button 
            onClick={handleDownload} 
            className="cursor-pointer w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition mt-6"
            >
            Download Config
            </button>
        </div>
        </div>
    );
};

export default Success;