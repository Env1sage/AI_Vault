import { ApiError } from "./api-client";
import { getAccessToken } from "./session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** A plain `<a href>` can't hit an authenticated endpoint — the access
 * token lives in memory (`session.ts`), not a cookie — so downloading
 * requires a real `fetch` with the Bearer header, then handing the
 * response off to the browser as a synthetic click. No retry-on-401 here
 * (unlike `apiClient`): a download is a one-shot user action, not
 * something worth silently retrying after a session refresh. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const accessToken = getAccessToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (!response.ok) {
    throw new ApiError(`Download failed (${response.status}).`, response.status, "download_failed");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
