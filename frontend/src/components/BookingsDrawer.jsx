import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";

export default function BookingsDrawer({ open, onClose, bookings, onCancel }) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: { xs: "100%", sm: 410 }, bgcolor: "background.default", p: 2.5 },
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
        <Stack direction="row" spacing={1} alignItems="center">
          <EventAvailableIcon color="primary" />
          <Typography variant="h6">My Table Bookings</Typography>
        </Stack>
        <IconButton onClick={onClose} aria-label="close bookings">
          <CloseIcon />
        </IconButton>
      </Stack>

      <Divider sx={{ mb: 2 }} />

      {bookings.length === 0 ? (
        <Box sx={{ textAlign: "center", py: 6 }}>
          <Typography variant="body1" fontWeight={600} gutterBottom>
            No reservations yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select a nearby restaurant in the chat, inspect its menu nutrients, and book a table.
          </Typography>
        </Box>
      ) : (
        <Stack spacing={1.5}>
          {bookings.map((b) => (
            <Paper
              key={b.id}
              elevation={0}
              sx={{ p: 2, borderRadius: 2.5, border: "1px solid #E8E1D5" }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>
                    {b.restaurant_name}
                  </Typography>
                  <Stack direction="row" spacing={1} mt={0.5} flexWrap="wrap" useFlexGap>
                    <Chip size="small" label={b.booking_code} variant="outlined" />
                    <Chip
                      size="small"
                      label={b.status}
                      color={b.status === "CONFIRMED" ? "success" : "default"}
                    />
                  </Stack>
                </Box>

                {b.status === "CONFIRMED" && (
                  <Button
                    size="small"
                    color="error"
                    variant="outlined"
                    onClick={() => onCancel(b.id)}
                  >
                    Cancel
                  </Button>
                )}
              </Stack>

              <Typography variant="body2" color="text.secondary" mt={1.2}>
                {b.booking_date} at {b.time_slot} • {b.party_size} guests
              </Typography>
              {b.notes && (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                  {b.notes}
                </Typography>
              )}
            </Paper>
          ))}
        </Stack>
      )}
    </Drawer>
  );
}
