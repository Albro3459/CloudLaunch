import { collection, getDocs, getFirestore } from "firebase/firestore";
import { useAWSRegionsStore } from "../stores/awsRegionsStore";

// Fallback for AWSRegionsStore
export const aws_regions: Region[] = [
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
    
    // These don't support t2.micro:
    { name: "Hong Kong", value: "ap-east-1", invalid: true },
    { name: "Mexico", value: "mx-central-1", invalid: true },
    { name: "South Africa", value: "af-south-1", invalid: true },
    { name: "Sweden", value: "eu-north-1", invalid: true },
    { name: "United Arab Emirates", value: "me-central-1", invalid: true },
].toSorted((a, b) => a.name.localeCompare(b.name));

export type Region = {
    name: string;
    value: string;
    invalid?: boolean;
}

export const getLiveRegions = async (): Promise<Region[] | null> => {
    try {
        const db = getFirestore();
        const querySnapshot = await getDocs(collection(db, "Live-Regions"));
        const regions: Region[] = [];

        const _checkAWSRegions = useAWSRegionsStore.getState().AWSRegions;
        const validAWSRegions = (_checkAWSRegions?.length ? _checkAWSRegions : aws_regions).filter(x => !x.invalid);

        querySnapshot.forEach((doc) => {
          regions.push({ name: doc.data().name, value: doc.id, invalid: !validAWSRegions.find(x => x.value === doc.id) });
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

export const getRegionName = (region: string | null): string => {
    if (!region) return '';
    return aws_regions.find(r => r.value === region)?.name || region;
};