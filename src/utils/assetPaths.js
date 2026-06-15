const RAW_PUBLIC_URL = process.env.PUBLIC_URL || "";

export const PUBLIC_BASE = RAW_PUBLIC_URL.endsWith("/")
  ? RAW_PUBLIC_URL.slice(0, -1)
  : RAW_PUBLIC_URL;

export const SITE_ORIGIN =
  typeof window !== "undefined" && window.location?.origin
    ? window.location.origin
    : "";

export const SITE_BASE_URL =
  typeof window !== "undefined" && window.location?.origin
    ? `${window.location.origin}${PUBLIC_BASE && PUBLIC_BASE !== "." ? PUBLIC_BASE : ""}`
    : PUBLIC_BASE && PUBLIC_BASE !== "."
      ? PUBLIC_BASE
      : "";

export function assetUrl(path) {
  const trimmedPath = path.startsWith("/") ? path.slice(1) : path;
  if (!PUBLIC_BASE || PUBLIC_BASE === ".") {
    return `./${trimmedPath}`;
  }
  return `${PUBLIC_BASE}/${trimmedPath}`;
}
