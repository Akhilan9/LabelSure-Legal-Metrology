import io
from html import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas


class ConsolidatedNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for running headers, footers, watermark, and 'Page X of Y'.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()

        # Watermark
        self.setFont("Helvetica-Bold", 42)
        self.setFillColor(colors.HexColor("#064e3b"), alpha=0.035)
        self.rotate(35)
        self.drawString(120 * mm, -20 * mm, "LABELSURE INSPECTION CENTER")
        self.drawString(140 * mm, -70 * mm, "CONSOLIDATED STATUTORY AUDIT")
        self.rotate(-35)

        # Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#064e3b"))
        self.drawString(20 * mm, 285 * mm, "MINISTRY OF CONSUMER AFFAIRS · LEGAL METROLOGY DIVISION")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#78716c"))
        self.drawRightString(190 * mm, 285 * mm, "INSPECTION CENTER CONSOLIDATED REPORT")
        self.setStrokeColor(colors.HexColor("#d6d3d1"))
        self.setLineWidth(0.5)
        self.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)

        # Running Footer
        self.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#78716c"))
        self.drawString(20 * mm, 11 * mm, "Official Consolidated Inspection Center Record · Legal Metrology (Packaged Commodities) Rules, 2011")
        self.drawRightString(190 * mm, 11 * mm, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


def build_consolidated_center_pdf(report_data: dict) -> bytes:
    """
    Builds the official Consolidated Inspection Center Audit Report PDF using ReportLab.
    """
    def safe(value):
        if isinstance(value, str): return escape(value)
        if isinstance(value, dict): return {k: safe(v) for k, v in value.items()}
        if isinstance(value, list): return [safe(item) for item in value]
        return value

    report_data = safe(report_data)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#064e3b')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    sec_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyTxt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )
    mono_style = ParagraphStyle(
        'MonoTxt',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )
    justification_hdr_style = ParagraphStyle(
        'JustHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#991b1b')
    )
    justification_txt_style = ParagraphStyle(
        'JustTxt',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#7f1d1d')
    )

    story = []

    # Title & Legal Citation Header
    story.append(Paragraph("CONSOLIDATED STATUTORY PACKAGING INSPECTION REPORT", title_style))
    story.append(Paragraph(
        "OFFICIAL AUDIT LEDGER · LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011–2026<br/>"
        "ISSUED UNDER SECTION 36(1) OF THE LEGAL METROLOGY ACT, 2009",
        subtitle_style
    ))
    story.append(Spacer(1, 10))

    # Center Information Table
    center_name = report_data.get("center_name", "Designated Inspection Center")
    category = report_data.get("category", "General Packaged Commodities")
    location = report_data.get("location", "Not Specified")
    session_code = report_data.get("session_code", "IC-2026-SESSION")
    generated_at = report_data.get("generated_at", "")
    generated_by = report_data.get("generated_by", "Authorized Legal Metrology Officer")
    overall_verdict = report_data.get("overall_verdict", "COMPLIANT")
    tamper_hash = report_data.get("tamper_sha256", "SEALED-CRYPTOGRAPHIC-SHA256")

    is_compliant = overall_verdict == "COMPLIANT"
    verdict_color = "#064e3b" if is_compliant else "#991b1b"
    verdict_text = "PASSED · COMPLIANT DRIVE" if is_compliant else "NON-COMPLIANT · ENFORCEMENT ACTION REQUIRED"

    center_table_data = [
        [
            Paragraph("<b>Inspection Center:</b>", body_style),
            Paragraph(f"<b>{center_name}</b>", body_style),
            Paragraph("<b>Drive Code:</b>", body_style),
            Paragraph(f"<b>{session_code}</b>", mono_style)
        ],
        [
            Paragraph("<b>Enforcement Category:</b>", body_style),
            Paragraph(f"{category}", body_style),
            Paragraph("<b>Inspection Date:</b>", body_style),
            Paragraph(f"{generated_at}", body_style)
        ],
        [
            Paragraph("<b>Jurisdiction / Location:</b>", body_style),
            Paragraph(f"{location}", body_style),
            Paragraph("<b>Inspecting Officer:</b>", body_style),
            Paragraph(f"{generated_by}", body_style)
        ],
        [
            Paragraph("<b>Overall Center Status:</b>", body_style),
            Paragraph(f"<font color='{verdict_color}'><b>{verdict_text}</b></font>", body_style),
            Paragraph("<b>Tamper Seal (SHA-256):</b>", body_style),
            Paragraph(f"{tamper_hash[:20]}…", mono_style)
        ]
    ]

    c_table = Table(center_table_data, colWidths=[38 * mm, 50 * mm, 38 * mm, 48 * mm])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(c_table)
    story.append(Spacer(1, 12))

    # Executive Scorecard Grid
    total_items = report_data.get("total_items", 0)
    compliant_count = report_data.get("compliant_count", 0)
    non_compliant_count = report_data.get("non_compliant_count", 0)
    total_violations = report_data.get("total_violations", 0)
    compliance_rate = report_data.get("compliance_rate", "0.0%")

    metrics_data = [
        [
            Paragraph("<font size=7 color='#64748b'>TOTAL PACKAGES INSPECTED</font><br/><b><font size=13 color='#0f172a'>" + str(total_items) + "</font></b>", body_style),
            Paragraph("<font size=7 color='#64748b'>COMPLIANT ITEMS</font><br/><b><font size=13 color='#059669'>" + str(compliant_count) + "</font></b>", body_style),
            Paragraph("<font size=7 color='#64748b'>NON-COMPLIANT ITEMS</font><br/><b><font size=13 color='#e11d48'>" + str(non_compliant_count) + "</font></b>", body_style),
            Paragraph("<font size=7 color='#64748b'>COMPLIANCE RATE</font><br/><b><font size=13 color='#0284c7'>" + str(compliance_rate) + "</font></b>", body_style),
            Paragraph("<font size=7 color='#64748b'>TOTAL VIOLATIONS</font><br/><b><font size=13 color='#d97706'>" + str(total_violations) + "</font></b>", body_style),
        ]
    ]
    m_table = Table(metrics_data, colWidths=[34.8 * mm] * 5)
    m_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(m_table)
    story.append(Spacer(1, 14))

    # Legal Metrology Guideline Failure Justifications Section
    justifications = report_data.get("guideline_failure_justifications", [])
    if justifications:
        story.append(Paragraph("LEGAL METROLOGY GUIDELINE FAILURE JUSTIFICATIONS", sec_heading))
        just_rows = [
            [Paragraph("<b>Legal Metrology Guideline Failure Justifications</b>", justification_hdr_style)]
        ]
        for j in justifications:
            just_rows.append([Paragraph(j, justification_txt_style)])

        j_table = Table(just_rows, colWidths=[174 * mm])
        j_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fee2e2')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff1f2')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#f43f5e')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fecdd3')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(j_table)
        story.append(Spacer(1, 14))

    # Inspected Items Breakdown Table
    story.append(Paragraph("ITEMIZED STATUTORY PACKAGING AUDIT LEDGER", sec_heading))
    items = report_data.get("items", [])

    items_table_data = [
        [
            Paragraph("<b>#</b>", body_style),
            Paragraph("<b>COMMODITY / BRAND</b>", body_style),
            Paragraph("<b>CATEGORY</b>", body_style),
            Paragraph("<b>VERDICT</b>", body_style),
            Paragraph("<b>STATUTORY VIOLATIONS & CITATIONS</b>", body_style),
        ]
    ]

    for idx, itm in enumerate(items, start=1):
        p_name = itm.get("product_name") or f"Commodity Item #{idx}"
        b_name = itm.get("brand_name", "")
        prod_desc = f"<b>{p_name}</b>"
        if b_name: prod_desc += f"<br/><font color='#64748b'>Brand: {b_name}</font>"

        cat = itm.get("category", category)
        v = itm.get("verdict", "PENDING")
        v_color = "#059669" if v == "COMPLIANT" else "#e11d48"
        v_badge = f"<font color='{v_color}'><b>{v}</b></font>"

        viols = itm.get("violations", [])
        if viols:
            viol_text = ", ".join(viols)
        elif v == "COMPLIANT":
            viol_text = "<font color='#059669'>Conforms with Rule 6</font>"
        else:
            viol_text = "<font color='#e11d48'>Statutory Non-Compliance</font>"

        items_table_data.append([
            Paragraph(f"<b>{idx}</b>", body_style),
            Paragraph(prod_desc, body_style),
            Paragraph(cat, body_style),
            Paragraph(v_badge, body_style),
            Paragraph(viol_text, body_style),
        ])

    if len(items_table_data) > 1:
        it_table = Table(items_table_data, colWidths=[10 * mm, 54 * mm, 32 * mm, 30 * mm, 48 * mm])
        it_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(it_table)
    else:
        story.append(Paragraph("<i>No items evaluated under this center session.</i>", body_style))

    story.append(Spacer(1, 16))

    # Officer Affirmation & Signature Block
    sign_block = [
        [
            Paragraph(
                "<b>STATUTORY LEGAL AFFIRMATION:</b><br/>"
                "I hereby certify that the packaged commodities detailed in this consolidated audit report were inspected at the designated "
                "inspection center in accordance with the provisions of the <b>Legal Metrology Act, 2009</b> and the <b>Legal Metrology (Packaged Commodities) "
                "Rules, 2011–2026</b>. The automated image processing, optical text extraction, and rule verification findings are preserved "
                "with tamper-evident cryptographic integrity.",
                ParagraphStyle('AffTxt', parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'))
            )
        ],
        [
            Table([
                [
                    Paragraph(f"<b>Inspecting Officer:</b> {generated_by}<br/><b>Jurisdiction:</b> {location}<br/><b>Session Hash:</b> {tamper_hash[:28]}…", body_style),
                    Paragraph("<b>OFFICIAL STAMP & DIGITAL SIGNATURE:</b><br/><br/>________________________________________<br/>Authorized Legal Metrology Officer", body_style)
                ]
            ], colWidths=[87 * mm, 87 * mm])
        ]
    ]
    s_table = Table(sign_block, colWidths=[174 * mm])
    s_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([s_table]))

    doc.build(story, canvasmaker=ConsolidatedNumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
