import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { generateConfig } from "../helpers/configHelper";
import QRCode from "qrcode";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHouse } from "@fortawesome/free-solid-svg-icons"; // Home icon
import { saveAs } from "file-saver";
import { auth, onAuthStateChanged, signOut } from "../firebase";

interface VPNSuccessState {
    region: string | null;
    isNew: boolean | null;
    ip: string | null;
    client_private_key: string | null;
    server_public_key: string | null;
  }

const VPNSuccess: React.FC = () => {
    const navigate = useNavigate();

    const location = useLocation();
    const { 
        region,
        isNew,
        ip,
        client_private_key, 
        server_public_key
    } = (location.state || {}) as Partial<VPNSuccessState>;
    
    const [configData, setConfigData] = useState<string | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    useEffect(() => {
        // console.log(ip);
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
            saveAs(blob, `wireguard.conf`);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
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
                onClick={handleLogout} 
                className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
                >
                Logout
                </button>
            </nav>

            <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-lg text-center">
                <h2 className="text-2xl font-semibold mb-4">
                    {isNew ? (
                        <>
                            Deployment  {ip && ip.length > 0 ? "Successful 🎉" : "Failure ❌"}
                        </>
                    ) : (
                        <>
                            {ip && ip.length > 0 ? "Success 🎉" : "Fail ❌"}
                        </>
                    )}
                    
                </h2>

                {ip && ip.length > 0 ? (
                    <p className="text-gray-700">
                        {isNew ? (
                            <>
                                A new VPN has been deployed in <b>{region}</b>.
                            </>
                        ) : (
                            <>
                                A VPN has been found in <b>{region}</b>.
                            </>
                        )}
                    </p>
                ) : (
                    <p className="text-gray-700">No VPN was deployed.</p>
                )}

                {ip && ip.length > 0 && (
                    <p className="pt-1 text-gray-700">
                    IP Address: <b>{ip}</b>
                    </p>
                )}

                {/* QR Code Canvas */}
                {ip && ip.length > 0 && (
                    <>
                    <canvas ref={canvasRef} className="mt-4 mx-auto"></canvas>
                    <button 
                        onClick={handleDownload} 
                        className="cursor-pointer w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition mt-6"
                    >
                        Download Config
                    </button>
                    </>
                )}
                </div>

        </div>
    );
};

export default VPNSuccess;