// Dynamically point to the same IP address the frontend is hosted on, but port 8000
const defaultBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000`;
const BASE_URL = import.meta.env.VITE_API_URL || defaultBaseUrl;

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
  getAllLogs: (params = {}) =>
    request(`/tanks/logs/all?${new URLSearchParams(params)}`),


  // Devices
  listDevices: () => request(`/devices/`),
  getDevice: (id) => request(`/devices/${id}`),
  sendCommand: (id, command) => request(`/devices/${id}/command`, { method: "POST", body: asJson(command) }),

  // Predictions
  getLatestPrediction: (tankId) => request(`/tanks/${tankId}/predictions/latest`),
  getPredictionHistory: (tankId) => request(`/tanks/${tankId}/predictions/`),
};

export const getWsUrl = (path) => {
  const isHttps = window.location.protocol === "https:";
  const wsProtocol = isHttps ? "wss:" : "ws:";
  
  // If BASE_URL is an absolute URL (e.g. http://localhost:8000), use its host.
  // Otherwise, use the window's host.
  try {
    const apiURL = new URL(BASE_URL);
    return `${wsProtocol}//${apiURL.host}${path}`;
  } catch {
    return `${wsProtocol}//${window.location.host}${path}`;
  }
};

export { ApiError };
