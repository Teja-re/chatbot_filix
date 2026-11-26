import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import SearchIcon from "@mui/icons-material/Search";
import StarIcon from "@mui/icons-material/Star";

const HEALTH_GOALS = [
  { label: "High Protein", value: "High Protein" },
  { label: "Low Calorie", value: "Low Calorie" },
  { label: "High Fiber", value: "High Fiber" },
  { label: "Plant-Based", value: "Plant-Based" },
];

export default function NearbyRestaurants({
  restaurants,
  recommendations = [],
  healthGoal,
  busy,
  onSelect,
  onRecommendHealth,
  onClearHealth,
  onDecline,
}) {
  const [search, setSearch] = useState("");

  const recByRestId = new Map(recommendations.map((r) => [r.restaurant_id, r]));

  const query = search.trim().toLowerCase();
  let visible = !query
    ? [...restaurants]
    : restaurants.filter(
        (r) =>
          r.name.toLowerCase().includes(query) ||
          r.cuisine.toLowerCase().includes(query) ||
          r.address.toLowerCase().includes(query)
      );

  // Move AI health-recommended restaurants to the top while keeping original order for the rest
  if (recByRestId.size > 0) {
    visible.sort((a, b) => {
      const aRec = recByRestId.has(a.id) ? 0 : 1;
      const bRec = recByRestId.has(b.id) ? 0 : 1;
      return aRec - bRec;
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
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        spacing={1.5}
        mb={1.5}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>
            Nearby Restaurants ({visible.length})
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Pick one to inspect dishes &amp; nutrients, or tap a health goal for AI picks
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            size="small"
            placeholder="Filter by name or cuisine..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: { xs: 0, sm: 220 }, flex: 1 }}
          />
          <Button
            size="small"
            color="error"
            variant="text"
            disabled={busy}
            onClick={onDecline}
            sx={{ whiteSpace: "nowrap" }}
          >
            Not Booking
          </Button>
        </Stack>
      </Stack>

      {/* AI Health Advisor chip bar */}
      <Stack
        direction="row"
        spacing={0.75}
        alignItems="center"
        flexWrap="wrap"
        useFlexGap
        sx={{ mb: 2, p: 1.25, borderRadius: 2, bgcolor: "#FAF8F5", border: "1px solid #EDE7DC" }}
      >
        <Stack direction="row" spacing={0.5} alignItems="center" mr={0.5}>
          <AutoAwesomeIcon sx={{ fontSize: 16, color: "primary.main" }} />
          <Typography variant="caption" fontWeight={700} color="primary.main">
            AI Health Picks:
          </Typography>
        </Stack>
        {HEALTH_GOALS.map((g) => (
          <Chip
            key={g.value}
            size="small"
            label={g.label}
            clickable
            disabled={busy}
            color={healthGoal === g.value ? "primary" : "default"}
            variant={healthGoal === g.value ? "filled" : "outlined"}
            onClick={() => onRecommendHealth(g.value)}
          />
        ))}
        {recommendations.length > 0 && (
          <Chip size="small" label="Clear" clickable disabled={busy} onClick={onClearHealth} />
        )}
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
          gap: 1.5,
        }}
      >
        {visible.map((rest) => {
          const rec = recByRestId.get(rest.id);
          return (
            <Card
              key={rest.id}
              elevation={0}
              sx={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                border: rec ? "1.5px solid #2D6A4F" : undefined,
                bgcolor: rec ? "#F7FCF9" : undefined,
                transition: "transform 0.18s ease, box-shadow 0.18s ease",
                "&:hover": {
                  transform: "translateY(-2px)",
                  boxShadow: "0 8px 22px rgba(27, 67, 50, 0.1)",
                },
              }}
            >
              <CardContent sx={{ pb: 1.5 }}>
                {rec && (
                  <Box mb={1}>
                    <Chip
                      size="small"
                      icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
                      label={rec.badge}
                      color="success"
                      sx={{ fontWeight: 700, mb: 0.6 }}
                    />
                    <Typography variant="caption" color="primary.dark" display="block">
                      {rec.reason}
                    </Typography>
                    {rec.recommended_dishes.length > 0 && (
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap mt={0.5}>
                        {rec.recommended_dishes.map((dish) => (
                          <Chip key={dish} size="small" label={dish} variant="outlined" />
                        ))}
                      </Stack>
                    )}
                  </Box>
                )}

                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
                  <Typography variant="subtitle1" fontWeight={700} lineHeight={1.25}>
                    {rest.name}
                  </Typography>
                  <Chip
                    size="small"
                    icon={<StarIcon sx={{ fontSize: 15, color: "#D97706 !important" }} />}
                    label={rest.rating}
                    sx={{ bgcolor: "#FEF6E6", fontWeight: 700 }}
                  />
                </Stack>

                <Typography variant="body2" color="secondary.main" fontWeight={600} mt={0.5}>
                  {rest.cuisine} • {rest.price_tier}
                </Typography>

                <Stack direction="row" spacing={0.5} alignItems="center" mt={1}>
                  <LocationOnIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                  <Typography variant="caption" color="text.secondary">
                    {rest.address} • {rest.distance_km} km away
                  </Typography>
                </Stack>

                <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                  {rest.total_seats} seats • Open {rest.open_hours}
                </Typography>
              </CardContent>

              <Box sx={{ px: 2, pb: 2 }}>
                <Button
                  variant="contained"
                  color={rec ? "secondary" : "primary"}
                  fullWidth
                  disabled={busy}
                  onClick={() => onSelect(rest.id)}
                >
                  View Menu &amp; Nutrients
                </Button>
              </Box>
            </Card>
          );
        })}
      </Box>
    </Paper>
  );
}
