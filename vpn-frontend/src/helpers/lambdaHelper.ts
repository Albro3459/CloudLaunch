export const lambdaHelper = async (region: string, instance_name: string, token: string) => {
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
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const result = await response.json();
        return result;
        
    } catch (error) {
        console.error("Lambda API Error:", error);
        return null;
    }
};
