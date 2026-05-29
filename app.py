"""Verdict — web UI (Gradio). This is the deployable prototype.

Local:  python app.py
Deploy: push to a Hugging Face Space (SDK: gradio). Set secrets there:
        USE_MOCK=false, LLM_PROVIDER=groq, GROQ_API_KEY, BRIGHTDATA_API_TOKEN
"""
import html
import tempfile

import gradio as gr

import agent
import config
import report

_COLORS = {
    "APPROVE": ("#1f9d72", "APPROVE"),
    "ESCALATE": ("#d39a2f", "ESCALATE"),
    "BLOCK": ("#d24b4b", "BLOCK"),
}
_SEV = {"CRITICAL": "#d24b4b", "HIGH": "#e07a3f",
        "MEDIUM": "#d39a2f", "LOW": "#3a9bd1"}
_ORDER = {"BLOCK": 0, "ESCALATE": 1, "APPROVE": 2}

_CSS = """
.gradio-container {background:#0a1622 !important; color:#e6eef5;}
#title {font-size:30px; font-weight:800; letter-spacing:-.5px; color:#e6eef5;}
#title span {color:#27d4c4;}
#subtitle {color:#8aa2b5; margin-top:-6px;}
.vcard {border:1px solid #1e3346; border-radius:14px; padding:22px;
        background:#0e1f30;}
.badge {display:inline-block; padding:8px 18px; border-radius:999px;
        font-weight:800; font-size:18px; color:#fff; letter-spacing:.5px;}
.score {color:#8aa2b5; margin-left:12px; font-size:15px;}
.summary {font-size:16px; line-height:1.5; margin:16px 0; color:#cdddea;}
.factor {border-left:3px solid #27d4c4; padding:8px 0 8px 14px; margin:10px 0;}
.sev {font-weight:700; font-size:12px; letter-spacing:.5px;}
.src {font-size:12px;}
.src a {color:#27d4c4; text-decoration:none;}
.rec {margin-top:16px; padding:14px; border-radius:10px; background:#102a3f;
      color:#cdddea;}
button.primary, .primary {background:#27d4c4 !important; color:#06222b !important;
      border:none !important; font-weight:700 !important;}
.btable {width:100%; border-collapse:collapse; font-size:14px;}
.btable th {text-align:left; color:#8aa2b5; font-weight:600; padding:10px 12px;
      border-bottom:1px solid #1e3346;}
.btable td {padding:12px; border-bottom:1px solid #14283a; color:#cdddea;}
.bbadge {display:inline-block; padding:4px 12px; border-radius:999px;
      font-weight:800; font-size:12px; color:#fff;}
.sline {margin:12px 0 4px; font-size:13px; font-weight:600;}
.sline.ok {color:#1f9d72;}
.sline.hit {color:#d24b4b;}
.changed {margin:4px 0; font-size:13px; font-weight:600; color:#d39a2f;}
.seen {margin:4px 0; font-size:13px; color:#8aa2b5;}
.foot {margin-top:14px; color:#8aa2b5; font-size:12px; text-align:center;}
.foot b {color:#27d4c4;}
.gauge {height:10px; border-radius:999px; background:#16293a; margin:14px 0 6px;
        overflow:hidden; position:relative;}
.gauge > i {display:block; height:100%; border-radius:999px;}
.gscale {display:flex; justify-content:space-between; color:#5b7184;
        font-size:10px; letter-spacing:.3px; margin-bottom:6px;}
.pipe {display:flex; gap:8px; flex-wrap:wrap; margin:14px 0 4px;}
.pstep {font-size:11px; font-weight:600; color:#9fd; background:#0c2230;
        border:1px solid #15384a; border-radius:999px; padding:4px 10px;}
.pstep b {color:#27d4c4;}
.empty {border:1px dashed #1e3346; border-radius:14px; padding:30px 24px;
        background:#0c1c2b; color:#8aa2b5;}
.empty h3 {color:#cdddea; margin:0 0 14px; font-size:16px; font-weight:700;}
.empty .pipe {justify-content:flex-start;}
.vok {font-size:11px; font-weight:700; color:#1f9d72; margin-left:6px;}
.vno {font-size:11px; font-weight:700; color:#d39a2f; margin-left:6px;}
.integ {margin:12px 0 2px; font-size:12.5px; font-weight:600; padding:8px 12px;
        border-radius:8px;}
.integ.ok {color:#1f9d72; background:#0d2a22;}
.integ.warn {color:#d39a2f; background:#2a230d;}
.calc {margin:14px 0 4px; border:1px solid #1e3346; border-radius:10px;
       background:#0c1c2b; padding:12px 14px;}
.calc h4 {margin:0 0 8px; color:#9fb3c4; font-size:12px; font-weight:700;
          letter-spacing:.4px; text-transform:uppercase;}
.crow {display:flex; justify-content:space-between; font-size:13px;
       padding:3px 0; color:#cdddea;}
.crow .d {font-variant-numeric:tabular-nums; font-weight:700;}
.crow .up {color:#e07a3f;}
.crow .down {color:#1f9d72;}
.crow.base {color:#8aa2b5;}
.crow.tot {border-top:1px solid #1e3346; margin-top:6px; padding-top:8px;
           font-weight:800; color:#e6eef5;}
"""


