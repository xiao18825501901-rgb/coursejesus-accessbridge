import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearGuestSession, getGuestSessionToken } from "./guestSession";

describe("public guest session", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("requests one server-issued token per browser tab and reuses it", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          token: "cjg1.server.issued",
          expires_at: 2_000_000_000,
          expires_in_seconds: 900,
          session_kind: "guest",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      getGuestSessionToken("https://api.example.test/ui/api/ui/v1"),
    ).resolves.toBe("cjg1.server.issued");
    await expect(
      getGuestSessionToken("https://api.example.test/ui/api/ui/v1"),
    ).resolves.toBe("cjg1.server.issued");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/ui/api/ui/v1/guest-session",
      expect.objectContaining({
        method: "POST",
        credentials: "omit",
        cache: "no-store",
      }),
    );
  });

  it("clears only the current API namespace before requesting a replacement", async () => {
    const apiBase = "https://api.example.test/ui/api/ui/v1";
    sessionStorage.setItem("coursejesus.guest-session.v1:" + apiBase, "old-token");
    clearGuestSession(apiBase);

    expect(
      sessionStorage.getItem("coursejesus.guest-session.v1:" + apiBase),
    ).toBeNull();
  });
});
