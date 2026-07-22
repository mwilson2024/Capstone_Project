const apiURL = process.env.EXPO_PUBLIC_API_URL?.trim();

export const API_URL = apiURL ? apiURL.replace(/\/+$/, "") : "";
export const API_CONFIGURED = API_URL.length > 0;

const apiEndpoint = (path: string) => {
  if (!API_CONFIGURED) {
    throw new Error("The server connection is not configured. Please try again later.");
  }

  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
};

let token = process.env.EXPO_PUBLIC_JWT_TOKEN ?? "";

export const setToken = (t: string) => {
  token = t;
};

export const hasToken = () => token.length > 0;

let unauthorizedHandler: (() => void) | null = null;

export const onUnauthorized = (handler: () => void) => {
  unauthorizedHandler = handler;
};

const authHeaders = (): Record<string, string> =>
  hasToken() ? { Authorization: `Bearer ${token}` } : {};

async function parse<T>(res: Response, handleUnauthorized = true): Promise<T> {
  if (handleUnauthorized && res.status === 401 && hasToken()) {
    setToken("");
    unauthorizedHandler?.();
    throw new Error("Your session has expired. Please log in again.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    let message = "Request failed.";

    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item.msg === "string") return item.msg;
          return null;
        })
        .filter((item): item is string => Boolean(item));
      if (messages.length > 0) message = messages.join(" ");
    }

    throw new Error(message);
  }
  return res.json();
}

export async function apiFetch<T = any>(
  path: string,
  body?: unknown,
  method: string = body === undefined ? "GET" : "POST",
  signal?: AbortSignal
): Promise<T> {
  const res = await fetch(apiEndpoint(path), {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  return parse<T>(res);
}

export async function apiPublicFetch<T = any>(
  path: string,
  body?: unknown,
  method: string = body === undefined ? "GET" : "POST",
  signal?: AbortSignal
): Promise<T> {
  const res = await fetch(apiEndpoint(path), {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  return parse<T>(res, false);
}

export async function apiUpload<T = any>(path: string, form: FormData): Promise<T> {
  const res = await fetch(apiEndpoint(path), {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  return parse<T>(res);
}

export async function apiPublicUpload<T = any>(
  path: string,
  form: FormData
): Promise<T> {
  const res = await fetch(apiEndpoint(path), {
    method: "POST",
    body: form,
  });
  return parse<T>(res, false);
}
