import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from io import BytesIO
import markdown2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from models import Document

class DocumentGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for PDF generation"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f2937')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#374151')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#4b5563')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=0.25*inch
        ))
    
    def generate_pdf(self, document: Document) -> BytesIO:
        """Generate a PDF document from the lease abstract data"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        title = Paragraph("Lease Abstract", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        doc_info_data = [
            ['Document:', document.original_filename or document.filename],
            ['Status:', document.status.value.title()],
            ['Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Uploaded:', document.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ]
        
        doc_info_table = Table(doc_info_data, colWidths=[1.5*inch, 4*inch])
        doc_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(doc_info_table)
        story.append(Spacer(1, 30))
        
        if document.ai_summary:
            story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
            summary_text = document.ai_summary.replace('\n', '<br/>')
            story.append(Paragraph(summary_text, self.styles['CustomBodyText']))
            story.append(Spacer(1, 20))
        
        if document.extracted_lease_data:
            story.append(Paragraph("Lease Abstract Details", self.styles['SectionHeader']))
            
            try:
                lease_data = json.loads(document.extracted_lease_data) if isinstance(document.extracted_lease_data, str) else document.extracted_lease_data
                
                if lease_data.get('parties'):
                    story.append(Paragraph("Parties", self.styles['SubHeader']))
                    parties_data = []
                    if lease_data['parties'].get('landlord'):
                        parties_data.append(['Landlord:', lease_data['parties']['landlord']])
                    if lease_data['parties'].get('tenant'):
                        parties_data.append(['Tenant:', lease_data['parties']['tenant']])
                    
                    if parties_data:
                        parties_table = Table(parties_data, colWidths=[1.2*inch, 4.3*inch])
                        parties_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ]))
                        story.append(parties_table)
                        story.append(Spacer(1, 15))
                
                if lease_data.get('dates'):
                    story.append(Paragraph("Lease Term", self.styles['SubHeader']))
                    dates_data = []
                    if lease_data['dates'].get('effectiveDate'):
                        dates_data.append(['Effective Date:', lease_data['dates']['effectiveDate']])
                    if lease_data['dates'].get('expirationDate'):
                        dates_data.append(['Expiration Date:', lease_data['dates']['expirationDate']])
                    
                    if dates_data:
                        dates_table = Table(dates_data, colWidths=[1.2*inch, 4.3*inch])
                        dates_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ]))
                        story.append(dates_table)
                        story.append(Spacer(1, 15))
                
                if lease_data.get('rent'):
                    story.append(Paragraph("Rent Information", self.styles['SubHeader']))
                    rent_data = []
                    if lease_data['rent'].get('baseRent'):
                        rent_data.append(['Base Rent:', lease_data['rent']['baseRent']])
                    
                    if rent_data:
                        rent_table = Table(rent_data, colWidths=[1.2*inch, 4.3*inch])
                        rent_table.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ]))
                        story.append(rent_table)
                        story.append(Spacer(1, 15))
                    
                    if lease_data['rent'].get('escalationClauses'):
                        story.append(Paragraph("Escalation Clauses:", self.styles['CustomBodyText']))
                        for clause in lease_data['rent']['escalationClauses']:
                            story.append(Paragraph(f"• {clause}", self.styles['CustomBodyText']))
                        story.append(Spacer(1, 10))
                
                if lease_data.get('options'):
                    story.append(Paragraph("Options & Terms", self.styles['SubHeader']))
                    
                    if lease_data['options'].get('renewalOptions'):
                        story.append(Paragraph("Renewal Options:", self.styles['CustomBodyText']))
                        for option in lease_data['options']['renewalOptions']:
                            story.append(Paragraph(f"• {option}", self.styles['CustomBodyText']))
                        story.append(Spacer(1, 10))
                    
                    if lease_data['options'].get('terminationClauses'):
                        story.append(Paragraph("Termination Clauses:", self.styles['CustomBodyText']))
                        for clause in lease_data['options']['terminationClauses']:
                            story.append(Paragraph(f"• {clause}", self.styles['CustomBodyText']))
                        story.append(Spacer(1, 10))
                
                if lease_data.get('use_clauses'):
                    story.append(Paragraph("Permitted Use", self.styles['SubHeader']))
                    for clause in lease_data['use_clauses']:
                        story.append(Paragraph(f"• {clause}", self.styles['CustomBodyText']))
                    story.append(Spacer(1, 10))
                        
            except (json.JSONDecodeError, TypeError) as e:
                story.append(Paragraph("Error parsing extracted lease data", self.styles['CustomBodyText']))
        
        else:
            story.append(Paragraph("Lease Abstract Details", self.styles['SectionHeader']))
            story.append(Paragraph("No structured data could be extracted from this document.", self.styles['CustomBodyText']))
        
        story.append(Spacer(1, 30))
        footer_text = f"Generated by LegalEase AI on {datetime.now().strftime('%B %d, %Y')}"
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_markdown(self, document: Document) -> str:
        """Generate a Markdown document from the lease abstract data"""
        md_content = []
        
        md_content.append("# Lease Abstract\n")
        
        md_content.append("## Document Information\n")
        md_content.append(f"- **Document:** {document.original_filename or document.filename}")
        md_content.append(f"- **Status:** {document.status.value.title()}")
        md_content.append(f"- **Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        md_content.append(f"- **Uploaded:** {document.created_at.strftime('%B %d, %Y at %I:%M %p')}\n")
        
        if document.ai_summary:
            md_content.append("## Executive Summary\n")
            md_content.append(f"{document.ai_summary}\n")
        
        if document.extracted_lease_data:
            md_content.append("## Lease Abstract Details\n")
            
            try:
                lease_data = json.loads(document.extracted_lease_data) if isinstance(document.extracted_lease_data, str) else document.extracted_lease_data
                
                if lease_data.get('parties'):
                    md_content.append("### Parties\n")
                    if lease_data['parties'].get('landlord'):
                        md_content.append(f"- **Landlord:** {lease_data['parties']['landlord']}")
                    if lease_data['parties'].get('tenant'):
                        md_content.append(f"- **Tenant:** {lease_data['parties']['tenant']}")
                    md_content.append("")
                
                if lease_data.get('dates'):
                    md_content.append("### Lease Term\n")
                    if lease_data['dates'].get('effectiveDate'):
                        md_content.append(f"- **Effective Date:** {lease_data['dates']['effectiveDate']}")
                    if lease_data['dates'].get('expirationDate'):
                        md_content.append(f"- **Expiration Date:** {lease_data['dates']['expirationDate']}")
                    md_content.append("")
                
                if lease_data.get('rent'):
                    md_content.append("### Rent Information\n")
                    if lease_data['rent'].get('baseRent'):
                        md_content.append(f"- **Base Rent:** {lease_data['rent']['baseRent']}")
                    
                    if lease_data['rent'].get('escalationClauses'):
                        md_content.append("- **Escalation Clauses:**")
                        for clause in lease_data['rent']['escalationClauses']:
                            md_content.append(f"  - {clause}")
                    md_content.append("")
                
                if lease_data.get('options'):
                    md_content.append("### Options & Terms\n")
                    
                    if lease_data['options'].get('renewalOptions'):
                        md_content.append("- **Renewal Options:**")
                        for option in lease_data['options']['renewalOptions']:
                            md_content.append(f"  - {option}")
                    
                    if lease_data['options'].get('terminationClauses'):
                        md_content.append("- **Termination Clauses:**")
                        for clause in lease_data['options']['terminationClauses']:
                            md_content.append(f"  - {clause}")
                    md_content.append("")
                
                if lease_data.get('use_clauses'):
                    md_content.append("### Permitted Use\n")
                    for clause in lease_data['use_clauses']:
                        md_content.append(f"- {clause}")
                    md_content.append("")
                        
            except (json.JSONDecodeError, TypeError) as e:
                md_content.append("Error parsing extracted lease data\n")
        
        else:
            md_content.append("## Lease Abstract Details\n")
            md_content.append("No structured data could be extracted from this document.\n")
        
        md_content.append("---")
        md_content.append(f"*Generated by LegalEase AI on {datetime.now().strftime('%B %d, %Y')}*")
        
        return "\n".join(md_content)

document_generator = DocumentGenerator()
