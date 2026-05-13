import { DEPLOY_URL, SECURE_GET_URL } from "../Secrets/API_URLs";

export const SecureGetRegionsHelper = async (token: string) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "requested_keys": ["oci_region", "oci_region_name"]
        });

        const requestOptions: RequestInit = {
            method: "POST",
            headers: myHeaders,
            body: raw,
            redirect: "follow"
        };

        const response = await fetch(SECURE_GET_URL, requestOptions);
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
        console.error("Secure Get Regions API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown Secure Get Regions API Error"
        };
    }
};

export const SecureGetKeysHelper = async (requested_keys: string[], token: string) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "requested_keys": requested_keys
        });

        const requestOptions: RequestInit = {
            method: "POST",
            headers: myHeaders,
            body: raw,
            redirect: "follow"
        };

        const response = await fetch(SECURE_GET_URL, requestOptions);
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
        console.error("Secure Get Keys API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown Secure Get Keys API Error"
        };
    }
};


export type Targets = {
    [userID: string]: {
      [region: string]: string[]; // Array of instance IDs
    };
};

export enum ACTION {
    DEPLOY = "deploy",
    TERMINATE = "terminate"
}

export const VPNdeployHelper = async (action: ACTION, targets: Targets | null, email: string | null, target_region: string | null, token: string) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
            "action": action,
            "targets": targets,
            "email" : email,
            "target_region": target_region,
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
        console.error("Deploy API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown Deploy API Error"
        };
    }
};
