"""PDF Export Service - Professional HP Police Report Generation using ReportLab."""

import io
from datetime import datetime
from typing import Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


FIELD_DISPLAY_NAMES = {
    "unit_name": "Name of IRBn/Bn",
    "reserves_deployed": "Reserves Deployed",
    "districts": "Districts where force deployed",
    "stay_arrangement": "Stay Arrangement/Bathrooms",
    "messing": "Messing Arrangements",
    "co_interaction_date": "CO's last Interaction with SP",
    "disciplinary_issues": "Disciplinary Issues",
    "reserves_detained": "Reserves Detained",
    "training": "Training",
    "welfare": "Welfare Initiative in Last 24 Hrs",
    "reserves_available": "Reserves Available in Bn",
    "issues_for_phq": "Issue for AP&T/PHQ"
}

FIELD_KEYS = list(FIELD_DISPLAY_NAMES.keys())


def get_confidence_color(conf: float) -> colors.Color:
    """Get color based on confidence level."""
    if conf >= 0.7:
        return colors.Color(0.133, 0.773, 0.369)  # Green
    elif conf >= 0.5:
        return colors.Color(0.918, 0.702, 0.031)  # Yellow
    else:
        return colors.Color(0.937, 0.267, 0.267)  # Red


def get_confidence_label(conf: float) -> str:
    """Get label based on confidence level."""
    if conf >= 0.7:
        return "High"
    elif conf >= 0.5:
        return "Medium"
    else:
        return "Low"


def generate_pdf(
    report_data: Dict,
    confidence_scores: Dict,
    include_chart: bool = True,
    include_metadata: bool = True
) -> bytes:
    """Generate PDF report with HP Police styling."""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.Color(0.118, 0.227, 0.373),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.Color(0.118, 0.227, 0.373),
        spaceAfter=8,
        borderPadding=5
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    # Header
    story.append(Paragraph("HP Police ReportStream", title_style))
    story.append(Paragraph("Himachal Pradesh Police - Daily Status Report", 
        ParagraphStyle('SubTitle', parent=normal_style, fontSize=10, textColor=colors.gray, alignment=TA_CENTER)))
    story.append(Spacer(1, 12))
    
    # Report ID and Date
    story.append(Paragraph(f"<b>Report ID:</b> {report_data.get('id', 'N/A')} | <b>Generated:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        ParagraphStyle('Meta', parent=normal_style, fontSize=9, textColor=colors.gray)))
    story.append(Spacer(1, 10))
    
    # Statistics Summary
    total_fields = len(FIELD_KEYS)
    filled_fields = sum(1 for k in FIELD_KEYS if report_data.get(k))
    high_conf = sum(1 for c in confidence_scores.values() if c >= 0.7)
    avg_conf = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
    
    stats_data = [
        ['Fields Filled', 'Avg Confidence', 'High Confidence', 'Process Time'],
        [f"{filled_fields}/{total_fields}", f"{int(avg_conf*100)}%", f"{high_conf}", f"{report_data.get('processing_time', 0):.3f}s"]
    ]
    
    stats_table = Table(stats_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.118, 0.227, 0.373)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('BACKGROUND', (0, 1), (0, 1), colors.Color(0.863, 0.988, 0.906)),
        ('BACKGROUND', (1, 1), (1, 1), colors.Color(0.859, 0.914, 0.996)),
        ('BACKGROUND', (2, 1), (2, 1), colors.Color(0.988, 0.906, 0.969)),
        ('BACKGROUND', (3, 1), (3, 1), colors.Color(0.996, 0.953, 0.780)),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 15))
    
    # Meta Info
    meta_data = [
        ['Unit Name', report_data.get('unit_name', 'N/A')],
        ['Districts', report_data.get('districts', 'N/A')],
        ['CO Interaction', report_data.get('co_interaction_date', 'N/A')],
        ['Detected Format', (report_data.get('detected_format') or 'Unknown').upper()]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.5*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # Extracted Fields Table
    story.append(Paragraph("Extracted Fields", heading_style))
    
    field_data = [['Field', 'Value', 'Confidence', 'Status']]
    
    for field_key in FIELD_KEYS:
        value = report_data.get(field_key, "") or "N/A"
        conf = confidence_scores.get(field_key, 0)
        display_name = FIELD_DISPLAY_NAMES.get(field_key, field_key)
        
        if len(value) > 50:
            value = value[:47] + "..."
        
        field_data.append([
            display_name,
            value,
            f"{int(conf*100)}%",
            get_confidence_label(conf)
        ])
    
    field_table = Table(field_data, colWidths=[2*inch, 2.5*inch, 0.8*inch, 0.8*inch])
    field_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.118, 0.227, 0.373)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
    ]))
    
    for i in range(1, len(field_data)):
        conf = confidence_scores.get(FIELD_KEYS[i-1], 0)
        color = get_confidence_color(conf)
        field_table.setStyle(TableStyle([
            ('TEXTCOLOR', (2, i), (3, i), color),
        ]))
    
    story.append(field_table)
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "HP Police ReportStream v2.0 - Full Featured | PDF Export | Format Detection | Analytics",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    doc.build(story)
    
    buffer.seek(0)
    return buffer.getvalue()


class PDFService:
    """PDF Export Service."""
    
    def export_pdf(
        self,
        report_data: Dict,
        confidence_scores: Dict,
        include_chart: bool = True
    ) -> bytes:
        """Export report as PDF."""
        return generate_pdf(report_data, confidence_scores, include_chart)


pdf_service = PDFService()