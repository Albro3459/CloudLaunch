import { User } from "firebase/auth";
import { doc, getDoc, getFirestore } from "firebase/firestore";

export const lambdaHelper = async (region: string, token: string, instance_name = "VPN") => {
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

        const response = await fetch("https://gnzna5q2py67vtegyh2vjijnse0etwja.lambda-url.us-west-1.on.aws/", requestOptions);
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
            error: error instanceof Error ? error.message : "Unknown error"
        };
    }
};

export const createUser = async (username: string, password: string, token: string) => {
    try {
        const myHeaders = new Headers();
        myHeaders.append("Authorization", `Bearer ${token}`);
        myHeaders.append("Content-Type", "application/json");

        const email = `${username}@example.com`;
        const raw = JSON.stringify({
            "email": email,
            "password": password
        });

        const requestOptions: RequestInit = {
            method: "POST",
            headers: myHeaders,
            body: raw,
            redirect: "follow"
        };

        const response = await fetch("https://snsajcmvbq2alq5zplolwje72i0aoqnj.lambda-url.us-west-1.on.aws/", requestOptions);
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
        console.error("Create User API Error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
        };
    }    
};

export const getUserRole = async (user: User): Promise<string | null> => {
    try {
      const uid = user.uid;
    //   console.log(uid);
      const db = getFirestore();
      const docRef = doc(db, "Roles", uid);
      const docSnap = await getDoc(docRef);
  
      if (docSnap.exists()) {
        const data = docSnap.data();
        // console.log(data.role);
        return data.role || null;
      }
  
      console.warn(`Role document does not exist for user: ${uid}`);
      return null;
  
    } catch (error: any) {
      if (error.code === "permission-denied") {
        console.warn("Permission denied when trying to read role. Probably not an admin.");
      } else {
        console.error("Unexpected error getting user role:", error);
      }
  
      return null;
    }
};
  