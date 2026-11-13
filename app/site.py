from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.lessons import AccessLesson, LocalizedText, load_lessons
from app.offline_export import build_learning_pack
from app.offline_pack import render as render_offline_pack
from app.visual.compiler import CompiledVisual, compile_visual
from app.visual.router import route_visual


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _localized(value: LocalizedText | dict) -> LocalizedText:
    if isinstance(value, LocalizedText):
        return value
    if hasattr(value, "en") and hasattr(value, "zh"):
        return LocalizedText(en=value.en, zh=value.zh)
    return LocalizedText.model_validate(value)


def _localized_span(value: LocalizedText | dict) -> str:
    locale = _localized(value)
    en = _escape(locale.en)
    zh = _escape(locale.zh)
    return f'<span data-en="{en}" data-zh="{zh}">{en}</span>'


def _render_step(step, number: int) -> str:
    return (
        '<article class="step">'
        f'<p class="step-number" aria-hidden="true">{number:02d}</p>'
        f"<h3>{_localized_span(step.title)}</h3>"
        f"<p>{_localized_span(step.body)}</p>"
        '<p class="source-line"><span class="label" data-en="Source" data-zh="来源">Source</span> '
        f'<code>{_escape(step.source_id)}</code></p>'
        "</article>"
    )


def _render_quiz(lesson: AccessLesson) -> str:
    blocks: list[str] = []
    for index, question in enumerate(lesson.quiz, start=1):
        feedback_id = f"{lesson.lesson_id}-feedback-{index}"
        options = []
        for option_index, option in enumerate(question.options):
            locale = _localized(option)
            options.append(
                '<label class="quiz-option"><input type="radio" '
                f'name="{lesson.lesson_id}-q{index}" value="{option_index}" '
                f'aria-describedby="{feedback_id}"> '
                f'<span data-en="{_escape(locale.en)}" data-zh="{_escape(locale.zh)}">'
                f"{_escape(locale.en)}</span></label>"
            )
        rationale = _localized(question.rationale)
        blocks.append(
            '<fieldset class="quiz-question">'
            f"<legend>{index}. {_localized_span(question.prompt)}</legend>"
            f"{''.join(options)}"
            '<button type="button" class="check-answer" '
            f'data-lesson="{lesson.lesson_id}">'
            '<span data-en="Check answer" data-zh="检查答案">Check answer</span></button>'
            f'<p class="quiz-feedback" id="{feedback_id}" role="status" aria-live="polite" '
            f'data-answer="{question.answer}" '
            f'data-rationale-en="{_escape(rationale.en)}" '
            f'data-rationale-zh="{_escape(rationale.zh)}" '
            f'data-source="{_escape(question.source_id)}"></p>'
            "</fieldset>"
        )
    return "".join(blocks)


def _render_visual(lesson: AccessLesson) -> CompiledVisual:
    route_visual(lesson.visual_spec)
    return compile_visual(
        lesson.visual_spec,
        alt_text=lesson.alt_text.en,
        long_description=lesson.long_description.en,
        alt_text_zh=lesson.alt_text.zh,
        long_description_zh=lesson.long_description.zh,
    )


