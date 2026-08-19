import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


class BIReportGenerator:
    """Generates formatted reports (Markdown, HTML, JSON, CSV) with metrics, insights, and citations."""

    def format_markdown_report(
        self,
        title: str,
        company_name: str,
        timeframe: str,
        executive_summary: Dict[str, Any],
        kpis: List[Dict[str, Any]],
        insights: List[Dict[str, Any]],
        risks: List[Dict[str, Any]],
    ) -> str:
        """Formats full report in GitHub-flavored Markdown with tables and alerts."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        narrative = executive_summary.get("executive_narrative", "Ma'lumot mavjud emas.")
        lines = [
            f"# 📊 {title}",
            f"**Kompaniya:** {company_name}  ",
            f"**Davr:** {timeframe}  ",
            f"**Yaratilgan vaqti:** {now}  ",
            f"**Umumiy holat:** `{executive_summary.get('overall_health', 'good').upper()}`  ",
            "",
            "---",
            "",
            "## 1. 🎯 Ijroiy Xulosa (Executive Narrative)",
            f"> {narrative}",
            "",
            "### Asosiy Xulosalar:",
        ]

        for insight in executive_summary.get("key_insights", []):
            lines.append(f"- {insight}")

        lines.extend([
            "",
            "---",
            "",
            "## 2. 📈 Asosiy Ko'rsatkichlar Jadvali (KPI Table)",
            "",
            "| KPI KODI | Ko'rsatkich Nomi | Joriy Qiymat | Birlik | O'zgarish % | Holati |",
            "| :--- | :--- | :---: | :---: | :---: | :---: |",
        ])

        for k in kpis:
            chg = f"{k.get('change_pct')}%" if k.get('change_pct') is not None else "-"
            lines.append(
                f"| `{k.get('code')}` | {k.get('name')} | **{k.get('current_value')}** | {k.get('unit', '')} | {chg} | `{k.get('status')}` |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. ⚠️ Aniqlangan Xatarlar va Muammolar (Risk Matrix)",
            "",
        ])

        if risks:
            for r in risks:
                lines.append(f"### 🔻 [{r.get('risk_level', 'warning').upper()}] {r.get('title')}")
                lines.append(f"**Tavsif:** {r.get('description')}  ")
                lines.append(f"**Ta'siri:** {r.get('impact')}  ")
                lines.append(f"**Tavsiya etilgan chora:** {r.get('mitigation_step')}  ")
                lines.append("")
        else:
            lines.append("Xatarlar aniqlanmadi. Barcha jarayonlar me'yoriy chegarada.")

        lines.extend([
            "---",
            "",
            "## 4. 💡 AI Tavsiyalari va Qarorlar Intellekti (Recommendations)",
            "",
        ])

        for rec in executive_summary.get("actionable_recommendations", []):
            lines.append(f"- **[{rec.get('priority', 'medium').upper()}] {rec.get('action')}**: {rec.get('rationale')}")

        lines.extend([
            "",
            "---",
            "",
            "## 5. 📚 Axborot Manbalari (Source Citations)",
            "",
        ])

        for cit in executive_summary.get("source_citations", []):
            lines.append(f"- *{cit.get('title')}* ({cit.get('source_type')}) — {cit.get('timestamp')}")

        return "\n".join(lines)


report_generator = BIReportGenerator()