def _render(result: dict) -> str:
    d = result["decision"]
    sanc = result.get("sanctions") or {}
    change = result.get("change") or {}
    color, label = _COLORS.get(d["verdict"], ("#8aa2b5", d["verdict"]))
    factors = ""
    for f in d.get("factors", []):
        sev = str(f.get("severity", "")).upper()
        sc = _SEV.get(sev, "#8aa2b5")
        src = html.escape(str(f.get("source", "")))
        vflag = ('<span class="vok" title="Citation traced to collected evidence">'
                 '&#10003; verified</span>' if f.get("verified")
                 else '<span class="vno" title="Source not found in collected '
                 'evidence">&#9888; unverified</span>')
        factors += (
            f'<div class="factor">'
            f'<span class="sev" style="color:{sc}">{sev}</span> '
            f'{html.escape(str(f.get("finding", "")))} {vflag}'
            f'<div class="src">source: <a href="{src}" target="_blank">{src}</a></div>'
            f'</div>'
        )

    # Sanctions screen line — always shown (clear or hit).
    if sanc.get("hit"):
        sanc_html = (f'<div class="sline hit">&#9888; OFAC sanctions screen: '
                     f'HIT &mdash; matches "{html.escape(str(sanc.get("matched","")))}"</div>')
    else:
        sanc_html = ('<div class="sline ok">&#10003; OFAC sanctions screen: '
                     'clear</div>')

    # Memory / monitoring badge — only when seen before.
    change_html = ""
    if change and change.get("changed"):
        change_html = (
            f'<div class="changed">&#8635; Change since last check: '
            f'{html.escape(str(change.get("old_verdict")))} &rarr; '
            f'{html.escape(str(change.get("new_verdict")))} '
            f'(risk {change.get("old_risk")} &rarr; {change.get("new_risk")}, '
            f'{html.escape(str(change.get("direction")))})</div>')
    elif change:
        change_html = ('<div class="seen">&#8635; Previously checked &middot; '
                       'no material change</div>')

    # Risk gauge: a filled bar colored by verdict, width = risk score.
    try:
        pct = max(0, min(100, int(d.get("risk_score", 0))))
    except (TypeError, ValueError):
        pct = 0
    gauge = (
        f'<div class="gscale"><span>0 APPROVE</span>'
        f'<span>26 ESCALATE</span><span>70 BLOCK</span><span>100</span></div>'
        f'<div class="gauge"><i style="width:{pct}%;background:{color}"></i></div>'
    )

    # Pipeline status row — shows the steps that ran (auditability at a glance).
    web_ran = bool(result.get("evidence"))
    pipe = (
        '<div class="pipe">'
        '<span class="pstep"><b>&#10003;</b> OFAC screened</span>'
        + (f'<span class="pstep"><b>&#10003;</b> Live web ({len(result.get("evidence", []))} sources)</span>'
           if web_ran else '<span class="pstep">Web skipped (sanctions hit)</span>')
        + '<span class="pstep"><b>&#10003;</b> Sanitized</span>'
        '<span class="pstep"><b>&#10003;</b> Verdict</span>'
        '</div>'
    )

    # Evidence integrity badge — how many factors are citation-verified.
    integ = d.get("integrity") or {}
    integ_html = ""
    if integ.get("total"):
        if integ.get("all_verified"):
            integ_html = ('<div class="integ ok">&#10003; Evidence integrity: '
                          f'{integ["verified"]}/{integ["total"]} findings cited '
                          'and traced to collected sources</div>')
        else:
            integ_html = ('<div class="integ warn">&#9888; Evidence integrity: '
                          f'{integ["verified"]}/{integ["total"]} findings traced &middot; '
                          f'{html.escape(str(d.get("evidence_warning","")))}</div>')

    # Transparent risk calculation breakdown (explainability).
    bd = d.get("breakdown") or {}
    calc_html = ""
    if bd.get("lines"):
        rows = (f'<div class="crow base"><span>Base risk (unknown counterparty)'
                f'</span><span class="d">{bd.get("baseline",0)}</span></div>')
        for l in bd["lines"]:
            delta = l["delta"]
            sign = "+" if delta >= 0 else "\u2212"
            kind = "up" if delta >= 0 else "down"
            rows += (f'<div class="crow"><span>{html.escape(str(l["label"]))}</span>'
                     f'<span class="d {kind}">{sign}{abs(delta)}</span></div>')
        rows += (f'<div class="crow tot"><span>Final risk score</span>'
                 f'<span class="d">{bd.get("total",0)}/100</span></div>')
        calc_html = f'<div class="calc"><h4>Risk calculation</h4>{rows}</div>'

    return (
        f'<div class="vcard">'
        f'<span class="badge" style="background:{color}">{label}</span>'
        f'<span class="score">risk {d["risk_score"]}/100 &middot; '
        f'{html.escape(str(d["confidence"]))} confidence</span>'
        f'{gauge}'
        f'{sanc_html}{change_html}'
        f'{pipe}'
        f'{integ_html}'
        f'<div class="summary">{html.escape(str(d["summary"]))}</div>'
        f'<div>{factors}</div>'
        f'{calc_html}'
        f'<div class="rec"><b>Recommendation:</b> '
        f'{html.escape(str(d["recommendation"]))}</div>'
        f'</div>'
    )


