import { initializeApp } from "firebase/app";
import { getAuth, signInWithEmailAndPassword ,signOut, onAuthStateChanged, getIdToken } from "firebase/auth";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

import { apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId } from "./Secrets/firebaseKeys";

const firebaseConfig = {
  apiKey: apiKey,
  authDomain: authDomain,
  projectId: projectId,
  storageBucket: storageBucket,
  messagingSenderId: messagingSenderId,
  appId: appId
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { auth, signInWithEmailAndPassword, signOut, onAuthStateChanged, getIdToken };
