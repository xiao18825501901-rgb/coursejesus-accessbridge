import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AccessBridgeDemo } from "./ui/AccessBridgeDemo.jsx";
import { UiLocaleProvider } from "./ui/UiLocale";

import "./ui/styles.css";
import "./ui/styles-extra.css";
import "./ui/theme.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("AccessBridge root element was not found.");
}

createRoot(container).render(
  <StrictMode>
    <UiLocaleProvider>
      <div className="accessbridge-public-shell">
        <aside className="accessbridge-public-boundary" aria-label="Demo boundary">
          <strong>Public judging demo</strong>
          <span>
            Uses the same deterministic learning component as the complete
            CourseJesus competition build. No account, private learner data,
            production model, or GPU is required.
          </span>
          <a href="https://github.com/xiao18825501901-rgb/coursejesus-accessbridge">
            Source and local run instructions
          </a>
        </aside>
        <AccessBridgeDemo />
      </div>
    </UiLocaleProvider>
  </StrictMode>,
);
