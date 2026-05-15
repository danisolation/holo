"""AI-powered sector intelligence using Gemini.

Phase 103: Gathers sector performance, flow, and market breadth data,
then uses Gemini to produce structured sector strength/weakness analysis
with rotation timing recommendations — all in Vietnamese.
"""
from datetime import date, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.sector import SectorIntelligenceResponse
from app.services.market_breadth_service import MarketBreadthService
from app.services.sector_analysis_service import SectorAnalysisService


class SectorIntelligenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _gather_context(self) -> dict:
        """Fetch sector performance, flow, and breadth data for last 30 days."""
        today = date.today()
        start_30d = today - timedelta(days=45)  # buffer for trading days
        start_7d = today - timedelta(days=10)

        sector_svc = SectorAnalysisService(self.session)
        breadth_svc = MarketBreadthService(self.session)

        perf = await sector_svc.get_sector_performance(start_30d, today)
        flow = await sector_svc.get_sector_flow(start_7d, today)
        breadth = await breadth_svc.get_all_breadth(start_7d, today)

        return {"performance": perf, "flow": flow, "breadth": breadth}

    def _build_prompt(self, context: dict) -> str:
        """Format context data into Gemini prompt."""
        # Format sector performance table
        perf_lines = ["## Biến động giá theo ngành:"]
        for s in context["performance"]:
            perf_lines.append(
                f"- {s['sector']}: Hôm nay {s.get('avg_change_today', 'N/A')}%, "
                f"7D {s.get('avg_change_7d', 'N/A')}%, "
                f"30D {s.get('avg_change_30d', 'N/A')}% ({s['ticker_count']} mã)"
            )

        # Format latest flow data (aggregate last 7D by sector)
        flow_by_sector: dict[str, dict] = {}
        for f in context["flow"]:
            sec = f["sector"]
            if sec not in flow_by_sector:
                flow_by_sector[sec] = {"net": 0, "buy": 0, "sell": 0}
            flow_by_sector[sec]["net"] += f["net_volume"]
            flow_by_sector[sec]["buy"] += f["buy_volume"]
            flow_by_sector[sec]["sell"] += f["sell_volume"]

        flow_lines = ["## Dòng tiền 7 ngày gần nhất:"]
        for sec, v in sorted(flow_by_sector.items()):
            direction = "MUA RÒNG" if v["net"] > 0 else "BÁN RÒNG"
            flow_lines.append(f"- {sec}: {direction} {abs(v['net']):,.0f} CP")

        # Format breadth summary (latest day)
        breadth_lines = ["## Breadth thị trường (ngày gần nhất):"]
        ad = context["breadth"].get("ad_line", [])
        ma = context["breadth"].get("ma_breadth", [])
        hl = context["breadth"].get("highs_lows", [])
        if ad:
            latest_ad = ad[-1]
            breadth_lines.append(
                f"- A/D: Tăng {latest_ad['advancing']}, Giảm {latest_ad['declining']}, Net {latest_ad['net']}"
            )
        if ma:
            latest_ma = ma[-1]
            breadth_lines.append(
                f"- Trên MA50: {latest_ma['pct_above_ma50']}%, Trên MA200: {latest_ma['pct_above_ma200']}%"
            )
        if hl:
            latest_hl = hl[-1]
            breadth_lines.append(
                f"- New Highs: {latest_hl['new_highs']}, New Lows: {latest_hl['new_lows']}"
            )

        return "\n".join(perf_lines + [""] + flow_lines + [""] + breadth_lines + [
            "",
            "Hãy phân tích sức mạnh từng ngành (strong/neutral/weak), xu hướng (improving/stable/declining), "
            "dòng tiền (inflow/neutral/outflow), và đề xuất rotation timing."
        ])

    async def run_analysis(self) -> dict:
        """Run full sector intelligence analysis via Gemini.

        Returns the parsed SectorIntelligenceResponse as dict, or raises on failure.
        """
        import json as json_module
        from google import genai
        from app.services.analysis.gemini_client import GeminiClient
        from app.services.analysis.prompts import SECTOR_INTELLIGENCE_SYSTEM_INSTRUCTION

        context_data = await self._gather_context()
        prompt = self._build_prompt(context_data)

        client = genai.Client(api_key=settings.gemini_api_key)
        model = settings.gemini_model
        gemini = GeminiClient(self.session, client, model)

        response = await gemini._call_gemini(
            prompt=prompt,
            response_schema=SectorIntelligenceResponse,
            temperature=0.2,
            system_instruction=SECTOR_INTELLIGENCE_SYSTEM_INSTRUCTION,
        )
        await gemini._record_usage("sector_intelligence", 1, response)

        result = response.parsed
        if result is None and response.text:
            logger.warning("Sector intelligence: response.parsed is None, falling back to manual JSON parse")
            try:
                data = json_module.loads(response.text)
                result = SectorIntelligenceResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")

        if result is None:
            raise ValueError("Gemini returned empty sector analysis")

        return result.model_dump()

    async def run_and_store(self) -> dict:
        """Run analysis and store in DB. Returns the analysis dict."""
        from app.models.sector_analysis import SectorAnalysis

        analysis_dict = await self.run_analysis()
        today = date.today()

        # Upsert: delete existing for today, insert new
        existing = await self.session.execute(
            select(SectorAnalysis).where(SectorAnalysis.analysis_date == today)
        )
        old = existing.scalar_one_or_none()
        if old:
            await self.session.delete(old)
            await self.session.flush()

        record = SectorAnalysis(
            analysis_date=today,
            analysis_json=analysis_dict,
            model_version=settings.gemini_model,
        )
        self.session.add(record)
        return analysis_dict

    async def get_latest(self) -> dict | None:
        """Get the most recent sector analysis from DB."""
        from app.models.sector_analysis import SectorAnalysis

        stmt = select(SectorAnalysis).order_by(SectorAnalysis.analysis_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return {
            "analysis_date": record.analysis_date.isoformat(),
            "model_version": record.model_version,
            "analysis": record.analysis_json,
        }
