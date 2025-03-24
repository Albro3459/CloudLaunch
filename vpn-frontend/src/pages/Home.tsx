import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { terraformHelper, VPNdeployHelper } from "../helpers/APIHelper";
import { auth, getIdToken, onAuthStateChanged, signOut } from "../firebase";
import { aws_regions, getLiveRegions, Region } from "../helpers/regionsHelper";
import { getUserRole } from "../helpers/usersHelper";

const Home: React.FC = () => {
    const navigate = useNavigate();
    //   const [username, setUsername] = useState<string | null>(null);
    const [liveRegions, setLiveRegions] = useState<Region[] | null>();

    const [region, setRegion] = useState("");
    const [terraformRegion, setTerraformRegion] = useState("");
    // const [instanceName, setInstanceName] = useState("");
    const [role, setRole] = useState<string | null>(null);
    const [jwtToken, setJwtToken] = useState<string | null>(null);

    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    
    const handleDeploySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            if (!jwtToken) {
                console.error("Error: JWT token not found");
            }
            else {
                const response = await VPNdeployHelper(region, jwtToken);
            
                setLoading(false);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                const { public_ipv4, client_private_key, server_public_key } = response.data;

                navigate("/Success", {
                    replace: true,
                    state: { instanceName: null, region: region, ip: public_ipv4, client_private_key: client_private_key, server_public_key: server_public_key }
                });
            }

        } catch (error) {
        console.error("Error during deployment:", error);
        }
    };

    const handleTerraformSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            if (!jwtToken) {
                console.error("Error: JWT token not found");
            }
            else {
                const response = await terraformHelper(terraformRegion, jwtToken);
            
                setLoading(false);

                if (!response.success) {
                    setErrorMessage(response.error || "Something went wrong");
                    return;
                }

                navigate("/terraformSuccess", {
                    replace: true,
                    state: { region: terraformRegion }
                });
            }

        } catch (error) {
        console.error("Error during deployment:", error);
        }
    };

    
    const handleCreateNewAccount = () => {
        if (role === "admin") {
            navigate("/CreateUser", { replace: true });
        }
    }

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
                    // const email = user.email || "";
                    // const extractedUsername = email.split("@")[0];
                    // setUsername(extractedUsername);
                    setRole(await getUserRole(user));
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

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 px-4">
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
                        // && instanceName
                            ? "cursor-pointer bg-red-600 text-white hover:bg-red-700"
                            : "bg-gray-400 text-gray-200 cursor-not-allowed"
                        }`}
                    >
                        Terraform Region
                    </button>
                    </form>
                </div>
                <div className="pt-4">
                <button 
                    onClick={handleCreateNewAccount} 
                    className={"w-full p-3 rounded-lg transition cursor-pointer bg-blue-600 text-white hover:bg-blue-700"}
                    >
                        Create Test Account
                </button>
                </div>
            </>
            }

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
