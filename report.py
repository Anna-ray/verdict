"""Verdict — due-diligence report (PDF).

Turns a verdict result into a filed-ready, audit-grade PDF: the counterparty,
the verdict, risk score, sanctions-screen status, every cited factor, and a
timestamp. This is what makes Verdict feel like a compliance product rather
than a demo — a report a payment team can attach to the transaction record.

generate_report(result) -> path to the written PDF.
"""
import os
import tempfile
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# Brand palette (matches the deck / UI)
NAVY = colors.HexColor("#0A1A2F")
BLUE = colors.HexColor("#2E6FF2")
TEAL = colors.HexColor("#27D4C4")
INK = colors.HexColor("#1B2A3A")
MUTE = colors.HexColor("#5B6B7B")
GREEN = colors.HexColor("#1F9D72")
AMBER = colors.HexColor("#D39A2F")
RED = colors.HexColor("#D24B4B")
LIGHT = colors.HexColor("#F2F6FB")

_VCOLOR = {"APPROVE": GREEN, "ESCALATE": AMBER, "BLOCK": RED}
_SEVCOLOR = {"CRITICAL": RED, "HIGH": colors.HexColor("#E07A3F"),
             "MEDIUM": AMBER, "LOW": BLUE}


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("VTitle", parent=s["Title"], textColor=NAVY,
                         fontSize=22, spaceAfter=2, alignment=TA_LEFT))
    s.add(ParagraphStyle("VSub", parent=s["Normal"], textColor=MUTE,
                         fontSize=9.5, spaceAfter=2))
    s.add(ParagraphStyle("VH", parent=s["Heading2"], textColor=BLUE,
                         fontSize=11, spaceBefore=14, spaceAfter=6))
    s.add(ParagraphStyle("VBody", parent=s["Normal"], textColor=INK,
                         fontSize=10.5, leading=15))
    s.add(ParagraphStyle("VFind", parent=s["Normal"], textColor=INK,
                         fontSize=10, leading=14))
    s.add(ParagraphStyle("VSrc", parent=s["Normal"], textColor=BLUE,
                         fontSize=8.5, leading=12))
    s.add(ParagraphStyle("VFoot", parent=s["Normal"], textColor=MUTE,
                         fontSize=8, leading=11))
    return s


