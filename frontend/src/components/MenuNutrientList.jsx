import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import FavoriteIcon from "@mui/icons-material/Favorite";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import LocalFireDepartmentIcon from "@mui/icons-material/LocalFireDepartment";
import RefreshIcon from "@mui/icons-material/Refresh";
import TableRestaurantIcon from "@mui/icons-material/TableRestaurant";

const DIET_FILTERS = ["All", "Veg", "Vegan", "High-Protein", "Gluten-Free"];

export default function MenuNutrientList({
  restaurant,
  items,
  likedIds,
  busy,
  refreshing,
  onToggleLike,
  onRefreshNutrition,
  onAskCombo,
  onStartBooking,
  onBack,
  onDecline,
}) {
  const [dietFilter, setDietFilter] = useState("All");
  const [sortBy, setSortBy] = useState("default");

  let visibleItems =
    dietFilter === "All"
      ? [...items]
      : items.filter((item) =>
          item.dietary_tags.some((t) => t.toLowerCase() === dietFilter.toLowerCase())
        );

  if (sortBy === "low_cal") {
    visibleItems.sort((a, b) => a.calories_kcal - b.calories_kcal);
  } else if (sortBy === "high_protein") {
    visibleItems.sort((a, b) => b.protein_g - a.protein_g);
  }

  const aiEnriched = items.some((i) => i.nutrition_source && i.nutrition_source.endsWith("_llm"));

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
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={1}
        mb={1.5}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>
            {restaurant.name} — Menu, Ingredients &amp; Nutrients
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {restaurant.cuisine} • {restaurant.address} • Open {restaurant.open_hours}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
          <Chip
            size="small"
            icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
            label={aiEnriched ? "AI Nutrition" : "Baseline Nutrition"}
            color={aiEnriched ? "success" : "default"}
            variant="outlined"
          />
          <Chip
            size="small"
            color="primary"
            variant="outlined"
            label={`Liked: ${likedIds.length}`}
          />
          <Button
            size="small"
            variant="text"
            startIcon={<RefreshIcon />}
            disabled={busy || refreshing}
            onClick={onRefreshNutrition}
          >
            {refreshing ? "Fetching AI..." : "Refresh AI"}
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap mb={1.25}>
        {DIET_FILTERS.map((tag) => (
          <Chip
            key={tag}
            label={tag}
            size="small"
            clickable
            color={dietFilter === tag ? "primary" : "default"}
            variant={dietFilter === tag ? "filled" : "outlined"}
            onClick={() => setDietFilter(tag)}
          />
        ))}
      </Stack>

      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap mb={2}>
        <Chip
          label="Default order"
          size="small"
          clickable
          color={sortBy === "default" ? "secondary" : "default"}
          variant={sortBy === "default" ? "filled" : "outlined"}
          onClick={() => setSortBy("default")}
        />
        <Chip
          label="Lowest Calories"
          size="small"
          clickable
          color={sortBy === "low_cal" ? "secondary" : "default"}
          variant={sortBy === "low_cal" ? "filled" : "outlined"}
          onClick={() => setSortBy("low_cal")}
        />
        <Chip
          label="Highest Protein"
          size="small"
          clickable
          color={sortBy === "high_protein" ? "secondary" : "default"}
          variant={sortBy === "high_protein" ? "filled" : "outlined"}
          onClick={() => setSortBy("high_protein")}
        />
        <Chip
          icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
          label="Ask AI for 500 kcal Combo"
          size="small"
          clickable
          disabled={busy}
          color="primary"
          variant="outlined"
          onClick={onAskCombo}
        />
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
          gap: 1.5,
        }}
      >
        {visibleItems.map((item) => {
          const isLiked = likedIds.includes(item.id);
          return (
            <Card key={item.id} elevation={0}>
              <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
                  <Box>
                    <Typography variant="subtitle2" fontWeight={700}>
                      {item.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.category} • ₹{item.price}
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    disabled={busy}
                    onClick={() => onToggleLike(item.id)}
                    color={isLiked ? "secondary" : "default"}
                    aria-label={isLiked ? "Unlike dish" : "Like dish"}
                  >
                    {isLiked ? <FavoriteIcon /> : <FavoriteBorderIcon />}
                  </IconButton>
                </Stack>

                <Typography variant="body2" color="text.secondary" sx={{ my: 0.75, fontSize: "0.82rem" }}>
                  {item.description}
                </Typography>

                {item.ingredients && item.ingredients.length > 0 && (
                  <Typography
                    variant="caption"
                    color="text.primary"
                    display="block"
                    sx={{ mb: 1, bgcolor: "#FAF8F5", p: 0.75, borderRadius: 1.5 }}
                  >
                    <strong>Ingredients:</strong> {item.ingredients.join(", ")}
                  </Typography>
                )}

                <Stack direction="row" spacing={0.6} flexWrap="wrap" useFlexGap mb={1}>
                  <Chip
                    size="small"
                    icon={<LocalFireDepartmentIcon sx={{ fontSize: 14 }} />}
                    label={`${item.calories_kcal} kcal`}
                    sx={{ bgcolor: "#FDF1EC", color: "#9C3F1E", fontWeight: 600 }}
                  />
                  <Chip size="small" label={`P: ${item.protein_g}g`} sx={{ bgcolor: "#E8F4ED" }} />
                  <Chip size="small" label={`C: ${item.carbs_g}g`} />
                  <Chip size="small" label={`F: ${item.fat_g}g`} />
                  <Chip size="small" label={`Fiber: ${item.fiber_g}g`} />
                </Stack>

                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  {item.health_note && (
                    <Chip size="small" color="success" label={item.health_note} />
                  )}
                  {item.dietary_tags.map((tag) => (
                    <Chip key={tag} size="small" label={tag} variant="outlined" />
                  ))}
                  {item.allergens &&
                    item.allergens.map((alg) => (
                      <Chip
                        key={alg}
                        size="small"
                        color="warning"
                        variant="outlined"
                        label={`Allergen: ${alg}`}
                      />
                    ))}
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        mt={2}
        pt={2}
        sx={{ borderTop: "1px solid #EAE4DA" }}
      >
        <Button
          variant="contained"
          color="secondary"
          startIcon={<TableRestaurantIcon />}
          disabled={busy}
          onClick={onStartBooking}
        >
          Proceed to Book Table
        </Button>
        <Button
          variant="outlined"
          color="primary"
          startIcon={<ArrowBackIcon />}
          disabled={busy}
          onClick={onBack}
        >
          Back to Restaurants
        </Button>
        <Button variant="text" color="error" disabled={busy} onClick={onDecline}>
          No Booking Today
        </Button>
      </Stack>
    </Paper>
  );
}
