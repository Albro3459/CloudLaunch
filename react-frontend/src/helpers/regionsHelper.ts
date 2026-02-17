import { collection, getDocs, getFirestore } from "firebase/firestore";

export const aws_regions = [
{ name: "India (Mumbai)", value: "ap-south-1" },
{ name: "France", value: "eu-west-3" },
{ name: "United Kingdom", value: "eu-west-2" },
{ name: "Ireland", value: "eu-west-1" },
{ name: "Japan (Osaka)", value: "ap-northeast-3" },
{ name: "South Korea", value: "ap-northeast-2" },
{ name: "Japan (Tokyo)", value: "ap-northeast-1" },
{ name: "Canada", value: "ca-central-1" },
{ name: "Brazil", value: "sa-east-1" },
{ name: "Singapore", value: "ap-southeast-1" },
{ name: "Australia (Sydney)", value: "ap-southeast-2" },
{ name: "Germany", value: "eu-central-1" },
{ name: "Virginia", value: "us-east-1" },
{ name: "Ohio", value: "us-east-2" },
{ name: "California", value: "us-west-1" },
{ name: "Oregon", value: "us-west-2" },
// { name: "Hong Kong", value: "ap-east-1" },               // Doesn't support t2.micro
// { name: "Mexico", value: "mx-central-1" },               // Doesn't support t2.micro
// { name: "South Africa", value: "af-south-1" },           // Doesn't support t2.micro
// { name: "Sweden", value: "eu-north-1" },                 // Doesn't support t2.micro
// { name: "United Arab Emirates", value: "me-central-1" }, // Doesn't support t2.micro
];


// export const live_regions = [
//     { name: "California", value: "us-west-1" },
//     // { name: "Brazil", value: "sa-east-1" },
//     { name: "Japan (Tokyo)", value: "ap-northeast-1" },
//     // { name: "Korea", value: "ap-northeast-2" },
//     // { name: "United Kingdom", value: "eu-west-2" },

// ];

export type Region = {
    name: string;
    value: string;
}

export const getLiveRegions = async (): Promise<Region[] | null> => {
    try {
        const db = getFirestore();
        const querySnapshot = await getDocs(collection(db, "Live-Regions"));
        const regions: Region[] = [];
        querySnapshot.forEach((doc) => {
          regions.push({ name: doc.data().name, value: doc.id });
        });
        return regions.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        
    } catch (error: any) {
        if (error.code === "permission-denied") {
            console.warn("Permission denied when trying to read Live Regions. Probably not an admin.");
        } else {
            console.error("Unexpected error getting Live Regions:", error);
        }
        return null;
    }
};

export const getRegionName = (region: string | null) => {
    if (!region) return null;
    return aws_regions.find(r => r.value === region)?.name || null;
};