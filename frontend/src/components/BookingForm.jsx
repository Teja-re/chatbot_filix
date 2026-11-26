import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RemoveIcon from "@mui/icons-material/Remove";
import { getRestaurantSlots } from "../api";

function getIsoOffset(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function BookingForm({
  token,
  restaurant,
  initialSlots,
  likedCount,
  bookingDraft,
  busy,
  onConfirm,
  onBackToMenu,
  onBackToList,
  onDecline,
}) {
  const today = getIsoOffset(0);
  const tomorrow = getIsoOffset(1);

  const [bookingDate, setBookingDate] = useState(bookingDraft?.booking_date || today);
  const [slots, setSlots] = useState(initialSlots);
  const [timeSlot, setTimeSlot] = useState(bookingDraft?.time_slot || initialSlots[0]?.time_slot || "19:00");
  const [partySize, setPartySize] = useState(bookingDraft?.party_size || 2);
  const [notes, setNotes] = useState(bookingDraft?.notes || "");
  const [slotError, setSlotError] = useState("");

  useEffect(() => {
    if (!bookingDraft) return;
    if (bookingDraft.booking_date) setBookingDate(bookingDraft.booking_date);
    if (bookingDraft.time_slot) setTimeSlot(bookingDraft.time_slot);
    if (bookingDraft.party_size) setPartySize(bookingDraft.party_size);
    if (bookingDraft.notes) setNotes(bookingDraft.notes);
  }, [bookingDraft]);

  useEffect(() => {
    let active = true;
    async function refreshSlots() {
      try {
        setSlotError("");
        const data = await getRestaurantSlots(token, restaurant.id, bookingDate);
        if (active) {
          setSlots(data);
        }
      } catch (err) {
        if (active) setSlotError(err.message);
      }
    }
    refreshSlots();
    return () => {
      active = false;
    };
  }, [token, restaurant.id, bookingDate]);

  function handleSubmit(e) {
    e.preventDefault();
    onConfirm({
      booking_date: bookingDate,
      time_slot: timeSlot,
      party_size: partySize,
      notes,
    });
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 1.75, sm: 2.25 },
        borderRadius: 3,
        border: "1px solid #E8E1D5",
        bgcolor: "#FFFFFF",
      }}
    >
      <Typography variant="subtitle1" fontWeight={700}>
        Reserve Table at {restaurant.name}
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" mb={2}>
        {restaurant.address} • {restaurant.total_seats} total seats
        {likedCount > 0 ? ` • ${likedCount} liked dish(es) will be attached` : ""}
      </Typography>

      {slotError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {slotError}
        </Alert>
      )}

      <Stack component="form" spacing={2} onSubmit={handleSubmit}>
        <Box>
          <Typography variant="body2" fontWeight={600} mb={1}>
            Select Date
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
            <Chip
              label="Today"
              clickable
              color={bookingDate === today ? "primary" : "default"}
              onClick={() => setBookingDate(today)}
            />
            <Chip
              label="Tomorrow"
              clickable
              color={bookingDate === tomorrow ? "primary" : "default"}
              onClick={() => setBookingDate(tomorrow)}
            />
            <TextField
              type="date"
              size="small"
              value={bookingDate}
              inputProps={{ min: today }}
              onChange={(e) => setBookingDate(e.target.value)}
            />
          </Stack>
        </Box>

        <Box>
          <Typography variant="body2" fontWeight={600} mb={1}>
            Guests
          </Typography>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <IconButton
              size="small"
              onClick={() => setPartySize((n) => Math.max(1, n - 1))}
              disabled={partySize <= 1}
              sx={{ border: "1px solid #E8E1D5" }}
            >
              <RemoveIcon fontSize="small" />
            </IconButton>
            <Typography variant="subtitle1" fontWeight={700} minWidth={32} textAlign="center">
              {partySize}
            </Typography>
            <IconButton
              size="small"
              onClick={() => setPartySize((n) => Math.min(20, n + 1))}
              disabled={partySize >= 20}
              sx={{ border: "1px solid #E8E1D5" }}
            >
              <AddIcon fontSize="small" />
            </IconButton>
            <Typography variant="caption" color="text.secondary">
              {partySize === 1 ? "guest" : "guests"}
            </Typography>
          </Stack>
        </Box>

        <Box>
          <Typography variant="body2" fontWeight={600} mb={1}>
            Time Slot (live remaining seats)
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {slots.map((slot) => {
              const unavailable = slot.available_seats < partySize;
              const selected = timeSlot === slot.time_slot;
              return (
                <Button
                  key={slot.time_slot}
                  type="button"
                  disabled={unavailable}
                  variant={selected ? "contained" : "outlined"}
                  color={selected ? "secondary" : "primary"}
                  onClick={() => setTimeSlot(slot.time_slot)}
                  sx={{ flexDirection: "column", alignItems: "flex-start", py: 0.75, px: 1.5 }}
                >
                  <span>{slot.time_slot}</span>
                  <Typography
                    variant="caption"
                    sx={{ opacity: 0.85, fontSize: "0.7rem", lineHeight: 1.1 }}
                  >
                    {slot.available_seats} seats left
                  </Typography>
                </Button>
              );
            })}
          </Stack>
        </Box>

        <TextField
          label="Special Requests (optional)"
          size="small"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Window table, allergy note, birthday..."
          inputProps={{ maxLength: 300 }}
          fullWidth
        />

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          pt={1}
          sx={{ borderTop: "1px solid #EAE4DA" }}
        >
          <Button type="submit" variant="contained" color="secondary" disabled={busy}>
            {busy ? "Confirming..." : "Confirm Table Booking"}
          </Button>
          <Button
            type="button"
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            disabled={busy}
            onClick={onBackToMenu}
          >
            Back to Menu
          </Button>
          <Button type="button" variant="text" disabled={busy} onClick={onBackToList}>
            Switch Restaurant
          </Button>
          <Button type="button" variant="text" color="error" disabled={busy} onClick={onDecline}>
            No Booking Today
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}
