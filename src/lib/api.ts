export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "https://csi4999-api-h4exhuc3b3btafg3.eastus-01.azurewebsites.net/").replace(/\/+$/, "");

let token = process.env.EXPO_PUBLIC_JWT_TOKEN ?? "";

export const setToken = (t: string) => {
  token = t;
};

export const hasToken = () => token.length > 0;

let unauthorizedHandler: (() => void) | null = null;

export const onUnauthorized = (handler: () => void) => {
  unauthorizedHandler = handler;
};

export async function apiFetch<T = any>(
  path: string,
  body?: unknown,
  method: string = body === undefined ? "GET" : "POST",
  signal?: AbortSignal
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (hasToken()) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (res.status === 401 && hasToken()) {
    setToken("");
    unauthorizedHandler?.();
    throw new Error("Your session has expired. Please log in again.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Request failed.");
  }
  return res.json();
}
