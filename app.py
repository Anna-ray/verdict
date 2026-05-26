"""Verdict — web UI (Gradio). This is the deployable prototype.

Local:  python app.py
Deploy: push to a Hugging Face Space (SDK: gradio). Set secrets there:
        USE_MOCK=false, LLM_PROVIDER=groq, GROQ_API_KEY, BRIGHTDATA_API_TOKEN
"""
import html

import gradio as gr

import agent
import config

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
"""


def _render(result: dict) -> str:
    d = result["decision"]
    color, label = _COLORS.get(d["verdict"], ("#8aa2b5", d["verdict"]))
    factors = ""
    for f in d.get("factors", []):
        sev = str(f.get("severity", "")).upper()
        sc = _SEV.get(sev, "#8aa2b5")
        src = html.escape(str(f.get("source", "")))
        factors += (
            f'<div class="factor">'
            f'<span class="sev" style="color:{sc}">{sev}</span> '
            f'{html.escape(str(f.get("finding", "")))}'
            f'<div class="src">source: <a href="{src}" target="_blank">{src}</a></div>'
            f'</div>'
        )
    return (
        f'<div class="vcard">'
        f'<span class="badge" style="background:{color}">{label}</span>'
        f'<span class="score">risk {d["risk_score"]}/100 &middot; '
        f'{html.escape(str(d["confidence"]))} confidence</span>'
        f'<div class="summary">{html.escape(str(d["summary"]))}</div>'
        f'<div>{factors}</div>'
        f'<div class="rec"><b>Recommendation:</b> '
        f'{html.escape(str(d["recommendation"]))}</div>'
        f'</div>'
    )


def run_check(name, amount):
    name = (name or "").strip()
    if not name:
        yield "Enter a counterparty name to begin.", ""
        return
    log = []
    yield "Investigating the live web...", ""
    result = agent.run(name, amount, on_step=lambda m: log.append(m))
    trail = "\n".join(f"\u00b7 {m}" for m in log)
    yield trail, _render(result)


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
        card = gr.HTML()
        btn.click(run_check, inputs=[name_in, amount_in], outputs=[status, card])
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

if __name__ == "__main__":
    mode = "MOCK (offline)" if config.USE_MOCK else f"LIVE ({config.LLM_PROVIDER})"
    print(f"Verdict starting - data mode: {mode}")
    demo.launch()