def _page(title: str, body: str, *, skip_link: bool = True) -> str:
    skip = '<a class="skip-link" href="#main">Skip to content</a>' if skip_link else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; "
        "img-src data:; form-action 'none'; base-uri 'none'\">"
        f"<title>{_escape(title)}</title><style>"
        ":root{color-scheme:light;--ink:#0f172a;--muted:#475467;--paper:#fcfdff;"
        "--panel:#f7f9fc;--panel-strong:#eef4ff;--line:#cfd8e3;--accent:#174ea6;"
        "--accent-ink:#0d367c;--focus:#7a1fa2;--ok:#0f6b54;--bad:#a32017;"
        "--radius:16px;--shadow:0 12px 32px rgba(15,23,42,.08)}"
        "*,*::before,*::after{box-sizing:border-box}html{scroll-behavior:smooth}"
        "body{margin:0;background:var(--paper);color:var(--ink);"
        "font:18px/1.7 system-ui,sans-serif;-webkit-font-smoothing:antialiased}"
        "body.large-text{font-size:22px}.skip-link{position:fixed;left:1rem;top:-100px;"
        "background:#fff;padding:.75rem 1rem;border:2px solid var(--accent);z-index:20}"
        ".skip-link:focus{top:1rem}.shell{width:min(1040px,100%);margin:auto;padding:0 20px}"
        "header.site-header{border-bottom:1px solid var(--line);background:rgba(255,255,255,.94)}"
        ".header-row{display:flex;align-items:center;justify-content:space-between;gap:16px;"
        "padding:18px 0;flex-wrap:wrap}.brand{font-weight:850;letter-spacing:-.02em;color:var(--ink);"
        "text-decoration:none}.brand-mark{display:inline-grid;place-items:center;width:34px;height:34px;"
        "margin-right:8px;border-radius:10px;background:var(--ink);color:#fff;font-size:.85rem}"
        ".header-controls{display:flex;gap:8px;flex-wrap:wrap}button,select,input,label{font:inherit}"
        "button{min-height:44px;border:2px solid var(--accent);border-radius:999px;background:#fff;"
        "color:var(--accent-ink);padding:.5rem 1rem;cursor:pointer}button:hover{background:var(--panel-strong)}"
        "button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible{"
        "outline:3px solid var(--focus);outline-offset:3px}a{color:var(--accent-ink)}"
        "main{padding:38px 0 48px}.hero{display:grid;grid-template-columns:minmax(0,1.5fr) "
        "minmax(240px,.75fr);gap:30px;align-items:start;padding:12px 0 30px}"
        ".eyebrow{font-size:.77rem;font-weight:850;letter-spacing:.13em;text-transform:uppercase;"
        "color:var(--accent);margin:0 0 8px}h1,h2,h3{line-height:1.16;letter-spacing:-.025em}"
        "h1{font-size:clamp(2.15rem,6vw,4.25rem);margin:.15em 0 .3em;max-width:14ch}"
        "h2{font-size:clamp(1.45rem,3vw,2rem);margin:2.2rem 0 .8rem}h3{font-size:1.15rem;margin:.2rem 0}"
        "p{max-width:76ch}.lede{font-size:1.12em;color:var(--muted);max-width:55ch}"
        ".hero-card{border:1px solid var(--line);border-radius:var(--radius);padding:20px;"
        "background:linear-gradient(145deg,#fff,var(--panel-strong));box-shadow:var(--shadow)}"
        ".status-dot{display:inline-block;width:9px;height:9px;border-radius:50%;"
        "background:var(--ok);margin-right:7px}.status-list{list-style:none;padding:0;margin:12px 0 0}"
        ".status-list li{padding:.35rem 0;border-top:1px solid #dbe5f5}.status-list li:first-child{border-top:0}"
        ".lesson-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}"
        ".lesson-card{display:flex;flex-direction:column;gap:8px;border:1px solid var(--line);"
        "border-radius:var(--radius);padding:22px;background:#fff;box-shadow:0 4px 16px rgba(15,23,42,.04)}"
        ".lesson-card h2{font-size:1.35rem;margin:0}.lesson-card p{margin:.15rem 0}"
        ".lesson-card .card-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px}"
        "a.button-link{display:inline-flex;align-items:center;justify-content:center;"
        "min-height:44px;padding:.48rem 1rem;border-radius:999px;text-decoration:none;"
        "font-weight:750}.button-primary{background:var(--ink);color:#fff}.button-secondary{"
        "border:2px solid var(--accent);color:var(--accent-ink)}"
        ".flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;"
        "padding:0;list-style:none}.flow li{background:var(--panel);border:1px solid var(--line);"
        "border-radius:12px;padding:14px}.flow strong{display:block}.note{border-left:4px solid "
        "var(--accent);padding:.8rem 1rem;background:var(--panel-strong);border-radius:0 12px 12px 0}"
        ".lesson-header{padding-bottom:24px;border-bottom:1px solid var(--line)}.lesson-nav{"
        "display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.meta-row{display:flex;"
        "flex-wrap:wrap;gap:8px 18px;color:var(--muted);font-size:.92rem;margin-top:12px}"
        ".section-intro{color:var(--muted);margin-top:-.2rem}figure{margin:18px 0;border:1px solid "
        "var(--line);border-radius:var(--radius);padding:16px;background:var(--panel)}"
        "figure svg{display:block;width:100%;height:auto}figcaption{font-size:.92rem;color:var(--muted);"
        "margin-top:10px}.steps{display:grid;gap:14px}.step{position:relative;border:1px solid var(--line);"
        "border-radius:var(--radius);padding:20px 20px 16px;background:#fff}.step-number{font-size:.8rem;"
        "font-weight:850;color:var(--accent);letter-spacing:.1em;margin:0}.source-line{font-size:.88rem;"
        "color:var(--muted)}.label{font-weight:750;color:var(--muted)}details{border:1px solid var(--line);"
        "border-radius:12px;padding:.8rem 1rem;margin:.65rem 0;background:#fff}summary{cursor:pointer;"
        "font-weight:650}.glossary{display:grid;gap:4px}.quiz-question{border:1px solid var(--line);"
        "border-radius:var(--radius);padding:18px;margin:16px 0;background:#fff}legend{padding:0 .4rem;"
        "font-weight:800}.quiz-option{display:block;margin:.5rem 0;padding:.45rem .55rem;cursor:pointer;"
        "border-radius:10px}.quiz-option:hover{background:var(--panel)}.quiz-option input{margin-right:"
        ".7rem;min-width:1.2rem;min-height:1.2rem;accent-color:var(--accent)}.quiz-feedback{font-weight:700;"
        "margin:.7rem 0 0;min-height:1.7em}.quiz-feedback.correct{color:var(--ok)}"
        ".quiz-feedback.incorrect{color:var(--bad)}.footer-grid{display:flex;justify-content:space-between;"
        "gap:16px;flex-wrap:wrap;border-top:1px solid var(--line);padding:24px 0 40px;color:var(--muted);"
        "font-size:.9rem}footer a{color:var(--muted)}code{overflow-wrap:anywhere}"
        "@media(max-width:760px){.hero{grid-template-columns:1fr}.header-row{align-items:flex-start}"
        "main{padding-top:24px}h1{max-width:18ch}.lesson-card{padding:18px}}"
        "@media(max-width:460px){.shell{padding:0 14px}button{padding:.48rem .8rem}"
        "figure,.step,.quiz-question{padding:14px}.footer-grid{display:block}}"
        "@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}"
        "</style></head><body>"
        + skip
        + body
        + "</body></html>"
    )


