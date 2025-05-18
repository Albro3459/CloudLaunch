import { User } from "firebase/auth";
import { getFirestore, collection, getDocs } from "firebase/firestore";

import { getUserRole } from "./usersHelper";

export type VPNData = {
    userID: string;
    email: string | null;
    region: string | null;
    instanceID: string;
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

// const getAdminVPNs = async (user: User): Promise<VPNData[]> => {
//     try {        
//         if (await getUserRole(user) !== "admin") {
//             console.warn("Not an admin. Cannot fetch VPNs for admin.");
//             return [];
//         }

//         const db = getFirestore();
//         const usersSnapshot = await getDocs(collection(db, "Users"));

//         let vpnData: VPNData[] = [];

//         // for (const userDoc of usersSnapshot.docs) {
//         //     vpnData.push(...await getVPNs(userDoc.id, userDoc.data().email))
//         // }

//         // Same thing but this parallelizes to increase efficiency
//         vpnData = (await Promise.all(
//             usersSnapshot.docs.map(userDoc => getVPNs(userDoc.id, userDoc.data().email))
//         )).flat();

//         return vpnData;

//     } catch (error) {
//         console.warn("Error fetching VPNs for admin:", error);
//         return [];
//     }
// }

const getAdminVPNs = async (user: User): Promise<VPNData[]> => {
    const vpnTestData: VPNData[] = [
        {
            userID: "user-001",
            email: "alice@example.com",
            region: "us-east-1",
            instanceID: "i-0a1b2c3d4e5f67890",
            ipv4: "192.168.0.1",
            status: "Running"
        },
        {
            userID: "user-002",
            email: "bob@example.net",
            region: "eu-west-1",
            instanceID: "i-1234567890abcdef0",
            ipv4: "10.0.0.5",
            status: "Running"
        },
        {
            userID: "user-003",
            email: "carla@domain.com",
            region: "ap-southeast-2",
            instanceID: "i-abcdef1234567890a",
            ipv4: "172.31.255.10",
            status: "Running"
        },
        {
            userID: "user-004",
            email: "daniel@workmail.com",
            region: "ca-central-1",
            instanceID: "i-fedcba0987654321b",
            ipv4: "192.0.2.44",
            status: "Running"
        },
        {
            userID: "user-005",
            email: "eve@sample.org",
            region: "us-west-2",
            instanceID: "i-09f8e7d6c5b4a3210",
            ipv4: "198.51.100.22",
            status: "Running"
        }
    ];
    return vpnTestData;
}