const RAW_PUBLIC_URL = process.env.PUBLIC_URL || "";

export const PUBLIC_BASE = RAW_PUBLIC_URL.endsWith("/")
  ? RAW_PUBLIC_URL.slice(0, -1)
  : RAW_PUBLIC_URL;

export function assetUrl(path) {
  const trimmedPath = path.startsWith("/") ? path.slice(1) : path;
  if (!PUBLIC_BASE || PUBLIC_BASE === ".") {
    return `./${trimmedPath}`;
  }
  return `${PUBLIC_BASE}/${trimmedPath}`;
}
