import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { lambdaHelper } from "../helpers/lambdaHelper";
import { auth, getIdToken, onAuthStateChanged, signOut } from "../firebase";

const Home: React.FC = () => {
  const navigate = useNavigate();
//   const [username, setUsername] = useState<string | null>(null);

  const [region, setRegion] = useState("");
  const [instanceName, setInstanceName] = useState("");
  const [jwtToken, setJwtToken] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);

  const awsRegions = [
    { name: "Virginia", value: "us-east-1" },
    { name: "Ohio", value: "us-east-2" },
    { name: "California", value: "us-west-1" },
    { name: "Oregon", value: "us-west-2" },
    { name: "Montreal", value: "ca-central-1" },
    { name: "São Paulo", value: "sa-east-1" },
    { name: "Ireland", value: "eu-west-1" },
    { name: "England", value: "eu-west-2" },
    { name: "France", value: "eu-west-3" },
    { name: "Germany", value: "eu-central-1" },
    { name: "Stockholm", value: "eu-north-1" },
    { name: "Spain", value: "eu-south-1" },
    { name: "UAE", value: "me-central-1" },
    { name: "Cape Town", value: "af-south-1" },
    { name: "Tokyo", value: "ap-northeast-1" },
    { name: "Seoul", value: "ap-northeast-2" },
    { name: "Osaka", value: "ap-northeast-3" },
    { name: "Hong Kong", value: "ap-east-1" },
    { name: "Mumbai", value: "ap-south-1" },
    { name: "Hyderabad", value: "ap-south-2" },
    { name: "Singapore", value: "ap-southeast-1" },
    { name: "Sydney", value: "ap-southeast-2" },
    { name: "Jakarta", value: "ap-southeast-3" },
    { name: "Melbourne", value: "ap-southeast-4" },
  ];
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    setRegion('us-west-1'); // :) temporary
    
    try {
        if (!jwtToken) {
            console.error("Error: JWT token not found");
        }
        else {
            const response = await lambdaHelper(region, instanceName, jwtToken);
        
            setLoading(false);

            if (!response) {
                console.error("API call failed");
                navigate("/Home", { replace: true });
            }

            const { public_ipv4, client_private_key, server_public_key } = response;

            navigate("/Success", {
                replace: true,
                state: { instanceName: instanceName, region: region, ip: public_ipv4, client_private_key: client_private_key, server_public_key: server_public_key }
            });
        }

    } catch (error) {
      console.error("Error during deployment:", error);
    }
  };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            const fetchUserData = async () => {
                if (user) {
                    // const email = user.email || "";
                    // const extractedUsername = email.split("@")[0];
                    // setUsername(extractedUsername);
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

      {/* Deployment Form */}
      <div className="bg-white p-6 md:p-8 rounded-2xl shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-semibold text-center mb-6">Deploy VPN Instance</h2>

        <form onSubmit={async (e) => { await handleSubmit(e); }}>
          {/* AWS Region Dropdown */}
          <div className="mb-6">
            <label className="block text-gray-700 font-medium mb-2">Select AWS Region</label>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              required
            >
              <option value="" disabled>Select a region</option>
              {awsRegions.map((region) => (
                <option key={region.value} value={region.value}>
                  {region.name}
                </option>
              ))}
            </select>
          </div>

          {/* Instance Name Input */}
          <div className="mb-8">
            <label className="block text-gray-700 font-medium mb-2">Instance Name</label>
            <input
              type="text"
              value={instanceName}
              onChange={(e) => setInstanceName(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Enter instance name"
              required
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!region || !instanceName}
            className={`w-full p-3 rounded-lg transition ${
              region && instanceName
                ? "cursor-pointer bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-400 text-gray-200 cursor-not-allowed"
            }`}
          >
            Deploy VPN
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

export default Home;