_EMPTY_STATE = (
    '<div class="empty"><h3>Enter a counterparty to begin a live investigation.</h3>'
    '<div class="pipe">'
    '<span class="pstep"><b>1</b> OFAC sanctions screen</span>'
    '<span class="pstep"><b>2</b> Live web via Bright Data</span>'
    '<span class="pstep"><b>3</b> Sanitize untrusted input</span>'
    '<span class="pstep"><b>4</b> Cited verdict + score</span>'
    '</div></div>'
)


def run_check(name, amount):
    name = (name or "").strip()
    if not name:
        yield "Enter a counterparty name to begin.", "", None
        return
    log = []
    yield "Investigating the live web...", "", None
    result = agent.run(name, amount, on_step=lambda m: log.append(m))
    trail = "\n".join(f"\u00b7 {m}" for m in log)
    # Generate the audit-grade PDF report for download.
    try:
        pdf_path = report.generate_report(result, out_dir=tempfile.gettempdir())
    except Exception:
        pdf_path = None
    yield trail, _render(result), pdf_path


def _parse_names(text):
    raw = []
    for line in (text or "").splitlines():
        raw.extend(part.strip() for part in line.split(","))
    seen, out = set(), []
    for n in raw:
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def _render_batch(rows):
    rows = sorted(rows, key=lambda r: (_ORDER.get(r[1]["verdict"], 3),
                                       -int(r[1].get("risk_score", 0))))
    body = ""
    for name, d in rows:
        color, label = _COLORS.get(d["verdict"], ("#8aa2b5", d["verdict"]))
        top = d.get("factors", [])
        top_finding = html.escape(str(top[0].get("finding", "")) if top else "")
        body += (
            f'<tr>'
            f'<td><b>{html.escape(name)}</b></td>'
            f'<td><span class="bbadge" style="background:{color}">{label}</span></td>'
            f'<td>{d.get("risk_score", "?")}/100</td>'
            f'<td>{top_finding}</td>'
            f'</tr>'
        )
    return (
        '<div class="vcard"><table class="btable">'
        '<tr><th>Counterparty</th><th>Verdict</th><th>Risk</th>'
        '<th>Top finding</th></tr>'
        f'{body}</table></div>'
    )


