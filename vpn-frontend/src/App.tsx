import React from "react";
import { HashRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Success from "./pages/Success";
import About from "./pages/About";
import CreateUser from "./pages/CreateUser";
import CreateUserSuccess from "./pages/CreateUserSuccess";

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/home" element={<Home />} />
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/success" element={<Success />} />
        <Route path="/about" element={<About />} />
        <Route path="/createUser" element={<CreateUser />} />
        <Route path="/createUserSuccess" element={<CreateUserSuccess />} />
      </Routes>
    </Router>
  );
};

export default App;