def _header_controls(*, offline_link: str | None = None) -> str:
    link = (
        f'<a class="button-secondary button-link" download href="{offline_link}">'
        '<span data-en="Open offline pack" data-zh="打开离线学习包">Open offline pack</span></a>'
        if offline_link
        else ""
    )
    return (
        '<header class="site-header"><div class="shell header-row">'
        '<a class="brand" href="../index.html">'
        '<span class="brand-mark" aria-hidden="true">AB</span>CourseJesus · AccessBridge</a>'
        '<nav class="header-controls" aria-label="Reading controls">'
        '<button type="button" id="toggle-language">'
        '<span data-en="中文" data-zh="English">中文</span></button>'
        '<button type="button" id="toggle-size" aria-pressed="false">'
        '<span data-en="Larger text" data-zh="大字">Larger text</span></button>'
        f"{link}</nav></div></header>"
    )


def _render_lesson(lesson: AccessLesson, visual: CompiledVisual, *, lesson_number: int) -> str:
    body = [
        _header_controls(offline_link=f"../offline/{lesson.lesson_id}.html"),
        '<main id="main"><div class="shell">',
        '<div class="lesson-header">',
        f'<p class="eyebrow">Lesson {lesson_number} of 3</p>',
        f"<h1>{_localized_span(lesson.title)}</h1>",
        f'<p class="lede">{_localized_span(lesson.concept)}</p>',
        '<div class="meta-row"><span data-en="Deterministic visuals" '
        'data-zh="确定性图形">Deterministic visuals</span><span data-en="Keyboard ready" '
        'data-zh="键盘可用">Keyboard ready</span><span data-en="Practice only" '
        'data-zh="仅练习">Practice only</span></div>',
        '<nav class="lesson-nav" aria-label="Lesson sections">'
        '<a href="#lesson-steps"><span data-en="Steps" data-zh="步骤">Steps</span></a>'
        '<a href="#visual-section"><span data-en="Visual" data-zh="图形">Visual</span></a>'
        '<a href="#glossary"><span data-en="Terms" data-zh="术语">Terms</span></a>'
        '<a href="#quiz"><span data-en="Practice" data-zh="练习">Practice</span></a>'
        '<a href="#sources"><span data-en="Sources" data-zh="来源">Sources</span></a></nav>',
        "</div>",
        '<section aria-labelledby="lesson-steps"><h2 id="lesson-steps">'
        '<span data-en="Understand one step at a time" data-zh="一步一步理解">'
        "Understand one step at a time</span></h2>"
        '<p class="section-intro"><span data-en="Read one idea, then continue. '
        'Every step keeps its source visible." data-zh="每次读一个观点，再继续；每一步都保留来源。">'
        "Read one idea, then continue. Every step keeps its source visible.</span></p>"
        '<div class="steps">'
        + "".join(_render_step(step, index) for index, step in enumerate(lesson.steps, start=1))
        + '</div><div class="note"><strong><span data-en="Source excerpt:" '
        'data-zh="来源摘录：">Source excerpt:</span></strong> '
        + _localized_span(lesson.original_source_excerpt)
        + "</div></section>",
        '<section aria-labelledby="visual-section"><h2 id="visual-section">'
        '<span data-en="See the relationship" data-zh="查看关系">See the relationship</span></h2>'
        '<p class="section-intro"><span data-en="The SVG has a text equivalent and never relies '
        'on color alone." data-zh="SVG 配有文字等价内容，不会只依赖颜色。">'
        "The SVG has a text equivalent and never relies on color alone.</span></p><figure>"
        + visual.svg
        + '<figcaption><strong><span data-en="Long description:" data-zh="文字说明：">'
        "Long description:</span></strong> "
        + _localized_span(lesson.long_description)
        + "</figcaption></figure></section>",
        '<section aria-labelledby="glossary"><h2 id="glossary">'
        '<span data-en="Key terms" data-zh="关键术语">Key terms</span></h2><div class="glossary">'
        + "".join(
            f"<details><summary>{_localized_span(entry.term)}</summary>"
            f"<p>{_localized_span(entry.definition)}</p></details>"
            for entry in lesson.glossary
        )
        + "</div></section>",
        '<section aria-labelledby="quiz"><h2 id="quiz">'
        '<span data-en="Check your understanding" data-zh="检查理解">Check your understanding</span>'
        '</h2><p class="section-intro"><span data-en="Three short practice questions. '
        'Feedback names the source; results are not an official grade." '
        'data-zh="三道短练习；反馈会标明来源；结果不是正式成绩。">'
        "Three short practice questions. Feedback names the source; results are not an official grade."
        "</span></p>" + _render_quiz(lesson) + "</section>",
        '<section aria-labelledby="sources"><h2 id="sources">'
        '<span data-en="Inspect the sources" data-zh="查看来源">Inspect the sources</span></h2>'
        '<p class="section-intro"><span data-en="Open a source to check the rights note and '
        'the claim used in this lesson." data-zh="展开来源，核对授权说明与课程使用的论点。">'
        "Open a source to check the rights note and the claim used in this lesson.</span></p>"
        + "".join(
            f"<details><summary><code>{_escape(source.id)}</code> · "
            f"{_localized_span(source.title)}</summary>"
            f"<p>{_localized_span(source.text)}</p><p class=\"source-line\">"
            f"{_escape(source.rights)}</p></details>"
            for source in lesson.sources
        )
        + '<p class="source-line"><span class="label" data-en="Reference" data-zh="引用">Reference</span> '
        f"{_escape(lesson.source_reference)}</p></section>",
        "</div></main>",
        '<footer><div class="shell footer-grid"><p>CourseJesus — AccessBridge · '
        '<span data-en="Original synthetic lesson." data-zh="原创合成课程。">'
        "Original synthetic lesson.</span><br>"
        '<span data-en="Offline packs contain answers for study and are not an official assessment." '
        'data-zh="离线包含有学习用答案，不是正式测评。">'
        "Offline packs contain answers for study and are not an official assessment.</span></p>"
        '<p><a href="../index.html"><span data-en="All lessons" data-zh="全部课程">'
        "All lessons</span></a></p></div></footer>",
    ]
    body.append(
        "<script>document.addEventListener('click',event=>{"
        "if(event.target.closest('#toggle-language')){"
        "const english=document.documentElement.lang!=='en';"
        "document.documentElement.lang=english?'en':'zh-CN';"
        "document.querySelectorAll('[data-en]').forEach(el=>{"
        "el.textContent=english?el.dataset.en:el.dataset.zh;});}"
        "if(event.target.closest('#toggle-size')){const button=event.target.closest('#toggle-size');"
        "const on=document.body.classList.toggle('large-text');"
        "button.setAttribute('aria-pressed',String(on));}"
        "const button=event.target.closest('.check-answer');if(!button){return;}"
        "const form=button.closest('fieldset');const chosen=form.querySelector('input:checked');"
        "const feedback=form.querySelector('.quiz-feedback');"
        "if(!chosen){feedback.textContent=document.documentElement.lang==='en'?"
        "'Choose an answer first.':'请先选择一个答案。';"
        "feedback.className='quiz-feedback';return;}"
        "const ok=Number(chosen.value)===Number(feedback.dataset.answer);"
        "const phrase=document.documentElement.lang==='en'?"
        "(ok?'Correct. ':'Try again. '):(ok?'正确。':'再试一次。');"
        "const rationale=document.documentElement.lang==='en'?"
        "feedback.dataset.rationaleEn:feedback.dataset.rationaleZh;"
        "const source=document.documentElement.lang==='en'?' Source: ':' 来源：';"
        "feedback.textContent=phrase+rationale+source+feedback.dataset.source;"
        "feedback.className='quiz-feedback '+(ok?'correct':'incorrect');});</script>"
    )
    return _page(f"{lesson.title.en} — CourseJesus AccessBridge", "".join(body))


