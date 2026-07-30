from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import allocations, company, cx, finance, marketing, product, quarter, sales

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Operations and People workspaces have no rules config yet (see README) -- not wired
# until operations_rules.json/people_rules.json exist, rather than shipping routers that
# can never accept a real decision.
app.include_router(company.router)
app.include_router(finance.router)
app.include_router(marketing.router)
app.include_router(product.router)
app.include_router(sales.router)
app.include_router(cx.router)
app.include_router(allocations.router)
app.include_router(quarter.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
