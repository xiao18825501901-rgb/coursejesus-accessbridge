import { ClerkProvider, useAuth, useClerk } from "@clerk/react";
import katex from "katex";
import { useEffect, useState } from "react";

import { App as CourseMateApp } from "./ui/App.jsx";
import { BRAND } from "./brand";
import {
  clearGuestSession,
  getGuestSessionToken,
} from "./guestSession";
import { UiLocaleProvider } from "./ui/UiLocale";

import "./ui/styles.css";
import "./ui/styles-extra.css";
import "./ui/theme.css";

/**
 * The new CourseJesus shell renders KaTeX to MathML and refuses to build React
 * elements from any other model HTML, so it only needs the render entry point.
 */
window.CourseMateMath = katex;

interface CourseMateAuthBridge {
  getToken: () => Promise<string | null>;
  subscribe: (listener: () => void) => () => void;
  signIn: () => void;
  signOut: () => Promise<void>;
  canSignIn?: boolean;
}

declare global {
  interface Window {
    CourseMateMath?: typeof katex;
    CourseMateAuth?: CourseMateAuthBridge;
  }
}

/**
 * Development and E2E identity, mirroring the existing `VITE_AUTH_TEST_TOKEN`
 * convention in `main.tsx`.
 *
 * The project's E2E runs authenticate with the backend's test verifier, which
 * accepts `Bearer test-session-token`. Vite inlines this value only when the build
 * was given it; a production build without the variable leaves it undefined and
 * falls through to Clerk, so this cannot silently bypass production sign-in.
 */
const testToken = import.meta.env.VITE_AUTH_TEST_TOKEN;

function currentApiBase(): string {
  return (
    window.COURSEMATE_CONFIG?.apiBase ??
    import.meta.env.VITE_UI_API_BASE ??
    "/ui-extension/api/ui/v1"
  );
}

function TestAuthBridge({ token }: { token: string }) {
  const [bridgeReady, setBridgeReady] = useState(false);

  useEffect(() => {
    window.CourseMateAuth = {
      getToken: async () => token,
      subscribe: () => () => undefined,
      signIn: () => undefined,
      signOut: async () => undefined,
      canSignIn: false,
    };
    setBridgeReady(true);
    return () => {
      delete window.CourseMateAuth;
    };
  }, [token]);

  return bridgeReady ? <UiLocaleProvider><CourseMateApp /></UiLocaleProvider> : null;
}

function GuestOnlyAuthBridge() {
  const [bridgeReady, setBridgeReady] = useState(false);

  useEffect(() => {
    const apiBase = currentApiBase();
    window.CourseMateAuth = {
      getToken: () => getGuestSessionToken(apiBase),
      subscribe: () => () => undefined,
      signIn: () => undefined,
      signOut: async () => {
        clearGuestSession(apiBase);
      },
      canSignIn: false,
    };
    setBridgeReady(true);
    return () => {
      delete window.CourseMateAuth;
    };
  }, []);

  return bridgeReady ? <UiLocaleProvider><CourseMateApp /></UiLocaleProvider> : null;
}

/**
 * Publish the already-verified Clerk session to the new shell.
 *
 * The delivered `api.js` reads a token getter and an auth subscription from
 * `window.CourseMateAuth`; this bridge supplies both from the same Clerk provider
 * the rest of CourseJesus uses, so no second authentication system exists and the
 * bearer token is never handed to React through an environment variable.
 */
function AuthBridge() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const clerk = useClerk();
  const [bridgeReady, setBridgeReady] = useState(false);

  useEffect(() => {
    window.CourseMateAuth = {
      getToken: async () => {
        if (isSignedIn) {
          return getToken();
        }
        return getGuestSessionToken(currentApiBase());
      },
      subscribe: (listener) => {
        const addListener = (
          clerk as typeof clerk & {
            addListener?: (handler: () => void) => () => void;
          }
        ).addListener;
        return addListener ? addListener(listener) : () => undefined;
      },
      signIn: () => {
        // The signed-out login card only exists inside the new shell document,
        // and the shell is the default entry at `/`, so after sign-in Clerk must
        // land back on the new dashboard rather than any legacy route.
        void clerk.openSignIn({
          fallbackRedirectUrl: `${window.location.origin}/`,
        });
      },
      signOut: async () => {
        await clerk.signOut();
        clearGuestSession(currentApiBase());
      },
      canSignIn: true,
    };
    setBridgeReady(true);
    return () => {
      delete window.CourseMateAuth;
    };
  }, [clerk, getToken, isSignedIn]);

  return bridgeReady && isLoaded ? <UiLocaleProvider><CourseMateApp /></UiLocaleProvider> : null;
}

export function CourseMateUi() {
  const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
  if (testToken) {
    return <TestAuthBridge token={testToken} />;
  }
  if (!publishableKey) {
    return <GuestOnlyAuthBridge />;
  }
  return (
    <ClerkProvider publishableKey={publishableKey}>
      <AuthBridge />
    </ClerkProvider>
  );
}

export default CourseMateUi;