def _render_index(lessons: list[AccessLesson], visuals: dict[str, CompiledVisual]) -> str:
    cards = []
    for index, lesson in enumerate(lessons, start=1):
        cards.append(
            '<article class="lesson-card">'
            f'<p class="eyebrow">Lesson {index}</p>'
            f'<h2><span data-en="{_escape(lesson.title.en)}" data-zh="{_escape(lesson.title.zh)}">'
            f"{_escape(lesson.title.en)}</span></h2>"
            f'<p><span data-en="{_escape(lesson.concept.en)}" data-zh="{_escape(lesson.concept.zh)}">'
            f"{_escape(lesson.concept.en)}</span></p>"
            f'<p class="source-line">Visual hash: <code>{visuals[lesson.lesson_id].sha256[:12]}</code></p>'
            '<div class="card-actions">'
            f'<a class="button-link button-primary" href="lessons/{lesson.lesson_id}.html">'
            '<span data-en="Start lesson" data-zh="开始学习">Start lesson</span></a>'
            f'<a class="button-link button-secondary" href="offline/{lesson.lesson_id}.html">'
            '<span data-en="Open offline pack" data-zh="打开离线包">Open offline pack</span></a>'
            "</div></article>"
        )
    body = (
        '<header class="site-header"><div class="shell header-row">'
        '<a class="brand" href="index.html">'
        '<span class="brand-mark" aria-hidden="true">AB</span>CourseJesus · AccessBridge</a>'
        '<nav class="header-controls" aria-label="Reading controls">'
        '<button type="button" id="toggle-language">'
        '<span data-en="中文" data-zh="English">中文</span></button>'
        '<button type="button" id="toggle-size" aria-pressed="false">'
        '<span data-en="Larger text" data-zh="大字">Larger text</span></button></nav></div></header>'
        '<main id="main"><div class="shell">'
        '<section class="hero"><div><p class="eyebrow">AccessED Hacks 2026 · Learning access</p>'
        '<h1><span data-en="Complex ideas, one accessible step at a time." '
        'data-zh="复杂概念，一步一步无障碍地学。">'
        "Complex ideas, one accessible step at a time.</span></h1>"
        '<p class="lede"><span data-en="CourseJesus — AccessBridge turns a validated VisualSpec '
        'into a bilingual lesson with an accessible diagram, source trail, and short practice." '
        'data-zh="CourseJesus — AccessBridge 将经过校验的 VisualSpec 转成双语课程，'
        '包含无障碍图形、来源链和短练习。">'
        "CourseJesus — AccessBridge turns a validated VisualSpec into a bilingual lesson with an "
        "accessible diagram, source trail, and short practice.</span></p>"
        '<div class="lesson-nav"><a class="button-link button-primary" href="#lessons">'
        '<span data-en="Choose a lesson" data-zh="选择课程">Choose a lesson</span></a>'
        '<a class="button-link button-secondary" href="#how-it-works">'
        '<span data-en="How it works" data-zh="工作方式">How it works</span></a></div></div>'
        '<aside class="hero-card" aria-label="Demo status"><p class="eyebrow">'
        '<span data-en="Local demo status" data-zh="本地演示状态">Local demo status</span></p>'
        '<p><span class="status-dot" aria-hidden="true"></span><strong>'
        '<span data-en="Ready to explore" data-zh="可立即体验">Ready to explore</span></strong></p>'
        '<ul class="status-list"><li><span data-en="No account required" data-zh="无需账号">'
        'No account required</span></li><li><span data-en="No AI or network request" '
        'data-zh="不调用 AI 或网络">No AI or network request</span></li>'
        '<li><span data-en="Complete single-file offline packs" data-zh="完整单文件离线包">'
        'Complete single-file offline packs</span></li><li>'
        '<span data-en="Practice, not an official grade" data-zh="练习，不是正式成绩">'
        "Practice, not an official grade</span></li></ul>"
        "</aside></section>"
        '<section id="lessons" aria-labelledby="lessons-title"><h2 id="lessons-title">'
        '<span data-en="Three concepts. Three small wins." data-zh="三个概念，三次小进步。">'
        "Three concepts. Three small wins.</span></h2>"
        f'<div class="lesson-grid">{"".join(cards)}</div></section>'
        '<section id="how-it-works" aria-labelledby="how-title"><h2 id="how-title">'
        '<span data-en="A source-first learning path" data-zh="来源优先的学习路径">'
        "A source-first learning path</span></h2>"
        '<ol class="flow"><li><strong><span data-en="1 · Read" data-zh="1 · 阅读">1 · Read</span>'
        '</strong><span data-en="One explanation at a time in English or Chinese." '
        'data-zh="每次阅读一个解释，中英可切换。">'
        "One explanation at a time in English or Chinese.</span></li>"
        '<li><strong><span data-en="2 · Inspect" data-zh="2 · 观察">2 · Inspect</span></strong>'
        '<span data-en="See the deterministic SVG and its text equivalent." '
        'data-zh="查看确定性 SVG 与文字等价内容。">'
        "See the deterministic SVG and its text equivalent.</span></li>"
        '<li><strong><span data-en="3 · Check" data-zh="3 · 检查">3 · Check</span></strong>'
        '<span data-en="Try three questions and trace every answer to a source." '
        'data-zh="完成三道练习，把每个答案追溯到来源。">'
        "Try three questions and trace every answer to a source.</span></li>"
        '<li><strong><span data-en="4 · Keep" data-zh="4 · 保留">4 · Keep</span></strong>'
        '<span data-en="Open a complete offline pack with no network dependency." '
        'data-zh="打开无需网络的完整离线包。">'
        "Open a complete offline pack with no network dependency.</span></li></ol>"
        "</section>"
        '<section aria-labelledby="boundary-title"><h2 id="boundary-title">'
        '<span data-en="What this demo does not claim" data-zh="本演示不声称的内容">'
        "What this demo does not claim</span></h2>"
        '<div class="note"><p><strong><span data-en="Practice is not certification." '
        'data-zh="练习不等于认证。">Practice is not certification.</span></strong> '
        '<span data-en="The app does not write CourseJesus learner scores or the LEARNED authority. '
        'It does not generate video, call a remote model, or present practice as an official course '
        'grade." data-zh="本应用不会写入 CourseJesus 学员成绩或 LEARNED 权威；不生成视频、'
        '不调用远程模型，也不把练习当作正式课程成绩。">The app does not write CourseJesus learner '
        "scores or the LEARNED authority. It does not generate video, call a remote model, or "
        "present practice as an official course grade.</span></p></div></section>"
        "</div></main>"
        '<footer><div class="shell footer-grid"><p>CourseJesus — AccessBridge · '
        '<span data-en="Original synthetic lessons." data-zh="原创合成课程。">'
        "Original synthetic lessons.</span><br>"
        '<span data-en="Deterministic VisualSpec 1.0 → local SVG compiler → offline practice." '
        'data-zh="确定性 VisualSpec 1.0 → 本地 SVG 编译器 → 离线练习。">'
        "Deterministic VisualSpec 1.0 → local SVG compiler → offline practice.</span></p>"
        '<p><a href="manifest.json"><span data-en="Build manifest" data-zh="构建清单">'
        "Build manifest</span></a></p></div></footer>"
        "<script>document.addEventListener('click',event=>{"
        "if(event.target.closest('#toggle-language')){"
        "const english=document.documentElement.lang!=='en';"
        "document.documentElement.lang=english?'en':'zh-CN';"
        "document.querySelectorAll('[data-en]').forEach(el=>{"
        "el.textContent=english?el.dataset.en:el.dataset.zh;});}"
        "if(event.target.closest('#toggle-size')){const button=event.target.closest('#toggle-size');"
        "const on=document.body.classList.toggle('large-text');"
        "button.setAttribute('aria-pressed',String(on));}});</script>"
    )
    return _page("CourseJesus — AccessBridge", body, skip_link=False)


