"""
PDF rendering service for Decision Intelligence Reports.

Uses Playwright for Python (headless Chromium) to convert Jinja2-templated HTML/CSS
into production-quality PDFs. This approach keeps all rendering in the Python backend,
avoiding the need for a separate Node/Puppeteer service.
"""

import asyncio
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright, Browser, Page

from app.schemas.decision_intelligence_report import DecisionIntelligenceReport


# ─── Constants ──────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "report.html"

# Playwright browser instance (shared per worker process for performance)
_browser_instance: Optional[Browser] = None
_browser_lock = asyncio.Lock()


# ─── Jinja2 Environment ─────────────────────────────────────────────────────────

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


# ─── Browser Lifecycle Management ──────────────────────────────────────────────

async def _get_browser() -> Browser:
    """
    Get or create a shared Playwright browser instance.
    
    Reuses a single browser across requests within the same worker process to avoid
    the ~500ms startup cost per request. This is safe because Playwright's browser
    instances are async-safe and each request gets its own page/context.
    """
    global _browser_instance
    
    async with _browser_lock:
        if _browser_instance is None or not _browser_instance.is_connected():
            playwright = await async_playwright().start()
            _browser_instance = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
    
    return _browser_instance


async def shutdown_browser() -> None:
    """
    Shut down the shared browser instance.
    
    Call this on application shutdown to clean up resources properly.
    """
    global _browser_instance
    
    async with _browser_lock:
        if _browser_instance is not None:
            await _browser_instance.close()
            _browser_instance = None


# ─── PDF Rendering ──────────────────────────────────────────────────────────────

async def render_decision_intelligence_pdf(
    report_data: DecisionIntelligenceReport,
) -> bytes:
    """
    Render a Decision Intelligence Report as a PDF.
    
    Args:
        report_data: Complete report data matching the 12-page schema.
    
    Returns:
        PDF file content as bytes.
    
    Raises:
        RuntimeError: If rendering fails (template error, Playwright crash, etc.)
    
    Implementation notes:
    - Jinja2 renders the HTML with injected data
    - CSS is loaded as a separate file (linked in the HTML)
    - Playwright loads the HTML+CSS in headless Chromium
    - Page is rendered to PDF with print-background enabled
    - Output is always exactly 12 pages (content is sized/truncated to fit)
    """
    try:
        # 1. Render HTML from Jinja2 template
        template = jinja_env.get_template(TEMPLATE_NAME)
        html_content = template.render(report_data.model_dump())
        
        # 2. Get browser instance (reused across requests)
        browser = await _get_browser()
        
        # 3. Create a new page (isolated context per request)
        page: Page = await browser.new_page()
        
        try:
            # 4. Set content with base URL so relative CSS links resolve
            await page.set_content(
                html_content,
                wait_until="networkidle",
            )
            
            # Manually inject CSS since set_content doesn't handle relative paths well
            css_path = TEMPLATE_DIR / "styles.css"
            css_content = css_path.read_text(encoding="utf-8")
            await page.add_style_tag(content=css_content)
            
            # 5. Wait for any dynamic content (fonts, images) to settle
            await page.wait_for_load_state("networkidle")
            
            # 6. Generate PDF
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "0mm",
                    "right": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                },
                prefer_css_page_size=True,
            )
            
            return pdf_bytes
        
        finally:
            # Always close the page to avoid resource leaks
            await page.close()
    
    except Exception as e:
        raise RuntimeError(f"Failed to render Decision Intelligence PDF: {e}") from e


# ─── Synchronous Wrapper (for non-async contexts) ──────────────────────────────

def render_decision_intelligence_pdf_sync(
    report_data: DecisionIntelligenceReport,
) -> bytes:
    """
    Synchronous wrapper for render_decision_intelligence_pdf.
    
    Useful for tests or CLI tools that don't run in an async context.
    """
    return asyncio.run(render_decision_intelligence_pdf(report_data))
