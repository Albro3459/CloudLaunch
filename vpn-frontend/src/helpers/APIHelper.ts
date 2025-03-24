import { AMI_WAITER_URL, DEPLOY_URL, TERRAFORM_URL } from "../Secrets/API_URLs";

export const VPNdeployHelper = async (region: string, token: string, instance_name = "VPN") => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "region": region,
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

export const terraformHelper = async (region: string, token: string) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "target_region": region,
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