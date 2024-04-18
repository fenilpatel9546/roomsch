"use strict";

// import firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyDfjkBLjxyHzW1vu-OpUfeeEgOuY1yVJUw",
  authDomain: "roomsch.firebaseapp.com",
  projectId: "roomsch",
  storageBucket: "roomsch.appspot.com",
  messagingSenderId: "892498618304",
  appId: "1:892498618304:web:a70f17d635c947ff45ca25",
};

window.addEventListener("load", function () {
  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);
  updateUI(document.cookie);
  console.log("hello world load");
  // signup of a new user to firebase

  document.getElementById("sign-up").addEventListener("click", function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    createUserWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        // we have a created user
        const user = userCredential.user;

        user.getIdToken().then((token) => {
          document.cookie = "token=" + token + "; path=/; SameSite=Strict";
          console.log(token);
          window.location = "/";
        });
      })
      // get the id token for the user who just logged in and force a redirect to /
      .catch((error) => {
        // issue with signup that we will drop to console
        console.log(error.code + error.message);
      });
  });

  // login of a user to firebase
  document.getElementById("login").addEventListener("click", function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    signInWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        const user = userCredential.user;
        console.log("logged in");

        user.getIdToken().then((token) => {
          document.cookie = "token=" + token + "; path=/; SameSite=Strict";
          console.log(token);
          console.log(document.cookie);
          window.location = "/";
        });
      })
      .catch((error) => {});
  });
  console.log(document.cookie);

  document.getElementById("sign-out").addEventListener("click", function () {
    signOut(auth).then((output) => {
      document.cookie = "token=;path=/; SameSite=Strict";
      window.location = "/";
      console.log(output);
    });
  });
});

function updateUI(cookie) {
  var token = parseCookieToken(cookie);
  console.log(token.length);
  if (token.length > 0) {
    document.getElementById("login-box").hidden = true;
  } else {
    document.getElementById("login-box").hidden = false;
  }
}

function parseCookieToken(cookie) {
  var strings = cookie.split(";");

  for (let i = 0; i < strings.length; i++) {
    var temp = strings[i].trim().split("=");
    if (temp[0] === "token") return temp[1];
  }
  return "";
}
