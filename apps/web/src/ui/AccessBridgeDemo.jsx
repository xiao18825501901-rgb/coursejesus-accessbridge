import React from "react";
import {
  LanguageControl,
  UiLocaleContext,
  defaultUiTranslate,
} from "./UiLocale";
import bfsDfs from "../competition/lessons/bfs-dfs.json";
import matrixTransform from "../competition/lessons/matrix-transform.json";
import stackQueue from "../competition/lessons/stack-queue.json";
import { AccessBridgeDiagram } from "./AccessBridgeDiagram";

const LESSONS = [stackQueue, bfsDfs, matrixTransform];

const TEXT = {
  "zh-CN": {
    eyebrow: "AccessED 公开学习示例",
    title: "AccessBridge 分步学习",
    intro:
      "三节原创合成微课展示确定性图示、文字等价内容、来源展开、短练习与离线导出。页面明确区分赛期示例与正式课程成绩。",
    chooseLesson: "选择微课",
    step: "步骤",
    sources: "来源与授权",
    sourceExcerpt: "教材等价原文",
    glossary: "术语表",
    practice: "短练习",
    practiceHint: "先独立作答，再查看反馈。练习不会写入 W3C 认证、正式成绩或 LEARNED 权威记录。",
    check: "检查答案",
    complete: "请先完成三道练习。",
    correct: "回答正确",
    incorrect: "再想一想",
    download: "下载当前课离线练习",
    offlineNote: "离线包只含当前已导出的讲解、答案与反馈，不提供离线 AI。",
    visualOrder: "访问顺序",
    matrixOrder: "本例执行顺序",
    bfsLabel: "BFS",
    dfsLabel: "DFS（A 先考察 B）",
    matrixResult: "本例 p′ = T R S p：",
    matrixReverse: "反序 p″ = S R T p：",
    stackResult: "压入 A、B、C 后，栈顶为 C；入队 A、B、C 后，队首为 A。",
    sourceRights: "赛期原创合成文本；不含学校、课程或学习者记录。",
    largeText: "大字",
    normalText: "标准字号",
  },
  en: {
    eyebrow: "AccessED public learning demo",
    title: "AccessBridge stepped learning",
    intro:
      "Three original synthetic micro-lessons show deterministic visuals, text equivalents, expandable sources, short practice, and offline export. This demo is separate from formal grades.",
    chooseLesson: "Choose a lesson",
    step: "Step",
    sources: "Sources and rights",
    sourceExcerpt: "Text-equivalent source",
    glossary: "Glossary",
    practice: "Short practice",
    practiceHint: "Answer independently before reading feedback. Practice never changes a certification, formal grade, or the LEARNED authority record.",
    check: "Check answers",
    complete: "Complete all three questions first.",
    correct: "Correct",
    incorrect: "Try again",
    download: "Download this offline practice",
    offlineNote: "The offline file contains only the exported lesson, answers, and feedback. It does not provide offline AI.",
    visualOrder: "Visit order",
    matrixOrder: "Example execution order",
    bfsLabel: "BFS",
    dfsLabel: "DFS (A considers B before C)",
    matrixResult: "This example, p′ = T R S p:",
    matrixReverse: "Reversed order, p″ = S R T p:",
    stackResult: "After pushes A, B, C, the stack top is C. After enqueues A, B, C, the queue front is A.",
    sourceRights: "Original synthetic competition text; it contains no school, course, or learner records.",
    largeText: "Large text",
    normalText: "Standard text",
  },
};

