import { User } from "firebase/auth";
import { auth, signOut } from "../firebase";
import { getFirestore, collection, getDocs } from "firebase/firestore";
import { NavigateFunction } from "react-router-dom";

import { getUserRole } from "./usersHelper";
import { useKeyStore } from "../stores/keyStore";
import { useLiveRegionsStore } from "../stores/liveRegionsStore";

export const logout = async (navigate: NavigateFunction) => {
    await signOut(auth);
    useKeyStore.getState().clearKeys();
    useLiveRegionsStore.getState().clearLiveRegions();
    navigate("/", { replace: true });
};

export type VPNData = {
    userID: string;
    email: string | null;
    region: string | null;
    instanceID: string;
    ipv4: string;
    status: string;
}

export const getUsersVPNs = async (user: User): Promise<VPNData[]> => {

    // if (await getUserRole(user) === "admin") {
    //     return await getAdminVPNs(user);
    // }

    // return await getVPNs(user.uid, user.email);
    return [
  {
    userID: "user",
    email: "example@email.com",
    region: "us-west-1", // California
    instanceID: "i-0abc123def456gh01",
    ipv4: "52.53.125.178",
    status: "Running"
  },
  {
    userID: "user",
    email: "example@email.com",
    region: "ap-northeast-1", // Tokyo
    instanceID: "i-0abc123def456gh02",
    ipv4: "192.27.42.1",
    status: "Running"
  },
  {
    userID: "user",
    email: "example@email.com",
    region: "sa-east-1", // Brazil
    instanceID: "i-0abc123def456gh03",
    ipv4: "127.0.48.3",
    status: "Running"
  },
  {
    userID: "user",
    email: "example@email.com",
    region: "eu-central-1", // Germany
    instanceID: "i-0abc123def456gh04",
    ipv4: "58.121.2.124",
    status: "Running"
  },
  {
    userID: "user",
    email: "example@email.com",
    region: "af-south-1", // South Africa
    instanceID: "i-0abc123def456gh05",
    ipv4: "52.0.82.5",
    status: "Running"
  }
];

};

const getVPNs = async (userID: string, email: string | null): Promise<VPNData[]> => {
    try {
        if (!email) {
            console.warn("Email null for user: " + userID);
            return [];
        }

        const db = getFirestore();
        const userRef = collection(db, "Users", userID, "Regions");
        const regionSnapshots = await getDocs(userRef);

        const vpnData: VPNData[] = [];

        for (const regionDoc of regionSnapshots.docs) {
            const regionID = regionDoc.id;
            const instancesRef = collection(db, "Users", userID, "Regions", regionID, "Instances");
            const instanceSnapshots = await getDocs(instancesRef);

            instanceSnapshots.forEach((instanceDoc) => {
                const { ipv4, status } = instanceDoc.data();
                if (ipv4 && status && status.toLowerCase() !== "terminated") {
                    vpnData.push({
                        userID: userID,
                        email: email,
                        region: regionID,
                        instanceID: instanceDoc.id,
                        ipv4: ipv4,
                        status: status,
                    });
                }
            });
        }

        return vpnData;

    } catch (error) {
        console.warn("Error fetching VPNs:", error);
        return [];
    }
};

const getAdminVPNs = async (user: User): Promise<VPNData[]> => {
    try {        
        if (await getUserRole(user) !== "admin") {
            console.warn("Not an admin. Cannot fetch VPNs for admin.");
            return [];
        }

        const db = getFirestore();
        const usersSnapshot = await getDocs(collection(db, "Users"));

        let vpnData: VPNData[] = [];

        // for (const userDoc of usersSnapshot.docs) {
        //     vpnData.push(...await getVPNs(userDoc.id, userDoc.data().email))
        // }

        // Same thing but this parallelizes to increase efficiency
        vpnData = (await Promise.all(
            usersSnapshot.docs.map(userDoc => getVPNs(userDoc.id, userDoc.data().email))
        )).flat();

        return vpnData;

    } catch (error) {
        console.warn("Error fetching VPNs for admin:", error);
        return [];
    }
}