def run_batch(text):
    names = _parse_names(text)
    if not names:
        yield "Paste one counterparty per line to begin.", ""
        return
    log = [f"Screening {len(names)} counterparties..."]
    yield "\n".join(log), ""
    rows = []
    for i, name in enumerate(names, 1):
        log.append(f"[{i}/{len(names)}] {name}")
        yield "\n".join(log), (_render_batch(rows) if rows else "")
        result = agent.run(name, "", on_step=lambda m: None)
        rows.append((name, result["decision"]))
        yield "\n".join(log), _render_batch(rows)
    log.append("Done. Highest-risk counterparties are listed first.")
    yield "\n".join(log), _render_batch(rows)


with gr.Blocks(css=_CSS, theme=gr.themes.Base()) as demo:
    gr.HTML('<div id="title">Verdict<span>.</span></div>'
            '<div id="subtitle">Autonomous counterparty due diligence - '
            'reads the live web before you wire a dollar.</div>')

    with gr.Tab("Single check"):
        with gr.Row():
            name_in = gr.Textbox(label="Counterparty / vendor name",
                                 placeholder="e.g. Wirecard AG")
            amount_in = gr.Textbox(label="Payment amount (optional)",
                                   placeholder="e.g. 50000 USD")
        btn = gr.Button("Run due diligence", variant="primary")
        status = gr.Textbox(label="Investigation trail", lines=6)
        card = gr.HTML(_EMPTY_STATE)
        report_file = gr.File(label="Download due-diligence report (PDF)",
                              interactive=False)
        btn.click(run_check, inputs=[name_in, amount_in],
                  outputs=[status, card, report_file])
        gr.Examples([["Apple Inc", "11111"], ["Wirecard AG", "50000"]],
                    inputs=[name_in, amount_in])

    with gr.Tab("Batch screening"):
        gr.HTML('<div style="color:#8aa2b5;margin:4px 0 8px">'
                'Paste a vendor list - one counterparty per line. Verdict checks '
                'them all and ranks the riskiest first.</div>')
        batch_in = gr.Textbox(
            label="Counterparty list", lines=8,
            placeholder="Apple Inc\nMicrosoft Corporation\nWirecard AG\nSiemens AG")
        bbtn = gr.Button("Screen all counterparties", variant="primary")
        bstatus = gr.Textbox(label="Progress", lines=6)
        btable = gr.HTML()
        bbtn.click(run_batch, inputs=[batch_in], outputs=[bstatus, btable])
        gr.Examples(
            [["Apple Inc\nMicrosoft Corporation\nWirecard AG\nSiemens AG"]],
            inputs=[batch_in])

    gr.HTML('<div class="foot">Powered by <b>Bright Data</b> (live web) &middot; '
            '<b>OFAC</b> sanctions screening &middot; <b>Cognee</b> memory &middot; '
            '<b>Groq / AI&#47;ML API</b> &middot; deployed on Hugging Face</div>')

if __name__ == "__main__":
    mode = "MOCK (offline)" if config.USE_MOCK else f"LIVE ({config.LLM_PROVIDER})"
    print(f"Verdict starting - data mode: {mode}")
    demo.launch()
