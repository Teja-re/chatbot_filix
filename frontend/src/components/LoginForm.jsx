import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  InputAdornment,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import RestaurantMenuIcon from "@mui/icons-material/RestaurantMenu";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import { loginUser, registerUser } from "../api";

export default function LoginForm({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await loginUser(email, password)
          : await registerUser(name, email, password);
      onAuth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDemoLogin() {
    setError("");
    setLoading(true);
    try {
      const data = await loginUser("demo@dinebot.com", "demo1234");
      onAuth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        background: "linear-gradient(145deg, #FAF8F5 0%, #EFE9DD 100%)",
      }}
    >
      <Paper
        elevation={0}
        sx={{
          width: "100%",
          maxWidth: 430,
          p: { xs: 3, sm: 4 },
          borderRadius: 3,
          border: "1px solid #E8E1D5",
          boxShadow: "0 14px 40px rgba(27, 67, 50, 0.08)",
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center" mb={1}>
          <Box
            sx={{
              width: 42,
              height: 42,
              borderRadius: 2.5,
              bgcolor: "primary.main",
              color: "#fff",
              display: "grid",
              placeItems: "center",
            }}
          >
            <RestaurantMenuIcon />
          </Box>
          <Box>
            <Typography variant="h5" color="primary.main">
              DineBot
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Smart restaurant discovery &amp; table concierge
            </Typography>
          </Box>
        </Stack>

        <Tabs
          value={mode}
          onChange={(_, val) => {
            setMode(val);
            setError("");
          }}
          variant="fullWidth"
          sx={{ mb: 2.5, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Sign In" value="login" />
          <Tab label="Create Account" value="register" />
        </Tabs>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Stack component="form" spacing={2} onSubmit={handleSubmit}>
          {mode === "register" && (
            <TextField
              label="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              inputProps={{ minLength: 2 }}
              fullWidth
            />
          )}

          <TextField
            label="Email Address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            fullWidth
          />

          <TextField
            label="Password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            inputProps={{ minLength: 6 }}
            fullWidth
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                    aria-label="toggle password visibility"
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <Button
            type="submit"
            variant="contained"
            color="secondary"
            size="large"
            disabled={loading}
            fullWidth
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign In & Start Chat" : "Create Account"}
          </Button>
        </Stack>

        <Divider sx={{ my: 2.5 }}>
          <Typography variant="caption" color="text.secondary">
            QUICK ACCESS
          </Typography>
        </Divider>

        <Button
          variant="outlined"
          color="primary"
          size="large"
          onClick={handleDemoLogin}
          disabled={loading}
          fullWidth
        >
          Demo Login (demo@dinebot.com)
        </Button>
      </Paper>
    </Box>
  );
}
