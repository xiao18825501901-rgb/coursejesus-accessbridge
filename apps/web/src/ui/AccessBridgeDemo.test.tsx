import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import bfsDfs from "../competition/lessons/bfs-dfs.json";
import matrixTransform from "../competition/lessons/matrix-transform.json";
import stackQueue from "../competition/lessons/stack-queue.json";
import {
  graphBfsOrder,
  graphDfsOrder,
  matrixTransformExample,
} from "../competition/lessonLogic";
import {
  AccessBridgeDemo,
  buildOfflineHtml,
} from "./AccessBridgeDemo";
import { UiLocaleProvider } from "./UiLocale";

const lessons = [stackQueue, bfsDfs, matrixTransform];

const offlineCopy = {
  eyebrow: "AccessED public learning demo",
  sourceExcerpt: "Text-equivalent source",
  practice: "Short practice",
  sources: "Sources and rights",
  offlineNote:
    "The offline file contains only the exported lesson, answers, and feedback. It does not provide offline AI.",
};

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("reviewed lesson content", () => {
  it("computes BFS from the graph instead of trusting the answer index", () => {
    expect(graphBfsOrder(bfsDfs)).toEqual(["a", "b", "c", "d", "e"]);
    const bfsQuestion = bfsDfs.quiz[1]!;
    expect(bfsQuestion.options[bfsQuestion.answer]!.en).toBe(
      "A, B, C, D, E",
    );
  });

  it("computes the DFS prefix from alphabetical neighbour order", () => {
    expect(graphDfsOrder(bfsDfs)).toEqual(["a", "b", "d", "c", "e"]);
    const dfsQuestion = bfsDfs.quiz[2]!;
    expect(dfsQuestion.options[dfsQuestion.answer]!.en).toBe("A, B, D");
  });

  it("uses homogeneous column vectors and distinguishes TRS from reversed order", () => {
    const result = matrixTransformExample();
    expect(result.forwardStages).toEqual([
      [1, 0, 1],
      [2, 0, 1],
      [0, 2, 1],
      [1, 3, 1],
    ]);
    expect(result.reverseStages).toEqual([
      [1, 0, 1],
      [2, 1, 1],
      [-1, 2, 1],
      [-2, 4, 1],
    ]);
    expect(matrixTransform.quiz[1]!.options[matrixTransform.quiz[1]!.answer]!.en)
      .toBe("(1,3)");
    expect(matrixTransform.quiz[2]!.options[matrixTransform.quiz[2]!.answer]!.en)
      .toBe("(-2,4)");
  });

  it("keeps exactly three grounded bilingual questions with rationales", () => {
    for (const lesson of lessons) {
      const sourceIds = new Set(lesson.sources.map((source) => source.id));
      expect(lesson.quiz).toHaveLength(3);
      for (const question of lesson.quiz) {
        expect(question.answer).toBeGreaterThanOrEqual(0);
        expect(question.answer).toBeLessThan(question.options.length);
        expect(question.prompt.en).toBeTruthy();
        expect(question.prompt.zh).toBeTruthy();
        expect(question.rationale.en).toBeTruthy();
        expect(question.rationale.zh).toBeTruthy();
        expect(sourceIds.has(question.source_id)).toBe(true);
      }
      for (const step of lesson.steps) {
        expect(sourceIds.has(step.source_id)).toBe(true);
      }
    }
  });
});

describe("AccessBridge interaction", () => {
  it("switches language, clears stale feedback, and supports large text", () => {
    render(
      <UiLocaleProvider>
        <AccessBridgeDemo />
      </UiLocaleProvider>,
    );

    fireEvent.click(screen.getByRole("radio", { name: "B 和 C" }));
    fireEvent.click(screen.getByRole("radio", { name: "A、B、C、D、E" }));
    fireEvent.click(screen.getByRole("radio", { name: "A、B、D" }));
    fireEvent.click(screen.getByRole("button", { name: "检查答案" }));
    expect(screen.getAllByText(/回答正确/)).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "AccessBridge stepped learning",
      }),
    ).toBeVisible();
    expect(screen.queryByText(/回答正确/)).not.toBeInTheDocument();
    expect(screen.queryByText(/The graph shows A to B/)).not.toBeInTheDocument();

    const largeText = screen.getByRole("button", { name: "Large text" });
    fireEvent.click(largeText);
    expect(largeText).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("main")).toHaveClass("accessbridge-large-text");
  });

  it("keeps source disclosure keyboard-operable and feedback intentionally gated", () => {
    render(
      <UiLocaleProvider>
        <AccessBridgeDemo />
      </UiLocaleProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "检查答案" }));
    expect(screen.getByRole("alert")).toHaveTextContent("请先完成三道练习");

    const source = screen.getAllByText(/查看来源 AB-S1/)[0]!;
    fireEvent.click(source);
    expect(source.closest("details")).toHaveAttribute("open");
    expect(source.closest("details")?.querySelector("p")).toBeVisible();
  });

  it("creates a self-contained offline practice with the same lesson and answers", () => {
    const html = buildOfflineHtml(
      matrixTransform,
      "en",
      offlineCopy,
      true,
    );

    expect(html).toContain("Matrix transforms");
    expect(html).toContain("font:22px/1.65");
    expect(html).toContain("1. After scaling");
    expect(html).toContain("✓ (0,2)");
    expect(html).toContain("(-2,4)");
    expect(html).toContain("does not provide offline AI");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("https://");
    expect(html).not.toContain("fetch(");
  });
});
