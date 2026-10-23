let csrf = "";
let onAccessLoss = () => {};
export function configureApi(token, handler) {
  csrf = token || "";
  onAccessLoss = handler || (() => {});
}
export class ApiError extends Error {
  constructor(code, status) {
    super(code);
    this.code = code;
    this.status = status;
  }
}
export const errors = {
  invalid_credentials: "Email or password was not accepted.",
  authentication_failed: "Email or password was not accepted.",
  authentication_unavailable:
    "The sign-in service is unavailable. Please try again shortly.",
  authentication_not_configured:
    "Sign-in is not configured on this server. Contact the hatchery owner.",
  invalid_token:
    "The sign-in response could not be verified. Please try again shortly.",
  access_denied: "You do not have access to this hatchery.",
  authentication_throttled:
    "Too many sign-in attempts. Wait a minute before trying again.",
  stale_version: "Someone changed this item. Refresh it before saving again.",
  command_pending:
    "This device already has a pending command. Refresh its status.",
  device_not_ready:
    "The device needs a confirmed assignment before it can receive commands.",
  claim_unavailable:
    "Check the device ID and private claim code, or contact the device provider.",
  invalid_request: "Check the form values and try again.",
  invalid_time_range: "The end time must follow the start time.",
  tank_archived: "Restore this tank before making changes.",
  csrf_denied: "Refresh your session and try again.",
  active_bindings: "Unassign the devices before archiving this resource.",
  resource_archived: "Restore this resource before changing it.",
  device_unverified:
    "This device must prove its identity before it can be assigned.",
  claim_pending:
    "This device already has a pending claim. Check its status before retrying.",
  measurement_required: "Enter at least one measured value.",
  future_measurement: "Measured time cannot be more than five minutes ahead.",
  request_id_conflict:
    "This attempt may already be saved. Refresh history before changing and resubmitting it.",
};
export function message(error) {
  return (
    errors[error?.code || error?.message] ||
    (error?.status === 422
      ? "Check the form values and try again."
      : "The request could not be completed. Please try again.")
  );
}
export async function request(
  path,
  { body, method = "GET", passive = false, signal, key, download = false } = {},
) {
  const headers = {};
  if (passive) headers["X-BB-Passive"] = "1";
  if (method !== "GET") headers["X-CSRF-Token"] = csrf;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (key) headers["Idempotency-Key"] = key;
  const response = await fetch("/api/v1" + path, {
    method,
    headers,
    credentials: "include",
    signal,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new ApiError(
      data.error?.code || "request_failed",
      response.status,
    );
    if ([401, 403].includes(response.status) && path !== "/auth/login")
      onAccessLoss(error);
    throw error;
  }
  return download
    ? response.blob()
    : response.status === 204
      ? null
      : response.json();
}
export function hatcheryPath(hatchery, suffix = "") {
  return `/hatcheries/${hatchery}${suffix}`;
}
export function query(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== undefined && value !== null)
      params.set(key, value);
  });
  return params.toString();
}
