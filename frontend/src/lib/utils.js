import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Safely extract a human-readable error message from an axios (or fetch) error.
 *
 * FastAPI validation errors return HTTP 422 with `detail` as an ARRAY of
 * objects ({ type, loc, msg, input }). Rendering such an array/object directly
 * as a React child throws "Objects are not valid as a React child"
 * (Minified React error #31). This helper normalizes any error shape into a
 * plain string.
 */
export function getErrorMessage(err, fallback = "An unexpected error occurred") {
  if (!err) return fallback;

  // axios-style error: err.response.data
  const data = err?.response?.data;
  if (data) {
    if (typeof data.detail === "string" && data.detail) return data.detail;
    if (Array.isArray(data.detail)) {
      const msg = data.detail
        .map((d) => (d && typeof d === "object" ? d.msg : String(d)))
        .filter(Boolean)
        .join("; ");
      return msg || fallback;
    }
    if (typeof data.message === "string" && data.message) return data.message;
  }

  // Already a string (e.g. Error.message passed through)
  if (typeof err === "string") return err;
  if (typeof err.message === "string" && err.message) return err.message;

  return fallback;
}