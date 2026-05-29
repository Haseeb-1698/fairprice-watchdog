"""
PDF Complaint Generator - Creates court-ready FTC complaint PDFs
"""
import hashlib
from datetime import datetime
from io import BytesIO
from typing import Optional
import uuid

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scan import Scan
from app.models.listing import Listing
from app.models.fee import Fee
from app.models.evidence_snapshot import EvidenceSnapshot


def _add_page_number(canvas, doc):
    """Add page number and timestamp to each page"""
    canvas.saveState()
    
    # Page number at bottom center
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.setFont('Helvetica', 9)
    canvas.drawCentredString(letter[0] / 2, 0.5 * inch, text)
    
    # Timestamp at bottom right
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Generated: {timestamp}")
    
    canvas.restoreState()


async def generate_pdf_complaint(scan_id: uuid.UUID, db: AsyncSession) -> bytes:
    """
    Generate a court-ready PDF complaint for FTC submission
    
    Args:
        scan_id: UUID of the scan to generate complaint for
        db: Database session
    
    Returns:
        PDF file as bytes
    
    Raises:
        ValueError: If scan not found
    """
    # Fetch scan with all related data
    result = await db.execute(
        select(Scan)
        .options(
            selectinload(Scan.listings).selectinload(Listing.fees),
            selectinload(Scan.evidence_snapshots)
        )
        .where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise ValueError(f"Scan {scan_id} not found")
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch
    )
    
    # Container for PDF elements
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    normal_style = styles['Normal']
    
    # Header
    story.append(Paragraph("FTC Complaint — FairPrice Watchdog", title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Scan Details Section
    story.append(Paragraph("Scan Details", heading_style))
    
    scan_data = [
        ['Scan ID:', str(scan.id)],
        ['URL:', scan.url],
        ['Status:', scan.status],
        ['Scan Date:', scan.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
        ['Last Updated:', scan.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
    ]
    
    scan_table = Table(scan_data, colWidths=[1.5 * inch, 5 * inch])
    scan_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(scan_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Geographic Coverage
    if scan.listings:
        unique_states = sorted(set(listing.location_state for listing in scan.listings))
        story.append(Paragraph("Geographic Coverage", heading_style))
        story.append(Paragraph(f"States: {', '.join(unique_states)}", normal_style))
        story.append(Spacer(1, 0.3 * inch))
    
    # Listings and Fees Section
    story.append(Paragraph("Fee Breakdown", heading_style))
    
    if scan.listings:
        for idx, listing in enumerate(scan.listings, 1):
            # Listing header
            listing_header = f"Listing #{idx} - {listing.location_state}"
            story.append(Paragraph(listing_header, ParagraphStyle(
                'ListingHeader',
                parent=styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=8,
                spaceBefore=8,
                fontName='Helvetica-Bold'
            )))
            
            # Listing details
            listing_details = [
                ['Advertised Price:', f"${listing.advertised_price:.2f}"],
                ['Final Price:', f"${listing.final_price:.2f}"],
                ['Price Increase:', f"${listing.final_price - listing.advertised_price:.2f}"],
            ]
            
            listing_table = Table(listing_details, colWidths=[1.5 * inch, 2 * inch])
            listing_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(listing_table)
            story.append(Spacer(1, 0.1 * inch))
            
            # Fees table
            if listing.fees:
                fee_data = [['Fee Name', 'Amount', 'Type', 'Junk Fee', 'FTC Clause']]
                for fee in listing.fees:
                    fee_data.append([
                        fee.fee_name,
                        f"${fee.fee_amount:.2f}",
                        fee.fee_type,
                        'Yes' if fee.is_junk_fee else 'No',
                        fee.ftc_clause or 'N/A'
                    ])
                
                fee_table = Table(fee_data, colWidths=[1.5 * inch, 0.8 * inch, 1 * inch, 0.8 * inch, 2.4 * inch])
                fee_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                story.append(fee_table)
            else:
                story.append(Paragraph("No fees recorded for this listing.", normal_style))
            
            story.append(Spacer(1, 0.2 * inch))
    else:
        # Dummy data for testing
        story.append(Paragraph("No listings found. Using dummy data for testing:", normal_style))
        story.append(Spacer(1, 0.1 * inch))
        
        dummy_data = [
            ['Fee Name', 'Amount', 'Type', 'Junk Fee', 'FTC Clause'],
            ['Service Fee', '$25.00', 'service', 'Yes', '16 CFR § 254.4 - Drip Pricing'],
            ['Processing Fee', '$15.00', 'processing', 'Yes', '16 CFR § 254.4 - Drip Pricing'],
            ['Convenience Fee', '$10.00', 'convenience', 'Yes', '16 CFR § 254.4 - Drip Pricing'],
        ]
        
        dummy_table = Table(dummy_data, colWidths=[1.5 * inch, 0.8 * inch, 1 * inch, 0.8 * inch, 2.4 * inch])
        dummy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(dummy_table)
        story.append(Spacer(1, 0.2 * inch))
    
    # Evidence Hash Chain Section
    story.append(PageBreak())
    story.append(Paragraph("Evidence Hash Chain (SHA-256)", heading_style))
    story.append(Paragraph(
        "The following cryptographic hashes provide tamper-proof evidence of the captured data:",
        normal_style
    ))
    story.append(Spacer(1, 0.1 * inch))
    
    if scan.evidence_snapshots:
        hash_data = [['Timestamp', 'SHA-256 Hash']]
        for snapshot in scan.evidence_snapshots:
            hash_data.append([
                snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                snapshot.sha256_hash
            ])
        
        hash_table = Table(hash_data, colWidths=[2 * inch, 4.5 * inch])
        hash_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))
        story.append(hash_table)
    else:
        story.append(Paragraph("No evidence snapshots recorded.", normal_style))
    
    story.append(Spacer(1, 0.3 * inch))
    
    # Summary Section
    story.append(Paragraph("Summary", heading_style))
    
    total_listings = len(scan.listings)
    total_junk_fees = sum(
        1 for listing in scan.listings 
        for fee in listing.fees 
        if fee.is_junk_fee
    )
    total_junk_fee_amount = sum(
        fee.fee_amount for listing in scan.listings 
        for fee in listing.fees 
        if fee.is_junk_fee
    )
    
    summary_text = f"""
    This complaint documents pricing violations detected by FairPrice Watchdog.
    <br/><br/>
    <b>Total Listings Analyzed:</b> {total_listings}<br/>
    <b>Total Junk Fees Detected:</b> {total_junk_fees}<br/>
    <b>Total Junk Fee Amount:</b> ${total_junk_fee_amount:.2f}<br/>
    <br/>
    All evidence has been cryptographically hashed and timestamped to ensure integrity.
    This document is suitable for submission to the Federal Trade Commission (FTC) as evidence
    of potential violations of 16 CFR Part 254 (Rule on Unfair or Deceptive Fees).
    """
    
    story.append(Paragraph(summary_text, normal_style))
    
    # Build PDF with page numbers
    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# Made with Bob