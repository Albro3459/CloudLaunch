import React from "react";

export default function StreamTrackerPrivacyPolicy() {
    return (
        <div style={styles.body}>
            <strong>Privacy Policy</strong>
            <p>
                This privacy policy applies to the StreamTracker app (hereby referred to as "Application") for mobile devices that was created by Alexander Brodsky (hereby referred to as "Service Provider") as a Free service. This service is intended for use "AS IS".
            </p>
            <br />
            <strong>Information Collection and Use</strong>
            <p>
                The Application collects information when you download and use it. This information may include information such as:
            </p>
            <ul>
                <li style={{ paddingLeft: "2em" }}>The user's email.</li>
                <li style={{ paddingLeft: "2em" }}>The user's name.</li>
                <li style={{ paddingLeft: "2em" }}>The user's favorited genres.</li>
                <li style={{ paddingLeft: "2em" }}>The user's favorited streaming services.</li>
            </ul>
            <br />
            <p>
                The Application does not gather precise information about the location of your mobile device.
            </p>
            <br />
            <p>
                For a better experience, while using the Application, the Service Provider may require you to provide us with certain personally identifiable information, including but not limited to Email, UserID, First Name, Last Name. The information that the Service Provider request will be retained by them and used as described in this privacy policy.
            </p>
            <br />
            <strong>Third Party Access</strong>
            <p>
                Only aggregated, anonymized data is periodically transmitted to external services to aid the Service Provider in improving the Application and their service. The Service Provider may share your information with third parties in the ways that are described in this privacy statement.
            </p>
            <br />
            <p>
                Please note that the Application utilizes third-party services that have their own Privacy Policy about handling data. Below are the links to the Privacy Policy of the third-party service providers used by the Application:
            </p>
            <ul>
                <li>
                    <a href="https://expo.dev/privacy" style={{ textDecoration: "underline" }} target="_blank" rel="noopener noreferrer">
                        Expo
                    </a>
                </li>
                <li>
                    <a href="https://firebase.google.com/support/privacy" style={{ textDecoration: "underline" }} target="_blank" rel="noopener noreferrer">
                        Firebase Authentication
                    </a>
                </li>
            </ul>
            <br />
            <p>The Service Provider may disclose User Provided and Automatically Collected Information:</p>
            <ul>
                <li>as required by law, such as to comply with a subpoena, or similar legal process;</li>
                <li>when they believe in good faith that disclosure is necessary to protect their rights, protect your safety or the safety of others, investigate fraud, or respond to a government request;</li>
                <li>with their trusted services providers who work on their behalf, do not have an independent use of the information we disclose to them, and have agreed to adhere to the rules set forth in this privacy statement.</li>
            </ul>
            <br />
            <strong>Opt-Out Rights</strong>
            <p>
                You can stop all collection of information by the Application easily by uninstalling it. You may use the standard uninstall processes as may be available as part of your mobile device or via the mobile application marketplace or network.
            </p>
            <br />
            <strong>Data Retention Policy</strong>
            <p>
                The Service Provider will retain User Provided data for as long as you use the Application and for a reasonable time thereafter. If you&apos;d like them to delete User Provided Data that you have provided via the Application, please contact them at brodsky.alex22@gmail.com and they will respond in a reasonable time.
            </p>
            <br />
            <strong>Children</strong>
            <p>
                The Service Provider does not use the Application to knowingly solicit data from or market to children under the age of 13.
            </p>
            <br />
            <p>
                The Application does not address anyone under the age of 13. The Service Provider does not knowingly collect personally identifiable information from children under 13 years of age. In the case the Service Provider discover that a child under 13 has provided personal information, the Service Provider will immediately delete this from their servers. If you are a parent or guardian and you are aware that your child has provided us with personal information, please contact the Service Provider (brodsky.alex22@gmail.com) so that they will be able to take the necessary actions.
            </p>
            <br />
            <strong>Security</strong>
            <p>
                The Service Provider is concerned about safeguarding the confidentiality of your information. The Service Provider provides physical, electronic, and procedural safeguards to protect information the Service Provider processes and maintains.
            </p>
            <br />
            <strong>Changes</strong>
            <p>
                This Privacy Policy may be updated from time to time for any reason. The Service Provider will notify you of any changes to the Privacy Policy by updating this page with the new Privacy Policy. You are advised to consult this Privacy Policy regularly for any changes, as continued use is deemed approval of all changes.
            </p>
            <br />
            <p>This privacy policy is effective as of 2025-07-20</p>
            <br />
            <strong>Your Consent</strong>
            <p>
                By using the Application, you are consenting to the processing of your information as set forth in this Privacy Policy now and as amended by us.
            </p>
            <br />
            <strong>Contact Us</strong>
            <p>
                If you have any questions regarding privacy while using the Application, or have questions about the practices, please contact the Service Provider via email at{" "}
                <a href="mailto:brodsky.alex22@gmail.com" style={{ textDecoration: "underline" }}>brodsky.alex22@gmail.com</a>.
            </p>
            <hr style={styles.hr} />
        </div>
    );
}

const styles = {
    body: {
        fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif",
        padding: "1em",
        maxWidth: "800px",
        margin: "0 auto",
    } as React.CSSProperties,
    hr: {
        margin: "2em 0",
    } as React.CSSProperties,
};