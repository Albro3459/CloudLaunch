import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUserRole, lambdaHelper } from "../helpers/APIHelper";
import { auth, getIdToken, onAuthStateChanged, signOut } from "../firebase";
import { live_regions } from "../helpers/live_regions";

const Home: React.FC = () => {
  const navigate = useNavigate();
//   const [username, setUsername] = useState<string | null>(null);

  const [region, setRegion] = useState("");
  // const [instanceName, setInstanceName] = useState("");
  const [role, setRole] = useState<string | null>(null);
  const [jwtToken, setJwtToken] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    setRegion('us-west-1'); // :) temporary
    
    try {
        if (!jwtToken) {
            console.error("Error: JWT token not found");
        }
        else {
            const response = await lambdaHelper(region, jwtToken);
        
            setLoading(false);

            if (!response.success) {
                setErrorMessage(response.error || "Something went wrong");
                return;
            }

            const { public_ipv4, client_private_key, server_public_key } = response.data;
            console.log(public_ipv4);

            navigate("/Success", {
                replace: true,
                state: { instanceName: null, region: region, ip: public_ipv4, client_private_key: client_private_key, server_public_key: server_public_key }
            });
        }

    } catch (error) {
      console.error("Error during deployment:", error);
    }
  };

  
  const handleCreateNewAccount = () => {
    navigate("/CreateUser", { replace: true });
  }


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
              {live_regions.map((region) => (
                <option key={region.value} value={region.value}>
                  {region.name}
                </option>
              ))}
            </select>
          </div>

          {/* Instance Name Input
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
          </div> */}

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

      { /* ADMIN ONLY: Make test account */ }
      {role && role === "admin" &&
        <div className="pt-4">
          <button 
              onClick={handleCreateNewAccount} 
              className={"w-full p-3 rounded-lg transition cursor-pointer bg-blue-600 text-white hover:bg-blue-700"}
              >
                Create Test Account
          </button>
        </div>
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
