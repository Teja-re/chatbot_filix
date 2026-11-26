import { useEffect, useRef, useState } from "react";
import {
  Alert,
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Fade,
  IconButton,
  Paper,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EventNoteIcon from "@mui/icons-material/EventNote";
import LogoutIcon from "@mui/icons-material/Logout";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import {
  cancelBooking,
  enrichRestaurantMenu,
  getMyBookings,
  getSession,
  sendChatAction,
} from "../api";
import BookingForm from "./BookingForm";
import BookingsDrawer from "./BookingsDrawer";
import MenuNutrientList from "./MenuNutrientList";
import NearbyRestaurants from "./NearbyRestaurants";

export default function ChatWindow({ user, token, onLogout }) {
  const [session, setSession] = useState(null);
  const [coords, setCoords] = useState(null);
  const [chatText, setChatText] = useState("");
  const [bookings, setBookings] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshingMenu, setRefreshingMenu] = useState(false);

  const bottomRef = useRef(null);

  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const [sessData, myBookings] = await Promise.all([
          getSession(token, null),
          getMyBookings(token).catch(() => []),
        ]);
        if (active) {
          setSession(sessData);
          setBookings(myBookings);
        }
      } catch (err) {
        if (err.status === 401) {
          onLogout();
          return;
        }
        if (active) setError(err.message);
      }
    }

    init();

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const nextCoords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          if (!active) return;
          setCoords(nextCoords);
          try {
            const refreshed = await getSession(token, nextCoords);
            if (active) setSession(refreshed);
          } catch {
            // Keep initial session if location refresh fails
          }
        },
        () => {},
        { timeout: 4000 }
      );
    }

    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages?.length, session?.state, busy]);

  async function dispatch(payload) {
    setError("");
    setBusy(true);
    try {
      const updated = await sendChatAction(token, {
        ...payload,
        lat: coords?.lat ?? null,
        lon: coords?.lon ?? null,
      });
      setSession(updated);
      if (updated.latest_booking) {
        const latestList = await getMyBookings(token).catch(() => null);
        if (latestList) setBookings(latestList);
      }
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleOpenDrawer() {
    setDrawerOpen(true);
    try {
      const list = await getMyBookings(token);
      setBookings(list);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCancelBooking(bookingId) {
    try {
      const updated = await cancelBooking(token, bookingId);
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? updated : b)));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRefreshNutrition() {
    if (!session?.selected_restaurant) return;
    setError("");
    setRefreshingMenu(true);
    try {
      const updatedItems = await enrichRestaurantMenu(token, session.selected_restaurant.id);
      setSession((prev) => (prev ? { ...prev, menu_items: updatedItems } : prev));
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshingMenu(false);
    }
  }

  function handleSendText(e) {
    e.preventDefault();
    if (!chatText.trim() || busy) return;
    const text = chatText.trim();
    setChatText("");
    dispatch({ action: "message", text });
  }

  if (!session) {
    return (
      <Box sx={{ minHeight: "100dvh", display: "grid", placeItems: "center", p: 2 }}>
        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <Stack alignItems="center" spacing={1.5}>
            <CircularProgress color="primary" />
            <Typography variant="body2" color="text.secondary">
              Starting DineBot chat...
            </Typography>
          </Stack>
        )}
      </Box>
    );
  }

  const confirmedCount = bookings.filter((b) => b.status === "CONFIRMED").length;
  const llmOnline = session.llm_provider === "openrouter" || session.llm_provider === "ollama";
  const llmLabel =
    session.llm_provider === "openrouter"
      ? "OpenRouter AI online"
      : session.llm_provider === "ollama"
        ? "Ollama LLM online"
        : "Smart fallback mode";

  return (
    <Box
      sx={{
        height: "100dvh",
        display: "flex",
        flexDirection: "column",
        bgcolor: "#E9E3D7",
      }}
    >
      <Container
        maxWidth="md"
        disableGutters
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          bgcolor: "#F3EFE6",
          boxShadow: { md: "0 12px 36px rgba(0,0,0,0.08)" },
        }}
      >
        {/* WhatsApp-style top bar */}
        <AppBar position="static" color="primary" elevation={0}>
          <Toolbar sx={{ gap: 1.5, py: 0.75 }}>
            <Avatar sx={{ bgcolor: "secondary.main", width: 40, height: 40 }}>
              <SmartToyIcon />
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={700} noWrap>
                DineBot Concierge
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: llmOnline ? "#4ADE80" : "#FBBF24",
                  }}
                />
                <Typography variant="caption" sx={{ opacity: 0.9 }} noWrap>
                  {llmLabel} • {user.name}
                </Typography>
              </Stack>
            </Box>

            <IconButton color="inherit" onClick={handleOpenDrawer} aria-label="my bookings">
              <Badge badgeContent={confirmedCount} color="secondary">
                <EventNoteIcon />
              </Badge>
            </IconButton>

            <IconButton color="inherit" onClick={onLogout} aria-label="logout">
              <LogoutIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        {error && (
          <Alert severity="error" onClose={() => setError("")} sx={{ m: 1.5, mb: 0 }}>
            {error}
          </Alert>
        )}

        {/* Scrollable WhatsApp conversation stream + interactive cards */}
        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            px: { xs: 1.5, sm: 2.5 },
            py: 2,
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
          }}
        >
          {session.messages.map((m, idx) => {
            const isBot = m.sender === "bot";
            return (
              <Box
                key={idx}
                sx={{
                  display: "flex",
                  justifyContent: isBot ? "flex-start" : "flex-end",
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    maxWidth: { xs: "86%", sm: "72%" },
                    px: 1.75,
                    py: 1.1,
                    borderRadius: isBot ? "4px 14px 14px 14px" : "14px 4px 14px 14px",
                    bgcolor: isBot ? "#FFFFFF" : "#DCEEE3",
                    border: "1px solid #E5DFD3",
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                    {m.text}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", textAlign: "right", fontSize: "0.68rem", mt: 0.3 }}
                  >
                    {m.timestamp}
                  </Typography>
                </Paper>
              </Box>
            );
          })}

          {busy && (
            <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
              <Paper
                elevation={0}
                sx={{
                  px: 1.75,
                  py: 1,
                  borderRadius: "4px 14px 14px 14px",
                  bgcolor: "#FFFFFF",
                  border: "1px solid #E5DFD3",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  DineBot is thinking...
                </Typography>
              </Paper>
            </Box>
          )}

          {/* Embedded interactive cards driven by backend state */}
          <Fade in key={session.state}>
            <Box sx={{ mt: 0.5 }}>
              {session.state === "NEARBY_LIST" && (
                <NearbyRestaurants
                  restaurants={session.nearby_restaurants}
                  recommendations={session.recommendations}
                  healthGoal={session.health_goal}
                  busy={busy}
                  onSelect={(id) => dispatch({ action: "select_restaurant", restaurant_id: id })}
                  onRecommendHealth={(goal) => dispatch({ action: "recommend_healthy", goal })}
                  onClearHealth={() => dispatch({ action: "recommend_healthy", goal: "clear" })}
                  onDecline={() => dispatch({ action: "decline_booking" })}
                />
              )}

              {session.state === "VIEWING_MENU" && session.selected_restaurant && (
                <MenuNutrientList
                  restaurant={session.selected_restaurant}
                  items={session.menu_items}
                  likedIds={session.liked_item_ids}
                  busy={busy}
                  refreshing={refreshingMenu}
                  onToggleLike={(itemId) => dispatch({ action: "toggle_like_item", item_id: itemId })}
                  onRefreshNutrition={handleRefreshNutrition}
                  onAskCombo={() =>
                    dispatch({
                      action: "message",
                      text: "Suggest a healthy meal combo under 600 kcal with high protein from this menu",
                    })
                  }
                  onStartBooking={() => dispatch({ action: "start_booking" })}
                  onBack={() => dispatch({ action: "go_back" })}
                  onDecline={() => dispatch({ action: "decline_booking" })}
                />
              )}

              {session.state === "BOOKING_FORM" && session.selected_restaurant && (
                <BookingForm
                  token={token}
                  restaurant={session.selected_restaurant}
                  initialSlots={session.slots}
                  likedCount={session.liked_item_ids.length}
                  bookingDraft={session.booking_draft}
                  busy={busy}
                  onConfirm={(values) => dispatch({ action: "confirm_booking", ...values })}
                  onBackToMenu={() => dispatch({ action: "go_back" })}
                  onBackToList={() => dispatch({ action: "show_nearby" })}
                  onDecline={() => dispatch({ action: "decline_booking" })}
                />
              )}

              {session.state === "CONFIRMED" && (
                <Paper
                  elevation={0}
                  sx={{ p: 2.5, borderRadius: 3, border: "1px solid #CBE4D4", bgcolor: "#F4FBF6" }}
                >
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <CheckCircleIcon color="success" />
                    <Typography variant="subtitle1" fontWeight={700}>
                      Table Reserved!
                    </Typography>
                  </Stack>

                  {session.latest_booking && (
                    <Typography variant="body2" mb={2}>
                      <strong>{session.latest_booking.restaurant_name}</strong> •{" "}
                      {session.latest_booking.booking_date} at {session.latest_booking.time_slot} •{" "}
                      {session.latest_booking.party_size} guests • Code:{" "}
                      <Chip
                        size="small"
                        color="success"
                        label={session.latest_booking.booking_code}
                      />
                    </Typography>
                  )}

                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={<RestaurantIcon />}
                      onClick={() => dispatch({ action: "show_nearby" })}
                    >
                      Browse Other Restaurants
                    </Button>
                    <Button variant="outlined" onClick={handleOpenDrawer}>
                      View My Bookings
                    </Button>
                  </Stack>
                </Paper>
              )}

              {session.state === "ENDED" && (
                <Paper
                  elevation={0}
                  sx={{ p: 2.5, borderRadius: 3, border: "1px solid #E8E1D5", bgcolor: "#FFFFFF" }}
                >
                  <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                    No Table Booked Today
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={2}>
                    Whenever you are ready to dine out, tap below or send a message.
                  </Typography>
                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={() => dispatch({ action: "restart" })}
                  >
                    Browse Nearby Restaurants
                  </Button>
                </Paper>
              )}
            </Box>
          </Fade>

          <div ref={bottomRef} />
        </Box>

        {/* Bottom sticky WhatsApp composer + quick chips */}
        <Box
          sx={{
            p: 1.5,
            bgcolor: "#FFFFFF",
            borderTop: "1px solid #E5DFD3",
          }}
        >
          <Stack direction="row" spacing={0.75} mb={1} sx={{ overflowX: "auto", pb: 0.25 }}>
            {session.quick_actions.map((label) => (
              <Chip
                key={label}
                label={label}
                size="small"
                clickable
                disabled={busy}
                variant="outlined"
                onClick={() => {
                  const q = label.toLowerCase();
                  if (q.includes("healthy")) {
                    dispatch({ action: "recommend_healthy", goal: "Balanced" });
                  } else if (q.includes("refresh") || q.includes("browse")) {
                    dispatch({ action: "show_nearby" });
                  } else if (q.includes("back to menu")) {
                    dispatch({ action: "go_back" });
                  } else if (q.includes("back to restaurants")) {
                    dispatch({ action: "show_nearby" });
                  } else if (q.includes("proceed")) {
                    dispatch({ action: "start_booking" });
                  } else {
                    dispatch({ action: "decline_booking" });
                  }
                }}
              />
            ))}
          </Stack>

          <Stack component="form" direction="row" spacing={1} onSubmit={handleSendText}>
            <TextField
              size="small"
              fullWidth
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              placeholder="Message DineBot (e.g. 'high protein dishes', 'back', 'book for 2 at 7pm')..."
              disabled={busy}
              sx={{ "& .MuiOutlinedInput-root": { borderRadius: 6, bgcolor: "#FAF8F5" } }}
            />
            <IconButton
              type="submit"
              color="primary"
              disabled={busy || !chatText.trim()}
              sx={{
                bgcolor: "primary.main",
                color: "#fff",
                "&:hover": { bgcolor: "primary.dark" },
                "&.Mui-disabled": { bgcolor: "#D6D1C7", color: "#fff" },
              }}
              aria-label="send message"
            >
              <SendIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>
      </Container>

      <BookingsDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        bookings={bookings}
        onCancel={handleCancelBooking}
      />
    </Box>
  );
}
