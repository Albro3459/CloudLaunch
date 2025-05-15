import { User } from "firebase/auth";
import { getFirestore, collection, getDocs } from "firebase/firestore";

import { getUserRole } from "./usersHelper";
import { getRegionName } from "./regionsHelper";
import { auth } from "../firebase";

export type VPNData = {
    email: string | null;
    region: string | null;
    ipv4: string;
    status: string;
}

export const getUsersVPNs = async (user: User): Promise<VPNData[]> => {

    if (await getUserRole(user) === "admin") {
        return await getAdminVPNs(user);
    }

    return await getVPNs(user.uid, user.email);
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
            const regionId = regionDoc.id;
            const instancesRef = collection(db, "Users", userID, "Regions", regionId, "Instances");
            const instanceSnapshots = await getDocs(instancesRef);

            instanceSnapshots.forEach((instanceDoc) => {
                const { ipv4, status } = instanceDoc.data();
                if (ipv4 && status && status.toLowerCase() !== "terminated") {
                    vpnData.push({
                        email: email,
                        region: getRegionName(regionId),
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