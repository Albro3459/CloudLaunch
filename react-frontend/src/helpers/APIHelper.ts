import { AMI_WAITER_URL, DEPLOY_URL, TERRAFORM_URL } from "../Secrets/API_URLs";

export const VPNdeployHelper = async (region: string, email: string, token: string, instance_name = "VPN") => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "region": region,
            "email" : email,
            "instance_name": instance_name
        });

        const requestOptions: RequestInit = {
            method: "POST",
            headers: myHeaders,
            body: raw,
            redirect: "follow"
        };

        const response = await fetch(DEPLOY_URL, requestOptions);
        const result = await response.json();

        if (!response.ok) {
            return {
                success: false,
                error: result?.error || `Error ${response.status}`
            };
        }

        return {
            success: true,
            data: result
        };
        
    } catch (error) {
        console.error("Lambda API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown Lambda API Error"
        };
    }
};

export enum TERRAFORM_ENUM {
    TERRAFORM,
    CLEAN
}

export const terraformHelper = async (region: string, token: string, cleanUp:TERRAFORM_ENUM=TERRAFORM_ENUM.TERRAFORM) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        // CleanUp is if the lambda script should delete the AMIs and Snapshots in that region
        const key = cleanUp === TERRAFORM_ENUM.CLEAN ? "region_to_clean" : "target_region";
        const raw = JSON.stringify({
            [key]: region,
            "waiter_url": AMI_WAITER_URL
        });

        const requestOptions: RequestInit = {
            method: "POST",
            headers: myHeaders,
            body: raw,
            redirect: "follow"
        };

        const response = await fetch(TERRAFORM_URL, requestOptions);
        const result = await response.json();

        if (!response.ok) {
            return {
                success: false,
                error: result?.error || `Error ${response.status}`
            };
        }

        return {
            success: true,
            data: result
        };
        
    } catch (error) {
        console.error("Terraform API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown Terraform API Error"
        };
    }
};