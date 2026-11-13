"""Validated, self-contained offline practice-pack renderer.

This module is adapted from the isolated 2026-11-12 AccessED handoff component.
It has no network client and deliberately labels exported answers as practice,
not as an official grade or an offline AI capability.
"""

from __future__ import annotations

import html
import re

from app.visual.validators import validate_output


ALLOWED_ACCESS = {"synthetic", "public", "permission-cleared"}


def _localized(value: object, field: str) -> dict[str, str]:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field} must not be empty")
        return {"en": value, "zh": value}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be text or a bilingual object")
    en = value.get("en")
    zh = value.get("zh")
    if not isinstance(en, str) or not en.strip() or not isinstance(zh, str) or not zh.strip():
        raise ValueError(f"{field} requires both en and zh")
    return {"en": en, "zh": zh}


def validate(pack: dict) -> None:
    if pack.get("schema") != 1:
        raise ValueError("Unsupported or missing pack schema")
    package_id = pack.get("packageId")
    if not isinstance(package_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", package_id):
        raise ValueError("Unsupported or missing pack identity")
    if pack.get("access") not in ALLOWED_ACCESS:
        raise ValueError("Only synthetic/public/permission-cleared learning material may be exported")
    source_revision = pack.get("sourceRevision")
    if not isinstance(source_revision, str) or not source_revision.strip():
        raise ValueError("A source revision is required")
    _localized(pack.get("title"), "title")

    sources = pack.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("At least one source is required")
    ids: list[str] = []
    for source in sources:
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("Source ids are required")
        ids.append(source_id)
        _localized(source.get("title"), f"source {source_id} title")
        _localized(source.get("text"), f"source {source_id} text")
        rights = source.get("rights")
        if not isinstance(rights, str) or not rights.strip():
            raise ValueError("Each source requires a rights note")
    if len(set(ids)) != len(ids):
        raise ValueError("Source ids must be unique")

    sections = pack.get("sections")
    questions = pack.get("questions")
    if not isinstance(sections, list) or not sections:
        raise ValueError("At least one learning section is required")
    if not isinstance(questions, list) or not questions:
        raise ValueError("At least one practice question is required")
    source_ids = set(ids)
    for section in sections:
        _localized(section.get("heading"), "section heading")
        _localized(section.get("body"), "section body")
        refs = section.get("sourceIds")
        if not isinstance(refs, list) or not refs or any(ref not in source_ids for ref in refs):
            raise ValueError("Every learning item needs valid source references")

    question_ids: set[str] = set()
    for question in questions:
        question_id = question.get("id")
        if not isinstance(question_id, str) or not question_id or question_id in question_ids:
            raise ValueError("Question ids must be present and unique")
        question_ids.add(question_id)
        _localized(question.get("prompt"), f"question {question_id} prompt")
        _localized(question.get("explanation"), f"question {question_id} explanation")
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError("At least two options are required")
        for option in options:
            _localized(option, f"question {question_id} option")
        answer = question.get("answer")
        if type(answer) is not int or not 0 <= answer < len(options):
            raise ValueError("Invalid answer index")
        refs = question.get("sourceIds")
        if not isinstance(refs, list) or not refs or any(ref not in source_ids for ref in refs):
            raise ValueError("Every question needs valid source references")

    visual = pack.get("visual")
    if visual is not None:
        if not isinstance(visual, dict):
            raise ValueError("Visual metadata must be an object")
        _localized(visual.get("alt"), "visual alt text")
        _localized(visual.get("longDescription"), "visual long description")
        svg = visual.get("svg")
        if not isinstance(svg, str) or not svg:
            raise ValueError("A visual requires SVG content")
        validate_output(
            svg.encode("utf-8"),
            mime_type="image/svg+xml",
            width=1024,
            height=576,
            duration_seconds=None,
            max_bytes=1_000_000,
            max_width=1024,
            max_height=576,
            max_duration_seconds=0,
        )


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _localized_span(value: object) -> str:
    locale = _localized(value, "text")
    return (
        f'<span data-en="{_escape(locale["en"])}" '
        f'data-zh="{_escape(locale["zh"])}">{_escape(locale["en"])}</span>'
    )


def _sources_text(source_ids: list[str]) -> str:
    return " · ".join(_escape(value) for value in source_ids)


def render(pack: dict) -> str:
    validate(pack)
    title = _localized(pack["title"], "title")
    visual_html = ""
    visual = pack.get("visual")
    if visual:
        alt = _localized(visual["alt"], "visual alt text")
        long_description = _localized(visual["longDescription"], "visual long description")
        visual_html = (
            '<section aria-labelledby="visual-title"><h2 id="visual-title">'
            '<span data-en="Visual and text equivalent" data-zh="图形与文字等价">'
            "Visual and text equivalent</span></h2><figure>"
            + visual["svg"]
            + '<figcaption><strong><span data-en="Long description: " data-zh="文字说明：">'
            "Long description: </span></strong>"
            + _localized_span(long_description)
            + "</figcaption></figure></section>"
        )

    sections = "".join(
        "<article>"
        f'<h3>{_localized_span(section["heading"])}</h3>'
        f'<p>{_localized_span(section["body"])}</p>'
        f'<p class="evidence">Evidence / 依据: {_sources_text(section["sourceIds"])}</p>'
        "</article>"
        for section in pack["sections"]
    )
    sources = "".join(
        "<details>"
        f'<summary>{_escape(source["id"])} · {_localized_span(source["title"])}</summary>'
        f'<p>{_localized_span(source["text"])}</p>'
        f'<p class="rights">{_escape(source["rights"])}</p>'
        "</details>"
        for source in pack["sources"]
    )
    questions = []
    for index, question in enumerate(pack["questions"], start=1):
        options = "".join(
            '<label class="option"><input type="radio" '
            f'name="q-{_escape(question["id"])}" value="{option_index}"> '
            f"{_localized_span(option)}</label>"
            for option_index, option in enumerate(question["options"])
        )
        explanation = _localized(question["explanation"], "question explanation")
        questions.append(
            '<fieldset class="question">'
            f'<legend>{index}. {_localized_span(question["prompt"])}</legend>'
            f"{options}"
            '<button type="button" class="check">'
            '<span data-en="Check answer" data-zh="检查答案">Check answer</span></button>'
            '<p class="feedback" role="status" aria-live="polite" '
            f'data-answer="{question["answer"]}" '
            f'data-answer-en="{_escape(explanation["en"])}" '
            f'data-answer-zh="{_escape(explanation["zh"])}" '
            f'data-sources="{_escape(", ".join(question["sourceIds"]))}"></p>'
            "</fieldset>"
        )

    page_title = title["en"]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; "
        "img-src data:; form-action 'none'; base-uri 'none'\">"
        f"<title>{_escape(page_title)}</title><style>"
        ":root{color-scheme:light;--ink:#101828;--muted:#475467;--paper:#fbfcfe;"
        "--panel:#fff;--line:#cfd8e3;--accent:#174ea6;--focus:#7a1fa2;--ok:#0f6b54;--bad:#a32017}"
        "*,*::before,*::after{box-sizing:border-box}body{margin:0;background:var(--paper);"
        "color:var(--ink);font:18px/1.7 system-ui,sans-serif}body.large{font-size:22px}"
        "header,main,footer{width:min(920px,100%);margin:auto;padding:24px 20px}"
        "header{border-bottom:2px solid var(--line)}.eyebrow{font-size:.78rem;"
        "font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}"
        "h1{font-size:clamp(2rem,5vw,3.35rem);line-height:1.08;margin:.3em 0}"
        "h2{font-size:1.55rem;line-height:1.25}h3{line-height:1.3}nav{display:flex;"
        "flex-wrap:wrap;gap:10px;margin:18px 0}button{font:inherit;min-height:44px;"
        "border:2px solid var(--accent);border-radius:999px;background:#fff;color:var(--accent);"
        "padding:8px 18px;cursor:pointer}button:focus-visible,a:focus-visible,"
        "summary:focus-visible,input:focus-visible{outline:3px solid var(--focus);"
        "outline-offset:3px}.note{border-left:4px solid var(--accent);padding:12px 16px;"
        "background:#eef4ff}article,fieldset,details,figure{background:var(--panel);"
        "border:1px solid var(--line);border-radius:14px;padding:18px;margin:18px 0}"
        "figure svg{display:block;width:100%;height:auto}figcaption,.evidence,.rights,"
        "footer{font-size:.9rem;color:var(--muted)}legend{font-weight:750;padding:0 6px}"
        ".option{display:block;margin:10px 0;padding:8px;cursor:pointer}"
        ".option input{min-width:20px;min-height:20px;margin-right:10px;accent-color:var(--accent)}"
        ".feedback{min-height:1.7em;font-weight:700}.question{margin-top:22px}"
        "footer{border-top:2px solid var(--line)}@media(max-width:640px){header,main,footer"
        "{padding:18px 14px}article,fieldset,details,figure{padding:14px}}"
        "@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}"
        "</style></head><body>"
        '<header><p class="eyebrow">CourseJesus · AccessBridge · Offline pack</p>'
        f"<h1>{_localized_span(title)}</h1>"
        '<p class="note"><span data-en="OFFLINE PRACTICE · No account, AI request, or network '
        'required. Answers are included for study. This is not an official grade." '
        'data-zh="离线练习 · 无需账号、AI 调用或网络。答案用于学习；这不是正式成绩。">'
        "OFFLINE PRACTICE · No account, AI request, or network required. "
        "Answers are included for study. This is not an official grade.</span></p>"
        '<nav aria-label="Reading controls"><button type="button" id="language">'
        '<span data-en="中文" data-zh="English">中文</span></button>'
        '<button type="button" id="size" aria-pressed="false">'
        '<span data-en="Larger text" data-zh="大字">Larger text</span></button></nav></header>'
        '<main id="main"><section aria-labelledby="lesson-title"><h2 id="lesson-title">'
        '<span data-en="Learn one step at a time" data-zh="一步一步学习">'
        "Learn one step at a time</span></h2>"
        f"{sections}</section>{visual_html}"
        '<section aria-labelledby="practice-title"><h2 id="practice-title">'
        '<span data-en="Short practice" data-zh="短练习">Short practice</span></h2>'
        f'{"".join(questions)}</section>'
        '<section aria-labelledby="sources-title"><h2 id="sources-title">'
        '<span data-en="Sources and permissions" data-zh="来源与授权">Sources and permissions</span>'
        f"</h2>{sources}</section></main>"
        f'<footer><p>Package: <code>{_escape(pack["packageId"])}</code> · Revision: '
        f'<code>{_escape(pack["sourceRevision"])}</code> · Access: '
        f'<code>{_escape(pack["access"])}</code></p><p>'
        "Original synthetic learning material for this competition. Practice results stay in "
        "this page and are not uploaded or written to the CourseJesus score authority.</p></footer>"
        "<script>document.addEventListener('click',event=>{"
        "if(event.target.closest('#language')){const english=document.documentElement.lang!=='en';"
        "document.documentElement.lang=english?'en':'zh-CN';"
        "document.querySelectorAll('[data-en]').forEach(el=>{"
        "el.textContent=english?el.dataset.en:el.dataset.zh;});}"
        "if(event.target.closest('#size')){const on=document.body.classList.toggle('large');"
        "event.target.closest('#size').setAttribute('aria-pressed',String(on));}"
        "const button=event.target.closest('.check');if(!button){return;}"
        "const form=button.closest('fieldset');const chosen=form.querySelector('input:checked');"
        "const feedback=form.querySelector('.feedback');"
        "if(!chosen){feedback.textContent=document.documentElement.lang==='en'?"
        "'Choose an answer first.':'请先选择一个答案。';return;}"
        "const correct=Number(chosen.value)===Number(feedback.dataset.answer);"
        "const explanation=document.documentElement.lang==='en'?"
        "feedback.dataset.answerEn:feedback.dataset.answerZh;"
        "const phrase=document.documentElement.lang==='en'?"
        "(correct?'Correct. ':'Try again. '):(correct?'正确。':'再试一次。');"
        "feedback.textContent=phrase+explanation+"
        "(document.documentElement.lang==='en'?' Source: ':' 来源：')+feedback.dataset.sources;"
        "feedback.style.color=correct?'var(--ok)':'var(--bad)';});</script>"
        "</body></html>"
    )
