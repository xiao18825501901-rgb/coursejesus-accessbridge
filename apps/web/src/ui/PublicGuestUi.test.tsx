import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App.jsx";

function guestApp(state: Record<string, unknown> = {}) {
  const app = new App({}) as any;
  app.state = {
    ...app.state,
    loading: false,
    error: "",
    config: {
      auth_mode: "injected",
      environment: "production",
      guest_sessions_enabled: true,
    },
    user: {
      id: "guest_public",
      name: "公开访客",
      handle: "public-guest",
      is_guest: true,
    },
    courses: [
      {
        id: "public-course",
        code: "PUBLIC",
        name: "Authorized Public Course",
        pinned: false,
        color: "#38585b",
      },
    ],
    route: { page: "dashboard", cid: "", tab: "" },
    drawer: null,
    theme: "light",
    ...state,
  };
  app.canvasImport = vi.fn();
  app.createCourse = vi.fn();
  app.profile = vi.fn();
  return app;
}

afterEach(() => {
  delete window.CourseMateAuth;
  window.location.hash = "";
  vi.restoreAllMocks();
});

describe("public visitor controls", () => {
  it("shows public courses on the dashboard without create, import, pin or discussion actions", () => {
    const app = guestApp();
    const view = render(app.renderDashboard());
    const actions = screen.getByRole("group", { name: "课程操作" });

    expect(within(actions).getAllByRole("button").map(button => button.textContent?.trim()))
      .toEqual(["进入所有课程"]);
    expect(screen.getByText("Authorized Public Course")).toBeVisible();
    expect(screen.getByText(/公开访客可浏览已授权课程/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "创建自己的课程" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "从 Canvas 导入" })).not.toBeInTheDocument();
    expect(view.container.querySelector(".course-card-menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /评论/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /文件/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /学习/ })).toBeVisible();
  });

  it("removes private-workspace navigation while preserving public learning routes", () => {
    const app = guestApp();
    render(app.renderNav());
    const nav = screen.getByRole("navigation", { name: "主导航" });

    expect(within(nav).getByRole("button", { name: /控制面板/ })).toBeVisible();
    expect(within(nav).getByRole("button", { name: /学习/ })).toBeVisible();
    expect(within(nav).getByRole("button", { name: /课程/ })).toBeVisible();
    expect(within(nav).getByRole("button", { name: /帮助/ })).toBeVisible();
    expect(within(nav).queryByRole("button", { name: /日历/ })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("button", { name: /收件箱/ })).not.toBeInTheDocument();
    expect(screen.getByText("公开访客")).toBeVisible();
  });

  it("keeps the authorized course catalogue but removes management columns and actions", () => {
    const app = guestApp({ route: { page: "courses", cid: "", tab: "" } });
    const view = render(app.renderCourses());

    expect(screen.getByText("Authorized Public Course")).toBeVisible();
    expect(screen.getByText(/公开访客可浏览已授权课程/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "创建课程" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "从 Canvas 导入" })).not.toBeInTheDocument();
    expect(view.container.querySelector(".add-toggle")).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "控制面板" })).not.toBeInTheDocument();
  });

  it("uses the account drawer only for public identity, language and optional sign-in", () => {
    const app = guestApp({ drawer: "account" });
    window.CourseMateAuth = {
      getToken: vi.fn(async () => "guest-token"),
      subscribe: vi.fn(() => () => undefined),
      signIn: vi.fn(),
      signOut: vi.fn(async () => undefined),
      canSignIn: true,
    };

    render(app.renderDrawer());
    const drawer = screen.getByRole("dialog", { name: "账户面板" });

    expect(within(drawer).getByText("公开访客")).toBeVisible();
    expect(within(drawer).getByRole("button", { name: "登录" })).toBeVisible();
    expect(within(drawer).queryByRole("button", { name: "退出登录" })).not.toBeInTheDocument();
    expect(within(drawer).queryByText("个人资料")).not.toBeInTheDocument();
    expect(within(drawer).queryByText("设置")).not.toBeInTheDocument();
    expect(within(drawer).queryByText("通知")).not.toBeInTheDocument();

    fireEvent.click(within(drawer).getByRole("button", { name: "登录" }));
    expect(window.CourseMateAuth.signIn).toHaveBeenCalledOnce();
  });
});
