const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (res.status === 204) return null;

  let body = null;
  try {
    body = await res.json();
  } catch {
    // no body
  }

  if (!res.ok) {
    const message = body?.detail || `Request failed with status ${res.status}`;
    throw new ApiError(message, res.status, body?.detail);
  }

  return body;
}

const asJson = (data) => JSON.stringify(data);

export const api = {
  // Users
  listUsers: (params = {}) => request(`/users/?${new URLSearchParams(params)}`),
  createUser: (data) => request(`/users/`, { method: "POST", body: asJson(data) }),
  updateUser: (id, data) => request(`/users/${id}`, { method: "PUT", body: asJson(data) }),
  deleteUser: (id) => request(`/users/${id}`, { method: "DELETE" }),

  // Tanks
  listTanks: (params = {}) => request(`/tanks/?${new URLSearchParams(params)}`),
  getTank: (id) => request(`/tanks/${id}`),
  getTankSummary: (id) => request(`/tanks/${id}/summary`),
  createTank: (data) => request(`/tanks/`, { method: "POST", body: asJson(data) }),
  updateTank: (id, data) => request(`/tanks/${id}`, { method: "PUT", body: asJson(data) }),
  deleteTank: (id) => request(`/tanks/${id}`, { method: "DELETE" }),

  // Water logs
  listWaterLogs: (tankId, params = {}) =>
    request(`/tanks/${tankId}/logs?${new URLSearchParams(params)}`),
  createWaterLog: (tankId, data) =>
    request(`/tanks/${tankId}/logs`, { method: "POST", body: asJson(data) }),
  deleteWaterLog: (tankId, logId) =>
    request(`/tanks/${tankId}/logs/${logId}`, { method: "DELETE" }),

  // Feeding logs
  listFeedingLogs: (tankId, params = {}) =>
    request(`/tanks/${tankId}/feedings?${new URLSearchParams(params)}`),
  createFeedingLog: (tankId, data) =>
    request(`/tanks/${tankId}/feedings`, { method: "POST", body: asJson(data) }),
  deleteFeedingLog: (tankId, feedingId) =>
    request(`/tanks/${tankId}/feedings/${feedingId}`, { method: "DELETE" }),
};

export { ApiError };