def generate_report(result: dict, out_dir: str = None) -> str:
    d = result.get("decision", {})
    name = result.get("name", "Unknown")
    amount = result.get("amount", "")
    sanc = result.get("sanctions") or {}
    verdict = d.get("verdict", "ESCALATE")
    vcolor = _VCOLOR.get(verdict, MUTE)
    st = _styles()

    out_dir = out_dir or tempfile.gettempdir()
    safe = "".join(c for c in name if c.isalnum() or c in " -_")[:40].strip()
    path = os.path.join(out_dir, f"Verdict_Report_{safe or 'counterparty'}.pdf")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    story = []

    # Header
    story.append(Paragraph("Verdict", st["VTitle"]))
    story.append(Paragraph("Counterparty Due-Diligence Report", st["VSub"]))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated {ts}", st["VFoot"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    story.append(Spacer(1, 12))

    # Verdict summary box (table used as a colored panel)
    score = d.get("risk_score", "?")
    conf = d.get("confidence", "")
    head = Table(
        [[Paragraph(f'<b>{verdict}</b>',
                    ParagraphStyle("v", textColor=colors.white, fontSize=18)),
          Paragraph(f'<b>{name}</b><br/><font size=9 color="#5B6B7B">'
                    f'Risk score {score}/100 &nbsp;|&nbsp; {conf} confidence'
                    f'{(" &nbsp;|&nbsp; Amount: " + str(amount)) if amount else ""}'
                    f'</font>',
                    ParagraphStyle("n", textColor=INK, fontSize=13, leading=16))]],
        colWidths=[38 * mm, 136 * mm])
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), vcolor),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
    ]))
    story.append(head)
    story.append(Spacer(1, 6))

    # Sanctions screen status
    if sanc.get("hit"):
        sline = (f'<b><font color="#D24B4B">OFAC sanctions screen: HIT</font></b> '
                 f'&mdash; matches "{sanc.get("matched","")}" ({sanc.get("source","")})')
    else:
        sline = ('<b><font color="#1F9D72">OFAC sanctions screen: CLEAR</font></b> '
                 '&mdash; no match on screened watchlists')
    story.append(Paragraph(sline, st["VBody"]))

    # Evidence integrity line (anti-hallucination verification result)
    integ = d.get("integrity") or {}
    if integ.get("total"):
        if integ.get("all_verified"):
            iline = (f'<b><font color="#1F9D72">Evidence integrity: '
                     f'{integ["verified"]}/{integ["total"]}</font></b> '
                     '&mdash; every finding cited and traced to a collected source.')
        else:
            iline = (f'<b><font color="#D39A2F">Evidence integrity: '
                     f'{integ["verified"]}/{integ["total"]} traced</font></b> &mdash; '
                     f'{d.get("evidence_warning","")}')
        story.append(Spacer(1, 2))
        story.append(Paragraph(iline, st["VBody"]))

    # Summary
    story.append(Paragraph("Summary", st["VH"]))
    story.append(Paragraph(d.get("summary", "(none)"), st["VBody"]))

    # Evidence confidence
    ct = d.get("confidence_tag") or {}
    if ct.get("level"):
        story.append(Paragraph(
            f'<b>Evidence confidence: {ct["level"]}</b> &mdash; '
            f'{ct.get("reason","")}', st["VBody"]))

    # Risk factors
    story.append(Paragraph("Risk factors &amp; evidence", st["VH"]))
    factors = d.get("factors", [])
    if not factors:
        story.append(Paragraph("No specific factors recorded.", st["VBody"]))
    for f in factors:
        sev = str(f.get("severity", "")).upper()
        sevc = _SEVCOLOR.get(sev, MUTE)
        vtag = ('<font color="#1F9D72"> [verified]</font>' if f.get("verified")
                else '<font color="#D39A2F"> [unverified]</font>')
        story.append(Paragraph(
            f'<font color="{sevc.hexval()}"><b>{sev}</b></font> &nbsp; '
            f'{f.get("finding","")}{vtag}', st["VFind"]))
        src = f.get("source", "")
        if src:
            story.append(Paragraph(f'Source: {src}', st["VSrc"]))
        story.append(Spacer(1, 6))

    # Recommendation
    story.append(Paragraph("Recommendation", st["VH"]))
    story.append(Paragraph(d.get("recommendation", "(none)"), st["VBody"]))

    # Why not higher risk (reassurance / what was checked and not found)
    why = d.get("why_not_higher") or []
    if why:
        story.append(Paragraph("Why not higher risk?", st["VH"]))
        for w in why:
            story.append(Paragraph(f'&#10003; {w}', st["VFind"]))

    # Adversarial-evidence / contradiction check
    contra = d.get("contradiction") or {}
    if contra.get("checked"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f'<b>Adversarial-evidence check:</b> {contra.get("note","")}',
            st["VBody"]))

    # Transparent risk calculation
    bd = d.get("breakdown") or {}
    if bd.get("lines"):
        story.append(Paragraph("Risk calculation", st["VH"]))
        rows = [["Base risk (unknown counterparty)", str(bd.get("baseline", 0))]]
        for l in bd["lines"]:
            dv = l["delta"]
            rows.append([l["label"], ("+" if dv >= 0 else "\u2212") + str(abs(dv))])
        rows.append(["Final risk score", f'{bd.get("total", 0)}/100'])
        t = Table(rows, colWidths=[140 * mm, 32 * mm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTE),
            ("LINEABOVE", (0, -1), (-1, -1), 0.75, MUTE),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(t)

    # Footer / methodology
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.75, color=MUTE))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Methodology: OFAC sanctions screening, then live-web investigation via "
        "Bright Data (search + structured scraping). Scraped content is treated "
        "as untrusted and sanitized before model analysis. Risk thresholds: "
        "0-25 APPROVE, 26-69 ESCALATE, 70-100 BLOCK. Generated by Verdict.",
        st["VFoot"]))
    story.append(Paragraph(
        "This report summarizes automated due-diligence signals and is intended "
        "to support, not replace, human compliance judgment.", st["VFoot"]))

    doc.build(story)
    return path
