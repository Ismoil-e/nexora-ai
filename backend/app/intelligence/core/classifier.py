import re
from typing import Any

from app.intelligence.contracts.types import DocumentCategory


class DocumentClassifier:
    """Classifies document type based on structural headers, keywords, and semantic patterns."""

    PATTERNS: dict[DocumentCategory, list[str]] = {
        "Contract": [r"shartnoma", r"bitim", r"contract", r"agreement", r"tomoni", r"nizolarni hal qilish", r"shartlar", r"ijrochi", r"buyurtmachi"],
        "Invoice": [r"hisob-faktura", r"hisob varaq", r"invoice", r"bill", r"to'lov usuli", r"jami summa", r"qshs", r"tax id", r"subtotal", r"total due"],
        "Report": [r"hisobot", r"report", r"tahlil", r"xulosa", r"xulosasi", r"progress", r"quarterly", r"summary", r"natijalar"],
        "Policy": [r"nizom", r"qoida", r"yo'riqnoma", r"policy", r"regulation", r"guideline", r"standard operating procedure", r"sop"],
        "Meeting Notes": [r"bayonnoma", r"protokol", r"meeting notes", r"minutes", r"kun tartibi", r"ishtirokchilar", r"vazifalar", r"action items"],
        "Financial Document": [r"balans", r"moliyaviy", r"financial statement", r"balance sheet", r"p&l", r"cash flow", r"daromad", r"xarajat"],
        "Proposal": [r"tijorat taklifi", r"taklif", r"proposal", r"rfp", r"quotation", r"tender"],
        "HR Document": [r"mehnat shartnomasi", r"buyruq", r"hr", r"resume", r"cv", r"lawozim", r"xodim", r"employment"],
        "Technical Document": [r"spetsifikatsiya", r"arxitektura", r"specification", r"manual", r"guide", r"api reference", r"architecture"],
        "Logistics Document": [r"yuk xati", r"nakladnaya", r"bill of lading", r"waybill", r"shipment", r"freight"],
    }

    def classify(self, text: str, filename: str = "", metadata: dict[str, Any] | None = None) -> DocumentCategory:
        text_lower = (text[:3000] + " " + filename).lower()

        scores: dict[DocumentCategory, int] = {}
        for category, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            if score > 0:
                scores[category] = score

        if not scores:
            return "Other"

        # Return category with highest score
        best_category = max(scores.items(), key=lambda x: x[1])[0]
        return best_category


classifier = DocumentClassifier()