def build_site(output_dir: Path | None = None) -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    output = output_dir or root / "app" / "dist"
    output.mkdir(parents=True, exist_ok=True)
    (output / "lessons").mkdir(parents=True, exist_ok=True)
    (output / "offline").mkdir(parents=True, exist_ok=True)

    lessons = load_lessons()
    visuals = {lesson.lesson_id: _render_visual(lesson) for lesson in lessons}
    files: list[Path] = []

    index_path = output / "index.html"
    index_path.write_text(_render_index(lessons, visuals), encoding="utf-8")
    files.append(index_path)

    for lesson_number, lesson in enumerate(lessons, start=1):
        online_path = output / "lessons" / f"{lesson.lesson_id}.html"
        online_path.write_text(
            _render_lesson(
                lesson,
                visuals[lesson.lesson_id],
                lesson_number=lesson_number,
            ),
            encoding="utf-8",
        )
        offline_path = output / "offline" / f"{lesson.lesson_id}.html"
        offline_path.write_text(
            render_offline_pack(build_learning_pack(lesson, visuals[lesson.lesson_id])),
            encoding="utf-8",
        )
        files.extend([online_path, offline_path])

    manifest_entries = [
        {
            "path": file_path.relative_to(output).as_posix(),
            "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
            "size": file_path.stat().st_size,
        }
        for file_path in files
    ]
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "build": "coursejesus-accessbridge-v1",
                "lessons": [lesson.lesson_id for lesson in lessons],
                "visual_hashes": {
                    lesson_id: visual.sha256 for lesson_id, visual in visuals.items()
                },
                "files": manifest_entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    files.append(manifest_path)
    return files
