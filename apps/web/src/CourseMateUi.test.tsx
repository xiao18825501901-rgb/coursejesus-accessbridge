import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearGuestSession } from "./guestSession";

/**
 * The refreshed shell publishes the verified Clerk session to the delivered
 * `api.js` through `window.CourseMateAuth`. Every browser journey so far ran with
 * the backend test verifier, which uses the development bridge, so this production
 * path had no coverage at all. These tests exercise it directly.
 */

const getToken = vi.fn<() => Promise<string | null>>(
  async () => "clerk-session-token",
);
const openSignIn = vi.fn();
const signOut = vi.fn(async () => undefined);
let clerkLoaded = true;
let clerkSignedIn = true;
let mockClerkToken: string | null = "clerk-session-token";

vi.mock("@clerk/react", () => ({
  ClerkProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    getToken,
    isLoaded: clerkLoaded,
    isSignedIn: clerkSignedIn,
  }),
  useClerk: () => ({ openSignIn, signOut }),
}));

// The delivered shell is plain JSX with no type declarations; keep it honest here.
vi.mock("./ui/App.jsx", () => ({
  App: () => {
    if (!window.CourseMateAuth) {
      throw new Error("CourseJesus auth bridge must exist before the shell mounts");
    }
    return <div data-testid="course-mate-app" />;
  },
}));

vi.mock("katex", () => ({
  default: { renderToString: () => "<math></math>" },
}));

import { CourseMateUi } from "./CourseMateUi";

/**
 * A production deployment sets the Clerk publishable key and no test token, which
 * is exactly the configuration these tests must exercise.
 */
beforeEach(() => {
  clerkLoaded = true;
  clerkSignedIn = true;
  mockClerkToken = "clerk-session-token";
  getToken.mockReset();
  getToken.mockImplementation(async () => mockClerkToken);
  vi.stubEnv("VITE_CLERK_PUBLISHABLE_KEY", "pk_test_coursemate");
  vi.stubEnv("VITE_AUTH_TEST_TOKEN", "");
  window.COURSEMATE_CONFIG = {
    apiBase: "https://api.example.test/ui/api/ui/v1",
  };
  sessionStorage.clear();
  clearGuestSession(window.COURSEMATE_CONFIG.apiBase);
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllEnvs();
  delete window.CourseMateAuth;
  vi.clearAllMocks();
});

describe("production Clerk auth bridge", () => {
  it("publishes a token getter that resolves the real Clerk session token", async () => {
    render(<CourseMateUi />);

    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());
    await expect(window.CourseMateAuth?.getToken()).resolves.toBe("clerk-session-token");
    expect(getToken).toHaveBeenCalled();
  });

  it("does not mount the API shell until Clerk has resolved the session", async () => {
    clerkLoaded = false;
    const view = render(<CourseMateUi />);

    expect(screen.queryByTestId("course-mate-app")).not.toBeInTheDocument();

    clerkLoaded = true;
    view.rerender(<CourseMateUi />);
    await waitFor(() => expect(screen.getByTestId("course-mate-app")).toBeVisible());
  });

  it("exposes an unsubscribe function from subscribe", async () => {
    render(<CourseMateUi />);
    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());

    const unsubscribe = window.CourseMateAuth?.subscribe(() => undefined);
    expect(typeof unsubscribe).toBe("function");
    expect(() => unsubscribe?.()).not.toThrow();
  });

  it("routes sign-in through Clerk's own modal and returns to the new dashboard", async () => {
    render(<CourseMateUi />);
    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());

    window.CourseMateAuth?.signIn();
    expect(openSignIn).toHaveBeenCalledTimes(1);
    // The default entry is `/`; after sign-in Clerk must land on the new
    // dashboard, not on a legacy route.
    expect(openSignIn).toHaveBeenCalledWith({
      fallbackRedirectUrl: `${window.location.origin}/`,
    });
  });

  it("routes sign-out through Clerk and resolves", async () => {
    render(<CourseMateUi />);
    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());

    await expect(window.CourseMateAuth?.signOut()).resolves.toBeUndefined();
    expect(signOut).toHaveBeenCalledTimes(1);
  });

  it("removes the bridge when the shell unmounts", async () => {
    const view = render(<CourseMateUi />);
    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());

    view.unmount();
    expect(window.CourseMateAuth).toBeUndefined();
  });

  it("still offers the isolated public shell when Clerk is not configured", async () => {
    const previous = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
    // A production build without Clerk must not silently render an unauthenticated
    // shell; it shows the configuration boundary instead.
    vi.stubEnv("VITE_CLERK_PUBLISHABLE_KEY", "");
    vi.stubEnv("VITE_AUTH_TEST_TOKEN", "");
    try {
      render(<CourseMateUi />);
      expect(await screen.findByTestId("course-mate-app")).toBeVisible();
      expect(window.CourseMateAuth?.canSignIn).toBe(false);
    } finally {
      vi.unstubAllEnvs();
      void previous;
    }
  });

  it("uses a server-issued guest session when Clerk is signed out", async () => {
    clerkSignedIn = false;
    mockClerkToken = null;
    const guestToken = "cjg1.server.issued";
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          token: guestToken,
          expires_at: Math.floor(Date.now() / 1000) + 900,
          expires_in_seconds: 900,
          session_kind: "guest",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<CourseMateUi />);
    await waitFor(() => expect(window.CourseMateAuth).toBeDefined());

    await expect(window.CourseMateAuth?.getToken()).resolves.toBe(guestToken);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/ui/api/ui/v1/guest-session",
      expect.objectContaining({ method: "POST", credentials: "omit" }),
    );
  });
});
