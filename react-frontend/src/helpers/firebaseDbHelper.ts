import { User } from "firebase/auth";
import { getFirestore, collection, getDocs } from "firebase/firestore";

import { getUserRole } from "./usersHelper";
import { getRegionName } from "./regionsHelper";

export type VPNData = {
    region: string | null;
    ipv4: string;
    status: string;
}

export const getUsersVPNs = async (user: User): Promise<VPNData[]> => {
    try {
        if (await getUserRole(user) === "admin") {
            return await getAdminVPNs();
        }

        const db = getFirestore();
        const userRef = collection(db, "Users", user.uid, "Regions");
        const regionSnapshots = await getDocs(userRef);

        const vpnData: VPNData[] = [];

        for (const regionDoc of regionSnapshots.docs) {
            const regionId = regionDoc.id;
            const instancesRef = collection(db, "Users", user.uid, "Regions", regionId, "Instances");
            const instanceSnapshots = await getDocs(instancesRef);

            instanceSnapshots.forEach((instanceDoc) => {
                const { ipv4, status } = instanceDoc.data();
                vpnData.push({
                    region: getRegionName(regionId),
                    ipv4: ipv4,
                    status: status,
                });
            });
        }

        return vpnData;

    } catch (error) {
        console.warn("Error fetching VPNs:", error);
        return [];
    }
};

const getAdminVPNs = async (): Promise<VPNData[]> => {
    return [
            {
                region: getRegionName("us-west-1")!,
                ipv4: "127.0.0.1",
                status: "Running",
            },
            {
                region: "us-west-1",
                ipv4: "127.0.0.1",
                status: "Running",
            },
            {
                region: getRegionName("us-east-2")!,
                ipv4: "127.0.0.1",
                status: "Running",
            }
        ];
}