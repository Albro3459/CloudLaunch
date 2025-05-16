import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { saveAs } from "file-saver";
import QRCode from "qrcode";

import { ACTION, SecureGetHelper, Targets, TERRAFORM_ENUM, terraformHelper, VPNdeployHelper } from "../helpers/APIHelper";
import { auth, getIdToken, onAuthStateChanged, signOut } from "../firebase";
import { aws_regions, getLiveRegions, getRegionName, Region } from "../helpers/regionsHelper";
import { getUserRole } from "../helpers/usersHelper";
import { SOURCE_REGION } from "../Secrets/source_region";

import { VPNTable, VPNTableEntry } from "../components/VPNTable";
import { getUsersVPNs, VPNData } from "../helpers/firebaseDbHelper";
import { User } from "firebase/auth";
import { generateConfig } from "../helpers/configHelper";

export enum TOGGLE {
    ADD,
    REMOVE
}

const Home: React.FC = () => {
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const [user, setUser] = useState<User | null>(null);
    const [email, setEmail] = useState<string | null>(null);
    const [role, setRole] = useState<string | null>(null);
    const [jwtToken, setJwtToken] = useState<string | null>(null);

    const [liveRegions, setLiveRegions] = useState<Region[] | null>();

    const [region, setRegion] = useState("");
    const [terraformRegion, setTerraformRegion] = useState("");
    const [cleanRegion, setCleanRegion] = useState("");

    const [VPNTableEntries, setVPNTableEntries] = useState<VPNTableEntry[]>([]);
    const [vpnRegion, setVpnRegion] = useState<string | null>(null);
    const [IP, setIP] = useState<string | null>(null);
    const [clientPrivateKey, setClientPrivateKey] = useState<string | null>(null);
    const [serverPublicKey, setServerPublicKey] = useState<string | null>(null);
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
                const response = await VPNdeployHelper(ACTION.DEPLOY, null, email || "", region, jwtToken);
            
                setLoading(false);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                const { isNew, public_ipv4, client_private_key, server_public_key } = response.data;

                navigate("/VPNSuccess", {
                    replace: true,
                    state: { region: getRegionName(region), isNew: isNew, ip: public_ipv4, client_private_key: client_private_key, server_public_key: server_public_key }
                });
            }

        } catch (error) {
            setErrorMessage("Error during deployment");
            console.error("Error during deployment:", error);
        }
    };

    const handleTerraformSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            if (!jwtToken) {
                setErrorMessage("Error: JWT token not found");
                console.error("Error: JWT token not found");
            }
            else {
                const response = await terraformHelper(terraformRegion, jwtToken, TERRAFORM_ENUM.TERRAFORM);
            
                setLoading(false);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                const { target_region, region_cleaned } = response.data;

                if (!target_region) {
                    setErrorMessage(`Terraform of target region ${terraformRegion} failed`);
                }

                navigate("/terraformSuccess", {
                    replace: true,
                    state: { region: getRegionName(target_region) }
                });
            }

        } catch (error) {
            setErrorMessage("Error during terraform");
            console.error("Error during terraform:", error);
        }
    };

    const handleTerraformClean = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            if (!jwtToken) {
                setErrorMessage("Error: JWT token not found");
                console.error("Error: JWT token not found");
            }
            else {
                const response = await terraformHelper(cleanRegion, jwtToken, TERRAFORM_ENUM.CLEAN);
            
                setLoading(false);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                const { target_region, region_cleaned } = response.data;

                if (!region_cleaned) {
                    setErrorMessage(`Cleaning region ${cleanRegion} failed`);
                }

                navigate("/cleanSuccess", {
                    replace: true,
                    state: { region: getRegionName(region_cleaned) }
                });
            }

        } catch (error) {
            setErrorMessage("Error during clean");
            console.error("Error during clean:", error);
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

                const { action_completed } = response.data;

                console.log("ACTION COMPLETED: ", action_completed);

                setTargets({});

                if (user) {
                    await fillVPNs(user);
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
    const secureGet = useCallback(async () => {
        try {
            if (!jwtToken) {
                setErrorMessage("Error: JWT token not found");
                console.error("Error: JWT token not found");
                return null;
            }
            else {
                const response = await SecureGetHelper(["client_private_key", "server_public_key"], jwtToken);
            
                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return null;
                }

                const { client_private_key, server_public_key } = response.data;

                setClientPrivateKey(client_private_key);
                setServerPublicKey(server_public_key);

                return { client_private_key, server_public_key };
            }

        } catch (error) {
            setErrorMessage("Error while fetching secrets");
            console.error("Error while fetching secrets: ", error);
            return null;
        }
    }, [jwtToken]);
    
    const handleQRcode = useCallback(async (IPv4: string, region: string | null) => {
        if (!IPv4) {
            setErrorMessage("Invalid IP address for QR code.");
            console.error("Invalid IP address for QR code.");
            return;
        }

        setLoading(true);

        setIP(IPv4); setVpnRegion(region);

        // Cache the keys
        let clientKey = clientPrivateKey;
        let serverKey = serverPublicKey;
        if (!clientKey || !serverKey) {
            const secrets = await secureGet();
            if (secrets) {
                clientKey = secrets.client_private_key;
                serverKey = secrets.server_public_key;
            }
        }
        
        if (clientKey && serverKey) {
            const config = await generateConfig(clientKey, serverKey, IPv4);
            setConfigData(config);
        } else {
            setErrorMessage("Failed to retrieve keys for QR code.");
            console.error("Failed to retrieve keys for QR code.");
        }

        setLoading(false);
    }, [clientPrivateKey, serverPublicKey, secureGet]);
    
    
    const handleCreateNewAccount = () => {
        if (role === "admin") {
            navigate("/CreateUser", { replace: true });
        }
    }

    const fillVPNs = useCallback(async (user: User) => {
        const VPNs: VPNData[] = await getUsersVPNs(user);
        setVPNTableEntries(VPNs.map((vpn) => ({
            ...vpn,
            onQrCodeClick: () => handleQRcode(vpn.ipv4, vpn.region),
        })))
    }, [handleQRcode]);

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
        const fetchLiveRegions = async () => {
            const result = await getLiveRegions();
            if (result) {
                setLiveRegions(result); // assuming useState
            }
        };

        fetchLiveRegions();
    }, []);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    setUser(user);
                    setRole(await getUserRole(user));
                    setEmail(user.email);
                    await fillVPNs(user);
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
    }, [navigate, fillVPNs]);

    const handleLogout = async () => {
        await signOut(auth);
        navigate("/", { replace: true });
    };

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
                <h1 className="text-xl font-semibold align-self-center">VPN Deployment</h1>
                <button 
                onClick={handleLogout} 
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
                {/* AWS Region Dropdown */}
                <div className="mb-6">
                    <label className="block text-gray-700 font-medium mb-2">Select AWS Region</label>
                    <select
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                    >
                    <option value="">Select a region</option>
                    {liveRegions && liveRegions.length > 0 &&
                    liveRegions.map((region) => (
                        <option key={region.value} value={region.value}>
                        {region.name}
                        </option>
                    ))}
                    </select>
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
                    // disabled={!region || !instanceName}
                    disabled={!region}
                    className={`w-full p-3 rounded-lg transition ${
                    region 
                    // && instanceName
                        ? "cursor-pointer bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-400 text-gray-200 cursor-not-allowed"
                    }`}
                >
                    Deploy VPN
                </button>
                </form>
            </div>

            { /* ADMIN ONLY */ }
            {role && role === "admin" &&
            <>
                <div className="bg-white mt-8 p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-md">
                    <h2 className="text-2xl font-semibold text-center mb-6">Terraform New Region</h2>

                    <form onSubmit={async (e) => { await handleTerraformSubmit(e); }}>
                        {/* AWS Region Dropdown */}
                        <div className="mb-6">
                            <label className="block text-gray-700 font-medium mb-2">Select AWS Region</label>
                            <select
                            value={terraformRegion}
                            onChange={(e) => setTerraformRegion(e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            required
                            >
                            <option value="">Select a region</option>
                            {liveRegions && liveRegions.length > 0 &&
                            aws_regions.filter((region) => !liveRegions.map((r) => r.value).includes(region.value))
                                .map((region) => (
                                    <option key={region.value} value={region.value}>
                                        {region.name}
                                    </option>
                                ))
                            }
                            </select>
                        </div>
                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={!terraformRegion}
                            className={`w-full p-3 rounded-lg transition ${
                                terraformRegion 
                                ? "cursor-pointer bg-green-600 text-white hover:bg-green-700"
                                : "bg-gray-400 text-gray-200 cursor-not-allowed"
                            }`}
                        >
                            Terraform Region
                        </button>
                    </form>
                </div>
                <div className="bg-white mt-8 p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-md">
                    <h2 className="text-2xl font-semibold text-center mb-6">Clean Region</h2>
                    <form onSubmit={async (e) => { await handleTerraformClean(e); }}>
                        {/* AWS Region Dropdown */}
                        <div className="mb-6">
                            <label className="block text-gray-700 font-medium mb-2">Select AWS Region</label>
                            <select
                            value={cleanRegion}
                            onChange={(e) => setCleanRegion(e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            required
                            >
                            <option value="">Select a region</option>
                            {liveRegions && liveRegions.length > 0 &&
                            liveRegions.filter((region) => region.value !== SOURCE_REGION)
                                .map((region) => (
                                    <option key={region.value} value={region.value}>
                                        {region.name}
                                    </option>
                                ))
                            }
                            </select>
                        </div>
                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={!cleanRegion}
                            className={`w-full p-3 rounded-lg transition ${
                                cleanRegion 
                                ? "cursor-pointer bg-red-600 text-white hover:bg-red-700"
                                : "bg-gray-400 text-gray-200 cursor-not-allowed"
                            }`}
                        >
                            Clean Region
                        </button>
                    </form>
                </div>
            </>
            }
            
            {VPNTableEntries.length > 0 &&
                <VPNTable
                    data={VPNTableEntries}
                    isAdmin={role === "admin"}
                    targets={targets}
                    toggleTarget={toggleTarget}
                    actionFunc={handleTerminate}
                />
            }

            {/* QR code overlay with download button */}
            {configData && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
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
                                Region: <b>{vpnRegion}</b>
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
