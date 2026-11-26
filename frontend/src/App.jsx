import { useState } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import theme from "./theme";
import LoginForm from "./components/LoginForm";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("dinebot_token") || "");
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("dinebot_user");
    return raw ? JSON.parse(raw) : null;
  });

  function handleAuth(authData) {
    localStorage.setItem("dinebot_token", authData.access_token);
    localStorage.setItem("dinebot_user", JSON.stringify(authData.user));
    setToken(authData.access_token);
    setUser(authData.user);
  }

  function handleLogout() {
    localStorage.removeItem("dinebot_token");
    localStorage.removeItem("dinebot_user");
    setToken("");
    setUser(null);
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {!token || !user ? (
        <LoginForm onAuth={handleAuth} />
      ) : (
        <ChatWindow user={user} token={token} onLogout={handleLogout} />
      )}
    </ThemeProvider>
  );
}
