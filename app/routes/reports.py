"""
Report generation endpoints.

Renders rich PDF reports from simulation/run data using server-side Playwright PDF generation.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.schemas.decision_intelligence_report import DecisionIntelligenceReport
from app.schemas.errors import READ_RESPONSES
from app.services.pdf.decision_intelligence import render_decision_intelligence_pdf


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/decision-intelligence/pdf",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "12-page Decision Intelligence PDF report",
        },
        **READ_RESPONSES,
    },
    summary="Generate Decision Intelligence Report PDF",
    description=(
        "Renders a 12-page Decision Intelligence Report as a PDF using server-side "
        "Playwright (headless Chromium). Takes complete report data and returns a "
        "production-quality PDF with dark theme, consistent typography, and page-by-page "
        "breakdown of decision-making performance.\n\n"
        "**Pages:**\n"
        "1. Cover with final score and decision-maker profile\n"
        "2. Quarterly decision timeline\n"
        "3. Seven-dimension decision profile\n"
        "4. Biggest strength deep-dive\n"
        "5. Biggest decision risk analysis\n"
        "6. Decision that mattered most breakdown\n"
        "7. Missed opportunities\n"
        "8. Adaptability analysis table\n"
        "9. Decision signature (pattern characterization)\n"
        "10. Final score explanation with modifiers\n"
        "11. Company outcome metrics\n"
        "12. Recommendations for improvement\n\n"
        "**Performance:** First request ~1-2s (browser startup), subsequent requests <500ms "
        "(browser instance is pooled per worker).\n\n"
        "**Output:** Always exactly 12 pages at A4 format. Content is sized/truncated to fit."
    ),
)
async def generate_decision_intelligence_pdf(
    report_data: DecisionIntelligenceReport,
) -> Response:
    """
    Generate a Decision Intelligence Report PDF.
    
    Args:
        report_data: Complete 12-page report data matching the schema.
    
    Returns:
        PDF file as application/pdf response.
    
    Raises:
        HTTPException(500): If PDF rendering fails (Playwright error, template error, etc.)
    """
    try:
        pdf_bytes = await render_decision_intelligence_pdf(report_data)
        
        # Generate filename from metadata
        company_slug = report_data.metadata.company_name.lower().replace(" ", "-")
        ceo_slug = report_data.metadata.ceo_name.lower().replace(" ", "-")
        filename = f"decision-intelligence-{company_slug}-{ceo_slug}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache",
            },
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        ) from e
