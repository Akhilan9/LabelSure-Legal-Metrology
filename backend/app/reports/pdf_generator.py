import io
from datetime import datetime
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


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for precise running headers, footers, watermark, and 'Page X of Y'.
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
        self.setFont("Helvetica-Bold", 46)
        self.setFillColor(colors.HexColor("#064e3b"), alpha=0.04)
        self.rotate(35)
        self.drawString(140 * mm, -20 * mm, "LABELSURE LEGAL METROLOGY")
        self.drawString(160 * mm, -70 * mm, "OFFICIAL INSPECTION RECORD")
        self.rotate(-35)

        # Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#064e3b"))
        self.drawString(20 * mm, 285 * mm, "MINISTRY OF CONSUMER AFFAIRS · LEGAL METROLOGY DIVISION")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#78716c"))
        self.drawRightString(190 * mm, 285 * mm, "APEX LABELSURE / INSPECTION SUPPORT")
        self.setStrokeColor(colors.HexColor("#d6d3d1"))
        self.setLineWidth(0.5)
        self.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)

        # Running Footer
        self.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#78716c"))
        self.drawString(20 * mm, 11 * mm, "Inspection support report · Subject to authorized review and applicable law")
        self.drawRightString(190 * mm, 11 * mm, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


def build_inspection_pdf(report_data: dict, evidence_images=None) -> bytes:
    from html import escape
    from reportlab.platypus import Image as PDFImage
    def safe(value):
        if isinstance(value, str): return escape(value)
        if isinstance(value, dict): return {key: safe(item) for key, item in value.items()}
        if isinstance(value, list): return [safe(item) for item in value]
        return value
    report_data = safe(report_data)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#064e3b')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#57534e')
    )
    section_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#064e3b'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1c1917')
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#292524')
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    story = []

    # Title & Header
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("LEGAL METROLOGY COMPLIANCE INSPECTION REPORT", title_style))
    story.append(Paragraph("Statutory Packaging Verification, AI Extraction Evidence, & Human Review Ledger", subtitle_style))
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#064e3b'), spaceAfter=6))

    # Overall Compliance Banner Box with BIG VISUAL PASS / FAIL BADGE
    status = report_data.get("overall_compliance", "UNCERTAIN")
    
    badge_style_pass = ParagraphStyle(
        'PassBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Centered
        textColor=colors.white
    )
    badge_style_fail = ParagraphStyle(
        'FailBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Centered
        textColor=colors.white
    )

    if status == "COMPLIANT":
        badge_cell = Paragraph("<b>[ PASS ]<br/>✓</b>", badge_style_pass)
        badge_bg = colors.HexColor("#065f46")
        summary_cell = Paragraph(
            "<b>OFFICIAL VERDICT: FULLY COMPLIANT WITH LEGAL METROLOGY RULES, 2011</b><br/>"
            "<font color='#047857'>All 12 Rule 6 mandatory statutory declarations (MRP, Net Quantity, Month/Year of Pkg, Manufacturer Address, Consumer Care, Country of Origin) verified on package panels.</font>",
            body_style
        )
    else:
        badge_cell = Paragraph("<b>[ FAIL ]<br/>✕</b>", badge_style_fail)
        badge_bg = colors.HexColor("#991b1b")
        summary_cell = Paragraph(
            "<b>OFFICIAL VERDICT: NON-COMPLIANT (STATUTORY VIOLATION / REJECTED EVIDENCE)</b><br/>"
            "<font color='#b91c1c'>Mandatory Legal Metrology packaging declarations are missing, misformatted, or unreadable due to optical defects. Subject to statutory enforcement notice & penalty under Section 36 of Legal Metrology Act, 2009.</font>",
            body_style
        )

    banner_table = Table(
        [[badge_cell, summary_cell]],
        colWidths=[40 * mm, 130 * mm]
    )
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), badge_bg),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fafaf9')),
        ('BOX', (0, 0), (-1, -1), 1, badge_bg),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7e5e4')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 4 * mm))

    # Inspection & Product Details Grid
    meta = report_data.get("product_metadata", {})
    details_data = [
        [
            Paragraph("<b>Inspection Code:</b>", body_style),
            Paragraph(f"<font color='#064e3b'><b>{report_data.get('inspection_code', '—')}</b></font>", body_style),
            Paragraph("<b>Inspection Date:</b>", body_style),
            Paragraph(str(report_data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))), body_style)
        ],
        [
            Paragraph("<b>Product Name:</b>", body_style),
            Paragraph(str(meta.get("product_name") or "—"), body_style),
            Paragraph("<b>Brand Name:</b>", body_style),
            Paragraph(str(meta.get("brand_name") or "—"), body_style)
        ],
        [
            Paragraph("<b>Package Type:</b>", body_style),
            Paragraph(str(meta.get("package_type") or "—"), body_style),
            Paragraph("<b>Category:</b>", body_style),
            Paragraph(str(meta.get("category") or "—"), body_style)
        ],
        [
            Paragraph("<b>Import Status:</b>", body_style),
            Paragraph(str(meta.get("import_status") or "DOMESTIC"), body_style),
            Paragraph("<b>Assigned Officer:</b>", body_style),
            Paragraph(str(report_data.get("reviewer_name") or report_data.get("generated_by") or "Inspector"), body_style)
        ]
    ]

    details_table = Table(details_data, colWidths=[35 * mm, 50 * mm, 35 * mm, 50 * mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafaf9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7e5e4')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f5f5f4')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 4 * mm))

    # Legal Metrology Guideline Failure Justifications Section
    failure_justifications = report_data.get("guideline_failure_justifications", [])
    if failure_justifications:
        just_h1 = ParagraphStyle(
            'JustH1',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#991b1b'),
            spaceBefore=8,
            spaceAfter=4
        )
        story.append(Paragraph("Legal Metrology Guideline Failure Justifications", just_h1))
        
        just_rows = []
        for j in failure_justifications:
            just_rows.append([
                Paragraph("<font color='#dc2626'><b>[FAIL]</b></font>", ParagraphStyle('FailTag', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#dc2626'))),
                Paragraph(f"<font color='#7f1d1d' name='Courier-Bold'>{j}</font>", ParagraphStyle('FailDesc', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#7f1d1d')))
            ])
            
        just_table = Table(just_rows, colWidths=[16 * mm, 154 * mm])
        just_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dc2626')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fecaca')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(just_table)
        story.append(Spacer(1, 4 * mm))

    # Section 1: Statutory Rule Assessment Table
    story.append(Paragraph("1. Statutory Rule Compliance Ledger (Legal Metrology Rules, 2011)", section_h1))

    rule_headers = [
        Paragraph("<b>Rule Key</b>", table_header),
        Paragraph("<b>Title & Statutory Scope</b>", table_header),
        Paragraph("<b>Machine</b>", table_header),
        Paragraph("<b>Inspector</b>", table_header),
        Paragraph("<b>Final Verdict</b>", table_header),
        Paragraph("<b>Legal Reference</b>", table_header)
    ]

    rule_rows = [rule_headers]
    for r in report_data.get("rule_evaluations", []):
        v = r.get("final_verdict")
        if v not in {"PASS", "FAIL", "NOT_APPLICABLE"}:
            v = "FAIL"
        v_color = "#065f46" if v == "PASS" else ("#78716c" if v == "NOT_APPLICABLE" else "#991b1b")
        ov_text = "Override" if r.get("is_overridden") else "Confirmed"

        rule_rows.append([
            Paragraph(f"<b>{r.get('rule_key')}</b>", table_cell),
            Paragraph(f"{r.get('title', '')}<br/><font color='#78716c' size='7'>{r.get('description', '')[:70]}</font>", table_cell),
            Paragraph(r.get("original_verdict") or r.get("machine_verdict") or "—", table_cell),
            Paragraph(f"<font color='{'#b45309' if r.get('is_overridden') else '#57534e'}'>{ov_text}</font>", table_cell),
            Paragraph(f"<font color='{v_color}'><b>{v}</b></font>", table_cell),
            Paragraph(f"<font size='7'>{r.get('legal_reference', 'Legal Metrology Rules, 2011')[:45]}</font>", table_cell),
        ])

    rules_table = Table(
        rule_rows,
        colWidths=[30 * mm, 45 * mm, 20 * mm, 20 * mm, 20 * mm, 35 * mm]
    )
    rules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#064e3b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7e5e4')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
    ]))
    story.append(rules_table)
    story.append(Spacer(1, 4 * mm))

    # Section 1A: Photometric Image Quality & Optical Defect Assessment
    image_quality = report_data.get("image_quality_findings", [])
    if image_quality:
        story.append(Paragraph("1A. Photometric Image Quality & Optical Defect Assessment", section_h1))
        quality_rows = [
            [
                Paragraph("<b>Evidence Image</b>", table_header),
                Paragraph("<b>Panel</b>", table_header),
                Paragraph("<b>Resolution</b>", table_header),
                Paragraph("<b>Quality Grade</b>", table_header),
                Paragraph("<b>Optical Defect Justification</b>", table_header)
            ]
        ]
        for q in image_quality:
            stat_color = "#991b1b" if q["is_defective"] else "#065f46"
            quality_rows.append([
                Paragraph(f"<b>{q['filename']}</b>", table_cell),
                Paragraph(q['panel'], table_cell),
                Paragraph(q['resolution'], table_cell),
                Paragraph(f"<font color='{stat_color}'><b>{q['quality_status']}</b></font>", table_cell),
                Paragraph(f"<font color='{stat_color}'>{q['justification']}</font>", table_cell)
            ])
        quality_table = Table(quality_rows, colWidths=[40 * mm, 25 * mm, 25 * mm, 25 * mm, 55 * mm])
        quality_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(quality_table)
        story.append(Spacer(1, 4 * mm))

    # Section 1B: Reason for Hazard & Non-Compliance Explanations
    hazards = report_data.get("hazard_explanations", [])
    if hazards:
        story.append(Paragraph("1B. Non-Compliance Hazard Explanations & Consumer Impact", section_h1))
        hazard_rows = [
            [
                Paragraph("<b>Rule & Title</b>", table_header),
                Paragraph("<b>Failure Reason / Technical Deviation</b>", table_header),
                Paragraph("<b>Consumer & Legal Hazard Explanation</b>", table_header)
            ]
        ]
        for h in hazards:
            hazard_rows.append([
                Paragraph(f"<font color='#991b1b'><b>{h['title']}</b></font><br/><font size='7' color='#78716c'>{h['rule_key']}</font>", table_cell),
                Paragraph(f"<font color='#991b1b'>{h['reason']}</font>", table_cell),
                Paragraph(f"<b>Hazard:</b> {h['hazard']}", table_cell)
            ])
        hazard_table = Table(hazard_rows, colWidths=[40 * mm, 60 * mm, 70 * mm])
        hazard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991b1b')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fca5a5')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef2f2'), colors.white]),
        ]))
        story.append(hazard_table)
        story.append(Spacer(1, 4 * mm))

    # Section 2: Cross-Border & International Metrological Standards Matrix
    matrix = report_data.get("international_matrix", [])
    if matrix:
        story.append(Paragraph("2. International & Cross-Border Metrological Compliance Matrix", section_h1))
        matrix_rows = [
            [
                Paragraph("<b>Declaration Parameter</b>", table_header),
                Paragraph("<b>🇮🇳 India (LMPC 2011)</b>", table_header),
                Paragraph("<b>🇺🇸 USA (NIST 133)</b>", table_header),
                Paragraph("<b>🇪🇺 EU / UK (Dir 76/211)</b>", table_header),
                Paragraph("<b>🌐 OIML (R79/R87)</b>", table_header)
            ]
        ]
        for row in matrix:
            ind_col = "#065f46" if row["india"] == "COMPLIANT" else "#991b1b"
            usa_col = "#065f46" if row["usa"] == "COMPLIANT" else ("#78716c" if row["usa"] == "EXEMPT" else "#92400e")
            eu_col = "#065f46" if row["eu_uk"] == "COMPLIANT" else ("#78716c" if row["eu_uk"] == "EXEMPT" else "#92400e")
            oiml_col = "#065f46" if row["oiml"] == "COMPLIANT" else ("#78716c" if row["oiml"] == "EXEMPT" else "#0284c7")

            matrix_rows.append([
                Paragraph(f"<b>{row['parameter']}</b>", table_cell),
                Paragraph(f"<font color='{ind_col}'><b>{row['india']}</b></font><br/><font size='6.5' color='#57534e'>{row['india_note']}</font>", table_cell),
                Paragraph(f"<font color='{usa_col}'><b>{row['usa']}</b></font><br/><font size='6.5' color='#57534e'>{row['usa_note']}</font>", table_cell),
                Paragraph(f"<font color='{eu_col}'><b>{row['eu_uk']}</b></font><br/><font size='6.5' color='#57534e'>{row['eu_uk_note']}</font>", table_cell),
                Paragraph(f"<font color='{oiml_col}'><b>{row['oiml']}</b></font><br/><font size='6.5' color='#57534e'>{row['oiml_note']}</font>", table_cell)
            ])

        matrix_table = Table(matrix_rows, colWidths=[38 * mm, 33 * mm, 33 * mm, 33 * mm, 33 * mm])
        matrix_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(matrix_table)
        story.append(Spacer(1, 4 * mm))

    # Section 3: Extracted Declarations & Photometric Evidence
    story.append(Paragraph("3. Extracted Declarations & Photometric Evidence Ledger", section_h1))

    decl_headers = [
        Paragraph("<b>Declaration Type</b>", table_header),
        Paragraph("<b>Normalized Value</b>", table_header),
        Paragraph("<b>Raw Observed Text</b>", table_header),
        Paragraph("<b>Confidence</b>", table_header),
        Paragraph("<b>Status / Source</b>", table_header)
    ]
    decl_rows = [decl_headers]
    for d in report_data.get("declarations_summary", []):
        conf = f"{float(d.get('confidence_score', 0)):.1%}" if d.get('confidence_score') is not None else "—"
        decl_rows.append([
            Paragraph(f"<b>{d.get('declaration_type')}</b>", table_cell),
            Paragraph(f"<font color='#064e3b'><b>{d.get('normalized_value', '—')}</b></font>", table_cell),
            Paragraph(f"<font color='#57534e'>{str(d.get('raw_value', '—'))[:60]}</font>", table_cell),
            Paragraph(conf, table_cell),
            Paragraph(f"<font size='7'>{d.get('extraction_method', 'AUTO')}</font>", table_cell)
        ])

    if len(decl_rows) > 1:
        decl_table = Table(decl_rows, colWidths=[38 * mm, 40 * mm, 50 * mm, 18 * mm, 24 * mm])
        decl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1c1917')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7e5e4')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafaf9')]),
        ]))
        story.append(decl_table)
    else:
        story.append(Paragraph("<i>No declarations detected or extracted.</i>", body_style))

    story.append(Spacer(1, 4 * mm))

    # Section 4: Summary Observations & Chain of Custody Signature Block
    story.append(KeepTogether([
        Paragraph("4. Inspector Observations & Chain of Custody Seal", section_h1),
        Table([
            [
                Paragraph(f"<b>Closing Officer Remarks:</b><br/>{report_data.get('summary_notes') or 'No inspector observations recorded.'}", body_style),
                Paragraph(f"<b>Cryptographic Tamper Checksum (SHA-256):</b><br/><font fontName='Courier' size='7'>{report_data.get('tamper_sha256', '—')}</font><br/><br/><b>Inspector account:</b><br/><i>{report_data.get('reviewer_name') or 'Not recorded'}</i><br/>Signature pending. This PDF is not digitally signed.", body_style)
            ]
        ], colWidths=[90 * mm, 80 * mm], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafaf9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d6d3d1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7e5e4')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]),
        Spacer(1, 4 * mm)
    ]))

    if evidence_images:
        story.append(Paragraph("4. Photographic Evidence", section_h1))
        for filename, checksum, content in evidence_images:
            picture = PDFImage(io.BytesIO(content))
            ratio = min(160*mm / picture.imageWidth, 130*mm / picture.imageHeight)
            picture.drawWidth = picture.imageWidth * ratio
            picture.drawHeight = picture.imageHeight * ratio
            story.append(KeepTogether([Paragraph(escape(filename), body_style), picture,
                Paragraph("Original evidence SHA-256: " + checksum, table_cell), Spacer(1, 6*mm)]))
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
