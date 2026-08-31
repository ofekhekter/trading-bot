import re
class NewsAnalyzer:
    def clean_headline(self, headline: str) -> str:
        cleaned = re.sub(
            r"^\{.*?\}!*",
            "",
            headline
        )

        return cleaned.strip()  
    def extract_price_target(self, headline: str):
        match = re.search(
            r"(?:target|price target)\s*\$?([0-9]+(?:\.[0-9]+)?)",
            headline.lower()
        )

        if not match:
            return None

        return float(match.group(1))

    def __init__(self):
        self.critical_negative_words = [
            "fraud",
            "bankruptcy",
            "investigation",
            "sec investigation",
            "guidance cut",
            "profit warning",
            "accounting issue",
            "recall",
            "lawsuit",
            "downgrade",
        ]

        self.positive_words = [
            "beats estimates",
            "raises guidance",
            "record revenue",
            "upgrade",
            "partnership",
            "contract win",
            "strong demand",
            "approval",
            "price target raised",
            "raises price target",
            "target raised",
            "soars",
            "surges",
            "jumps",
            "rallies",
            "strong growth",
            "growth outlook",
            "raises outlook",
            "strong outlook",
            "accelerating growth",
        ]

        self.negative_words = [
            "misses estimates",
            "cuts guidance",
            "weak demand",
            "downgrade",
            "layoffs",
            "warning",
            "decline",
            "price target cut",
            "cuts price target",
            "target lowered",
        ]

        self.analyst_weights = {
            "strong buy": 1.0,
            "buy": 0.8,
            "outperform": 0.8,
            "overweight": 0.8,
            "hold": 0.0,
            "underperform": -0.8,
            "underweight": -0.8,
            "sell": -1.0,
        }

    def analyze_headlines(
        self,
        headlines: list[str],
        current_price: float | None = None
    ) -> dict:
        score = 0.0
        critical_news = []
        price_targets = []

        for headline in headlines:
            headline = self.clean_headline(headline)
            text = headline.lower()

            target = self.extract_price_target(headline)

            if target is not None:
                price_targets.append(target)

            # Analyst rating
            analyst_score = 0.0

            for phrase, weight in self.analyst_weights.items():
                if phrase in text:
                    analyst_score = weight
                    break

            # Critical negative events
            for word in self.critical_negative_words:
                if word in text:
                    critical_news.append(headline)

            # General positive news
            for word in self.positive_words:
                if word in text:
                    score += 1.0

            # General negative news
            for word in self.negative_words:
                if word in text:
                    score -= 1.0

            score += analyst_score

            # Base news score
            if len(headlines) == 0:
                normalized_score = 0.0
            else:
                normalized_score = score / len(headlines)

            # Price target analysis
            highest_price_target = None
            target_upside_percent = None
            target_bonus = 0.0

            if current_price is not None and price_targets:
                highest_price_target = max(price_targets)

                target_upside_percent = (
                    (highest_price_target - current_price)
                    / current_price
                ) * 100

                if target_upside_percent >= 30:
                    target_bonus = 0.20
                elif target_upside_percent >= 15:
                    target_bonus = 0.12
                elif target_upside_percent >= 5:
                    target_bonus = 0.05
                elif target_upside_percent <= -20:
                    target_bonus = -0.20
                elif target_upside_percent <= -10:
                    target_bonus = -0.12
                elif target_upside_percent <= -5:
                    target_bonus = -0.05

            # Add price target influence
            normalized_score += target_bonus

            # Keep score between -1 and +1
            normalized_score = max(
                -1.0,
                min(1.0, normalized_score)
            )

            return {
                "news_score": round(normalized_score, 2),
                "has_critical_news": len(critical_news) > 0,
                "critical_headlines": critical_news,
                "highest_price_target": highest_price_target,
                "target_upside_percent": (
                    round(target_upside_percent, 2)
                    if target_upside_percent is not None
                    else None
                ),
                "target_bonus": round(target_bonus, 2),
            }