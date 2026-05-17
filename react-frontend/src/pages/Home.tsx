import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { saveAs } from "file-saver";
import QRCode from "qrcode";

import { ACTION, Targets, VPNdeployHelper } from "../helpers/APIHelper";
import { auth, onAuthStateChanged } from "../firebase";
import { getRegionName } from "../helpers/regionsHelper";
import { getUserRole } from "../helpers/usersHelper";

import { VPNTable, VPNTableEntry } from "../components/VPNTable";
import { getUsersVPNs, logout, VPNData } from "../helpers/firebaseDbHelper";
import { User } from "firebase/auth";
import { fetchOciRegions, useOciRegionsStore } from "../stores/ociRegionsStore";
import { normalizeVPNStatus } from "../helpers/vpnStatus";

export enum TOGGLE {
    ADD,
    REMOVE
}

const Home: React.FC = () => {
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const [role, setRole] = useState<string | null>(null);
    const [jwtToken, setJwtToken] = useState<string | null>(null);

    const { ociRegions } = useOciRegionsStore();

    const [region, setRegion] = useState("");

    const [VPNTableEntries, setVPNTableEntries] = useState<VPNTableEntry[] | null>(null);
    const [vpnRegion, setVpnRegion] = useState<string | null>(null);
    const [IP, setIP] = useState<string | null>(null);
    const [configData, setConfigData] = useState<string | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    const handleDeploySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            if (!jwtToken) {
                setErrorMessage("Error: JWT token not found");
                console.error("Error: JWT token not found");
            }
            else {
                const response = await VPNdeployHelper(ACTION.DEPLOY, null, auth.currentUser?.email || "", region, jwtToken);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    if (auth.currentUser) {
                        await fillVPNs(auth.currentUser);
                    }
                    return;
                }

                const { isNew, status, region: deployRegion, ip_addresses, wireguard_config } = response.data;
                const deployStatus = normalizeVPNStatus(status);
                const publicIPv4 = ip_addresses?.public_ipv4 || "";
                const ociRegion = deployRegion?.oci_region || region;
                const ociRegionName = deployRegion?.oci_region_name || getRegionName(ociRegion, ociRegions);

                navigate("/VPNSuccess", {
                    replace: true,
                    state: {
                        region: ociRegionName,
                        isNew: isNew,
                        status: deployStatus,
                        ip: publicIPv4,
                        wireguard_config: wireguard_config
                    }
                });
            }

        } catch (error) {
            setErrorMessage("Error during deployment");
            console.error("Error during deployment:", error);
            if (auth.currentUser) {
                await fillVPNs(auth.currentUser);
            }
        } finally {
            setLoading(false);
        }
    };

    // Terminate Action

    const [targets, setTargets] = useState<Targets>({});
    
    const toggleTarget = (toggle: TOGGLE, userID: string, region: string | null, instanceID: string) => {
        if (!region) return;
    
        setTargets(prev => {
            const updated = { ...prev };

            if (toggle === TOGGLE.ADD) {
                if (!updated[userID]) {
                    updated[userID] = {};
                }
                if (!updated[userID][region]) {
                    updated[userID][region] = [];
                }
                if (!updated[userID][region].includes(instanceID)) {
                    updated[userID][region].push(instanceID);
                }
            }
            else if (toggle === TOGGLE.REMOVE) {
                if (updated[userID]?.[region]) {
                    updated[userID][region] = updated[userID][region].filter(id => id !== instanceID);
        
                    if (updated[userID][region].length === 0) {
                        delete updated[userID][region];
                    }
        
                    if (Object.keys(updated[userID]).length === 0) {
                        delete updated[userID];
                    }
                }
            }
    
            return updated;
        });
    };    

    const handleTerminate = async (targets: Targets) => {
        if (Object.keys(targets).length === 0) {
            setErrorMessage("No instances selected");
            return;
        }

        setLoading(true);
        
        try {
            if (!jwtToken) {
                setErrorMessage("Error: JWT token not found");
                console.error("Error: JWT token not found");
                return;
            }
            else {
                const response = await VPNdeployHelper(ACTION.TERMINATE, targets, null, null, jwtToken);
            
                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                setTargets({});

                if (auth.currentUser) {
                    await fillVPNs(auth.currentUser);
                }
            }

        } catch (error) {
            setErrorMessage("Error during termination");
            console.error("Error during termination:", error);
        } finally {
            setLoading(false);
        }
    };

    // QR code functions
    
    const handleQRcode = useCallback((vpn: VPNTableEntry) => {
        if (!vpn.ipv4 || !vpn.wireguardConfig) {
            setErrorMessage("Config not available for QR code.");
            console.error("Config not available for QR code.");
            return;
        }

        setIP(vpn.ipv4); 
        setVpnRegion(vpn.region);
        setConfigData(vpn.wireguardConfig);
    }, []);
    
    
    const handleCreateNewAccount = () => {
        if (role === "admin") {
            navigate("/CreateUser", { replace: true });
        }
    }

    const fillVPNs = useCallback(async (user: User) => {
        setVPNTableEntries(null);
        try {
            const VPNs: VPNData[] = await getUsersVPNs(user);
            setVPNTableEntries(VPNs);
        } catch (error) {
            setErrorMessage("Error loading VPN instances");
            console.error("Error loading VPN instances:", error);
            setVPNTableEntries([]);
        }
    }, []);

    const handleDownload = () => {
        if (configData) {
            const blob = new Blob([configData], { type: "text/plain;charset=utf-8" });
            saveAs(blob, `wireguard.conf`);
        }
    };

    useEffect(() => {
        if (configData && canvasRef.current) {
            QRCode.toCanvas(canvasRef.current, configData, {
                width: 250,
            }, (error) => {
                if (error) console.error("QR Code generation failed:", error);
            });
        }
    }, [configData]);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    void fillVPNs(user); // Not awaiting
                    const token: string | null = await user.getIdToken();
                    setJwtToken(token);
                    
                    setRole(await getUserRole(user));
                    
                    void fetchOciRegions(token); // Not awaiting
                } else {
                    await logout(navigate);
                }
            };
            void fetchUserData();
        });
        return () => unsubscribe();
    }, [navigate, fillVPNs]);

    useEffect(() => {
        if (!region && ociRegions?.length) {
            setRegion(ociRegions[0].value);
        }
    }, [ociRegions, region]);

    return (
        // <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
        <div className={`flex flex-col items-center min-h-screen bg-gray-100 px-4 
                                ${role && role === "admin" ? "justify-start pt-24 pb-20 overflow-y-auto" : "justify-center px-4" }`
                        }>
            {/* Navbar */}
            <nav className="w-full bg-blue-600 text-white p-4 shadow-md fixed top-0 left-0 flex justify-center items-center px-6">
                <button 
                    onClick={() => navigate("/about")} 
                    className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute left-6"
                >
                    About
                </button>
                <h1 className="text-xl font-semibold align-self-center">CloudLaunch</h1>
                <button 
                    onClick={async () => await logout(navigate)} 
                    className="cursor-pointer bg-gray-300 text-blue-600 hover:bg-gray-100 px-4 py-2 rounded-lg transition absolute right-6"
                >
                    Logout
                </button>
            </nav>
            {errorMessage && (
                <div className="fixed top-20 w-full flex justify-center z-50">
                <div className="bg-red-500 text-white px-6 py-3 rounded-xl shadow-md w-full max-w-md flex justify-between items-center">
                    <span className="text-sm">{errorMessage}</span>
                    <button
                    className="ml-4 font-bold hover:text-gray-200 transition"
                    onClick={() => setErrorMessage(null)}
                    >
                    ✕
                    </button>
                </div>
                </div>
            )}

            { /* ADMIN ONLY */ }
            {role && role === "admin" &&
            <div className="pb-4">
                <button 
                    onClick={handleCreateNewAccount} 
                    className={"w-full p-3 rounded-lg transition cursor-pointer bg-blue-600 text-white hover:bg-blue-700"}
                    >
                        Create Test Account
                </button>
            </div>
            }

            {/* Deployment Form */}
            <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-md">
                <h2 className="text-2xl font-semibold text-center mb-6">Deploy VPN Instance</h2>

                <form onSubmit={async (e) => { await handleDeploySubmit(e); }}>
                {/* Region Display */}
                <div className="mb-6">
                    <p className="block text-gray-700 font-medium mb-2">Region</p>
                    <div className="w-full p-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-800">
                        {getRegionName(region, ociRegions) || "Loading region"}
                    </div>
                    {role && role !== "admin" &&
                        <div className="ps-2 mt-2 text-xs">
                            <a
                            href="mailto:Brodsky.Alex22@gmail.com"
                            className="text-blue-600 underline hover:text-blue-800"
                            >
                            Email me to request a region
                            </a>
                        </div>
                    }
                </div>
                {/* Submit Button */}
                <button
                    type="submit"
                    disabled={!region}
                    className={`w-full p-3 rounded-lg transition ${
                    region 
                        ? "cursor-pointer bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-400 text-gray-200 cursor-not-allowed"
                    }`}
                >
                    Deploy VPN
                </button>
                </form>
            </div>
            
            <VPNTable
                data={VPNTableEntries}
                isAdmin={role === "admin"}
                regions={ociRegions}
                targets={targets}
                toggleTarget={toggleTarget}
                actionFunc={handleTerminate}
                onQRCodeClick={handleQRcode}
            />

            {/* QR code overlay with download button */}
            {configData && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white p-6 rounded-2xl shadow-lg text-center relative max-w-md w-full">
                        <button
                            onClick={() => { setConfigData(null); setIP(null) }}
                            className="absolute top-2 right-3 text-gray-500 hover:text-black text-lg font-bold"
                        >
                            ×
                        </button>
                        <h3 className="text-2xl font-semibold mb-2">VPN QR Code</h3>

                        {vpnRegion && (
                            <p className="pt-1 text-gray-700">
                                Region: <b>{getRegionName(vpnRegion, ociRegions)}</b>
                            </p>
                        )}

                        {IP && (
                            <p className="pt-1 text-gray-700">
                                IP Address: <b>{IP}</b>
                            </p>
                        )}
                        <canvas ref={canvasRef} className="mt-2 mx-auto" />
                        <button
                            onClick={handleDownload}
                            className="cursor-pointer bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition mt-4"
                        >
                            Download Config
                        </button>
                    </div>
                </div>
            )}

            {/* Loading Overlay (Blocks clicks and dims background) */}
            {loading && (
                <div className="fixed inset-0 w-full h-full bg-black/50 flex items-center justify-center z-50">
                    <div className="border-t-4 border-white border-solid rounded-full w-16 h-16 animate-spin"></div>
                </div>
            )}
        </div>
    );
};

export default Home;
