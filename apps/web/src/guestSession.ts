const STORAGE_PREFIX = "coursejesus.guest-session.v1:";
const EXPIRY_SKEW_SECONDS = 30;

interface StoredGuestSession {
  token: string;
  expiresAt: number;
}

interface GuestSessionResponse {
  token: string;
  expires_at: number;
  expires_in_seconds: number;
  session_kind: "guest";
}

const inFlight = new Map<string, Promise<string>>();
const memoryFallback = new Map<string, StoredGuestSession>();

function normalizeApiBase(apiBase: string): string {
  return apiBase.replace(/\/+$/, "");
}

function storageKey(apiBase: string): string {
  return STORAGE_PREFIX + normalizeApiBase(apiBase);
}

function readStored(apiBase: string): StoredGuestSession | null {
  const key = storageKey(apiBase);
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<StoredGuestSession>;
      if (
        typeof parsed.token === "string" &&
        parsed.token.length > 0 &&
        typeof parsed.expiresAt === "number" &&
        Number.isFinite(parsed.expiresAt)
      ) {
        return { token: parsed.token, expiresAt: parsed.expiresAt };
      }
      sessionStorage.removeItem(key);
    }
  } catch {
    // Storage may be blocked. The per-tab in-memory fallback still works.
  }
  return memoryFallback.get(key) ?? null;
}

function writeStored(apiBase: string, session: StoredGuestSession): void {
  const key = storageKey(apiBase);
  memoryFallback.set(key, session);
  try {
    sessionStorage.setItem(key, JSON.stringify(session));
  } catch {
    // Keep the in-memory session when storage is unavailable.
  }
}

function removeStored(apiBase: string): void {
  const key = storageKey(apiBase);
  memoryFallback.delete(key);
  try {
    sessionStorage.removeItem(key);
  } catch {
    // Nothing else is needed when storage is unavailable.
  }
}

function isValid(session: StoredGuestSession): boolean {
  return session.expiresAt > Date.now() / 1000 + EXPIRY_SKEW_SECONDS;
}

function validateResponse(value: unknown): GuestSessionResponse {
  if (!value || typeof value !== "object") {
    throw new Error("GUEST_SESSION_INVALID_RESPONSE");
  }
  const body = value as Partial<GuestSessionResponse>;
  if (
    body.session_kind !== "guest" ||
    typeof body.token !== "string" ||
    body.token.length === 0 ||
    typeof body.expires_at !== "number" ||
    !Number.isFinite(body.expires_at) ||
    typeof body.expires_in_seconds !== "number" ||
    !Number.isFinite(body.expires_in_seconds)
  ) {
    throw new Error("GUEST_SESSION_INVALID_RESPONSE");
  }
  return body as GuestSessionResponse;
}

async function requestGuestSession(apiBase: string): Promise<string> {
  const normalized = normalizeApiBase(apiBase);
  const response = await fetch(`${normalized}/guest-session`, {
    method: "POST",
    credentials: "omit",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const error = new Error(`GUEST_SESSION_HTTP_${response.status}`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  const session = validateResponse(await response.json());
  writeStored(normalized, {
    token: session.token,
    expiresAt: session.expires_at,
  });
  return session.token;
}

export function getGuestSessionToken(apiBase: string): Promise<string> {
  const normalized = normalizeApiBase(apiBase);
  const cached = readStored(normalized);
  if (cached && isValid(cached)) {
    return Promise.resolve(cached.token);
  }
  if (cached) {
    removeStored(normalized);
  }

  const pending = inFlight.get(normalized);
  if (pending) {
    return pending;
  }

  const request = requestGuestSession(normalized).finally(() => {
    if (inFlight.get(normalized) === request) {
      inFlight.delete(normalized);
    }
  });
  inFlight.set(normalized, request);
  return request;
}

export function clearGuestSession(apiBase: string): void {
  const normalized = normalizeApiBase(apiBase);
  removeStored(normalized);
  inFlight.delete(normalized);
}