function localized(value, locale) {
  return value[locale === "en" ? "en" : "zh"];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function buildOfflineHtml(lesson, locale, copy, largeText = false) {
  const title = localized(lesson.title, locale);
  const steps = lesson.steps.map((step) => `
    <section><h2>${escapeHtml(localized(step.title, locale))}</h2><p>${escapeHtml(localized(step.body, locale))}</p></section>`).join("");
  const quiz = lesson.quiz.map((question, index) => `
    <fieldset><legend>${index + 1}. ${escapeHtml(localized(question.prompt, locale))}</legend>
      ${question.options.map((option, optionIndex) => `<p>${optionIndex === question.answer ? "✓" : "○"} ${escapeHtml(localized(option, locale))}</p>`).join("")}
      <p class="rationale">${escapeHtml(localized(question.rationale, locale))}</p>
    </fieldset>`).join("");
  return `<!doctype html>
<html lang="${locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(title)} · CourseJesus AccessBridge</title>
<style>body{font:${largeText ? "22px" : "18px"}/1.65 system-ui,sans-serif;max-width:850px;margin:auto;padding:32px;color:#243844;overflow-wrap:anywhere}h1{color:#8f1c4c}h2{margin-top:32px}.rationale{padding:12px;background:#f6f8fa;border-left:4px solid #8f1c4c}fieldset{margin:24px 0;padding:18px;border:1px solid #d8e0e5}legend{font-weight:700}.notice{padding:16px;background:#fff7e6;border:1px solid #ead39c}@media(max-width:520px){body{padding:20px}}</style></head>
<body><main><p>${escapeHtml(copy.eyebrow)}</p><h1>${escapeHtml(title)}</h1><p>${escapeHtml(localized(lesson.concept, locale))}</p>
<p class="notice">${escapeHtml(copy.offlineNote)}</p>
<h2>${escapeHtml(copy.sourceExcerpt)}</h2><p>${escapeHtml(localized(lesson.original_source_excerpt, locale))}</p>
${steps}<h2>${escapeHtml(copy.practice)}</h2>${quiz}
<h2>${escapeHtml(copy.sources)}</h2>${lesson.sources.map((source) => `<p><strong>${escapeHtml(source.id)}</strong> ${escapeHtml(localized(source.text, locale))}</p>`).join("")}
</main></body></html>`;
}

export class AccessBridgeDemo extends React.Component {
  static contextType = UiLocaleContext;
  state = {
    lessonId: "bfs-dfs",
    answers: {},
    checked: false,
    incomplete: false,
    largeText: false,
  };

  componentDidMount() {
    this.locale = this.context?.locale || "zh-CN";
  }

  componentDidUpdate() {
    const locale = this.context?.locale || "zh-CN";
    if (this.locale && locale !== this.locale) {
      this.locale = locale;
      if (this.state.checked || this.state.incomplete) {
        this.setState({ checked: false, incomplete: false });
      }
      return;
    }
    this.locale = locale;
  }

  copy() {
    return TEXT[this.context?.locale === "en" ? "en" : "zh-CN"];
  }

  selectLesson(lessonId) {
    this.setState({ lessonId, answers: {}, checked: false, incomplete: false });
  }

  answer(questionId, value) {
    this.setState((state) => ({ answers: { ...state.answers, [questionId]: Number(value) }, incomplete: false }));
  }

  check(lesson) {
    if (lesson.quiz.some((question) => this.state.answers[question.id] === undefined)) {
      this.setState({ incomplete: true, checked: false });
      return;
    }
    this.setState({ checked: true, incomplete: false });
  }

  download(lesson) {
    const locale = this.context?.locale === "en" ? "en" : "zh-CN";
    const copy = this.copy();
    const content = buildOfflineHtml(lesson, locale, copy, this.state.largeText);
    const url = URL.createObjectURL(new Blob([content], { type: "text/html;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `AccessBridge_${lesson.lesson_id}_${locale}.html`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  render() {
    const locale = this.context?.locale === "en" ? "en" : "zh-CN";
    const t = this.context?.t || defaultUiTranslate;
    const copy = this.copy();
    const lesson = LESSONS.find((entry) => entry.lesson_id === this.state.lessonId) || LESSONS[1];
    const correctCount = lesson.quiz.filter((question) => this.state.answers[question.id] === question.answer).length;
    return <main className={`page accessbridge-page ${this.state.largeText ? "accessbridge-large-text" : ""}`}>
      <header className="accessbridge-hero">
        <div><p className="accessbridge-eyebrow">{copy.eyebrow}</p><h1>{copy.title}</h1><p>{copy.intro}</p></div>
        <div className="accessbridge-hero-actions">
          <div className="accessbridge-badge" aria-label={locale === "en" ? "Deterministic and offline-ready" : "确定性与可离线"}>
            <strong>SVG</strong><span>{locale === "en" ? "Deterministic visual" : "确定性图示"}</span>
          </div>
          <LanguageControl />
          <button
            type="button"
            className="accessbridge-text-toggle"
            aria-pressed={this.state.largeText}
            onClick={() => this.setState((state) => ({ largeText: !state.largeText }))}
          >
            {this.state.largeText ? copy.normalText : copy.largeText}
          </button>
        </div>
      </header>
      <div className="accessbridge-layout">
        <aside className="accessbridge-lessons" aria-label={copy.chooseLesson}>
          <h2>{copy.chooseLesson}</h2>
          {LESSONS.map((entry, index) => <button type="button" key={entry.lesson_id}
            className={entry.lesson_id === lesson.lesson_id ? "active" : ""}
            aria-pressed={entry.lesson_id === lesson.lesson_id}
            onClick={() => this.selectLesson(entry.lesson_id)}>
            <span>{String(index + 1).padStart(2, "0")}</span>{localized(entry.title, locale)}
          </button>)}
        </aside>
        <article className="accessbridge-lesson" aria-labelledby="accessbridge-lesson-title">
          <header>
            <p>{localized(lesson.concept, locale)}</p>
            <h2 id="accessbridge-lesson-title">{localized(lesson.title, locale)}</h2>
            <p>{localized(lesson.original_source_excerpt, locale)}</p>
          </header>
          <section className="accessbridge-visual" aria-label={locale === "en" ? "Visual explanation" : "图示解释"}>
            <AccessBridgeDiagram lesson={lesson} locale={locale} copy={copy}/>
          </section>
          <section className="accessbridge-steps">
            {lesson.steps.map((step, index) => <div key={step.id}>
              <span className="accessbridge-step-number">{copy.step} {index + 1}</span>
              <div><h3>{localized(step.title, locale)}</h3><p>{localized(step.body, locale)}</p>
                <details><summary>{locale === "en" ? "Source" : "查看来源"} {step.source_id}</summary>
                  <p>{localized(lesson.sources.find((source) => source.id === step.source_id)?.text || lesson.original_source_excerpt, locale)}</p></details></div>
            </div>)}
          </section>
          <details className="accessbridge-sources"><summary>{copy.sources}</summary>
            {lesson.sources.map((source) => <div key={source.id}><strong>{source.id}</strong><h3>{localized(source.title, locale)}</h3>
              <p>{localized(source.text, locale)}</p><small>{copy.sourceRights}</small></div>)}
          </details>
          <section className="accessbridge-glossary"><h2>{copy.glossary}</h2>
            <dl>{lesson.glossary.map((entry) => <div key={localized(entry.term, locale)}><dt>{localized(entry.term, locale)}</dt><dd>{localized(entry.definition, locale)}</dd></div>)}</dl>
          </section>
          <section className="accessbridge-practice" aria-labelledby="accessbridge-practice-title">
            <div className="accessbridge-practice-head"><div><h2 id="accessbridge-practice-title">{copy.practice}</h2><p id="accessbridge-practice-hint">{copy.practiceHint}</p></div>
              {this.state.checked && <strong role="status">{correctCount} / {lesson.quiz.length}</strong>}
            </div>
            {lesson.quiz.map((question, index) => <fieldset key={question.id}>
              <legend>{index + 1}. {localized(question.prompt, locale)}</legend>
              {question.options.map((option, optionIndex) => <label key={optionIndex} className={this.state.answers[question.id] === optionIndex ? "selected" : ""}>
                <input type="radio" name={`${lesson.lesson_id}-${question.id}`} value={optionIndex}
                  checked={this.state.answers[question.id] === optionIndex}
                  onChange={(event) => this.answer(question.id, event.target.value)}/>
                <span>{localized(option, locale)}</span>
              </label>)}
              {this.state.checked && <p role="status" className={this.state.answers[question.id] === question.answer ? "correct" : "incorrect"}>
                <strong>{this.state.answers[question.id] === question.answer ? copy.correct : copy.incorrect}.</strong>{" "}
                {localized(question.rationale, locale)}
              </p>}
            </fieldset>)}
            {this.state.incomplete && <p role="alert" className="accessbridge-alert">{copy.complete}</p>}
            <div className="accessbridge-actions">
              <button type="button" className="btn primary" onClick={() => this.check(lesson)}>{copy.check}</button>
              <button type="button" className="btn" onClick={() => this.download(lesson)}>{copy.download}</button>
              <p>{copy.offlineNote}</p>
            </div>
          </section>
          <p className="accessbridge-fingerprint">{lesson.source_reference} · {t("accessbridge.deterministicNote")}</p>
        </article>
      </div>
    </main>;
  }
}
