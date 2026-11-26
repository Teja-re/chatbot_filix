// Plain fetch wrappers mapping 1-to-1 to FastAPI endpoints.

async function request(url, { method = "GET", body = null, token = null } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || "Something went wrong");
    err.status = res.status;
    throw err;
  }
  return data;
}

export function loginUser(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function registerUser(name, email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: { name, email, password },
  });
}

export function getSession(token, coords) {
  const params = new URLSearchParams();
  if (coords) {
    params.set("lat", String(coords.lat));
    params.set("lon", String(coords.lon));
  }
  const qs = params.toString();
  return request(`/api/chat/session${qs ? `?${qs}` : ""}`, { token });
}

export function sendChatAction(token, payload) {
  return request("/api/chat/action", {
    method: "POST",
    token,
    body: payload,
  });
}

export function getRestaurantSlots(token, restaurantId, bookingDate) {
  const params = new URLSearchParams({ booking_date: bookingDate });
  return request(`/api/restaurants/${restaurantId}/slots?${params.toString()}`, {
    token,
  });
}

export function enrichRestaurantMenu(token, restaurantId) {
  return request(`/api/restaurants/${restaurantId}/menu/enrich`, {
    method: "POST",
    token,
  });
}

export function getMyBookings(token) {
  return request("/api/bookings/my", { token });
}

export function cancelBooking(token, bookingId) {
  return request(`/api/bookings/${bookingId}/cancel`, {
    method: "PATCH",
    token,
  });
}
