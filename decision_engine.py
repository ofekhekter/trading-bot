class DecisionEngine:
    def __init__(
        self,
        min_fundamental_score=60,
        min_technical_score=70,
        min_news_score=-0.20,
        min_final_score=70,
    ):
        self.min_fundamental_score = min_fundamental_score
        self.min_technical_score = min_technical_score
        self.min_news_score = min_news_score
        self.min_final_score = min_final_score

    def evaluate(
        self,
        symbol: str,
        fundamental_score: float,
        technical_score: float,
        news_score: float,
        has_critical_news: bool = False,
        earnings_soon: bool = False,
        rsi: float | None = None,
        momentum: float | None = None,
        price: float | None = None,
        ema20: float | None = None,
        ema50: float | None = None,
    ) -> dict:

        reasons = []
        long_score = 0.0
        short_score = 0.0

        long_reasons = []
        short_reasons = []
        # Trend structure
        if (
            price is not None
            and ema20 is not None
            and ema50 is not None
        ):
            if price > ema20 > ema50:
                long_score += 30
                long_reasons.append(
                    "Bullish trend: price > EMA20 > EMA50"
                )

            elif price < ema20 < ema50:
                short_score += 30
                short_reasons.append(
                    "Bearish trend: price < EMA20 < EMA50"
                )
                # Momentum
        # Momentum
        if momentum is not None:

            if momentum >= 2.0:
                long_score += 20
                long_reasons.append(
                    f"Strong positive momentum: {momentum:.2f}%"
                )

            elif momentum >= 1.0:
                long_score += 15
                long_reasons.append(
                    f"Moderate positive momentum: {momentum:.2f}%"
                )

            elif momentum >= 0.3:
                long_score += 10
                long_reasons.append(
                    f"Positive momentum: {momentum:.2f}%"
                )

            elif momentum > 0:
                long_score += 3
                long_reasons.append(
                    f"Slight positive momentum: {momentum:.2f}%"
                )

            elif momentum <= -2.0:
                short_score += 20
                short_reasons.append(
                    f"Strong negative momentum: {momentum:.2f}%"
                )

            elif momentum <= -1.0:
                short_score += 15
                short_reasons.append(
                    f"Moderate negative momentum: {momentum:.2f}%"
                )

            elif momentum <= -0.3:
                short_score += 10
                short_reasons.append(
                    f"Negative momentum: {momentum:.2f}%"
                )

            elif momentum < 0:
                short_score += 3
                short_reasons.append(
                    f"Slight negative momentum: {momentum:.2f}%"
                )

                # Contextual RSI
        if rsi is not None:

            bullish_context = (
                price is not None
                and ema20 is not None
                and ema50 is not None
                and price > ema20 > ema50
            )

            bearish_context = (
                price is not None
                and ema20 is not None
                and ema50 is not None
                and price < ema20 < ema50
            )

        # RSI confirmation for LONG
        if bullish_context:
            if 50 <= rsi <= 65:
                long_score += 10
                long_reasons.append(
                    f"Healthy bullish RSI: {rsi:.2f}"
                )

            elif 40 <= rsi < 50:
                long_score += 5
                long_reasons.append(
                    f"Recovering bullish RSI: {rsi:.2f}"
                )

            elif rsi >= 75:
                long_score -= 10
                long_reasons.append(
                    f"LONG penalty - RSI overextended: {rsi:.2f}"
                )

        # RSI confirmation for SHORT
        if bearish_context:
            if 35 <= rsi <= 50:
                short_score += 10
                short_reasons.append(
                    f"Healthy bearish RSI: {rsi:.2f}"
                )

            elif 50 < rsi <= 60:
                short_score += 5
                short_reasons.append(
                    f"Bearish pullback RSI: {rsi:.2f}"
                )

            elif rsi <= 25:
                short_score -= 10
                short_reasons.append(
                    f"SHORT penalty - RSI oversold: {rsi:.2f}"
                )

        # News direction
        if news_score >= 0.6:
            long_score += 25
            long_reasons.append(
                f"Strong positive news: {news_score:.2f}"
            )

        elif news_score >= 0.2:
            long_score += 15
            long_reasons.append(
                f"Positive news: {news_score:.2f}"
            )

        elif news_score <= -0.6:
            short_score += 25
            short_reasons.append(
                f"Strong negative news: {news_score:.2f}"
            )

        elif news_score <= -0.2:
            short_score += 15
            short_reasons.append(
                f"Negative news: {news_score:.2f}"
            )

        if has_critical_news:
            return {
                "symbol": symbol,
                "action": "WAIT",
                "confidence": 0.0,
                "long_score": round(long_score, 2),
                "short_score": round(short_score, 2),
                "long_reasons": long_reasons,
                "short_reasons": short_reasons,
                "final_score": 0.0,
            }

        if earnings_soon:
            return {
                "symbol": symbol,
                "action": "WAIT",
                "confidence": 0.0,
                "long_score": round(long_score, 2),
                "short_score": round(short_score, 2),
                "long_reasons": long_reasons,
                "short_reasons": short_reasons,
                "final_score": 0.0,
            }

        # Fundamental direction
        if fundamental_score >= 75:
            long_score += 20
            long_reasons.append(
                f"Strong fundamentals: {fundamental_score:.1f}"
            )

        elif fundamental_score >= 60:
            long_score += 10
            long_reasons.append(
                f"Positive fundamentals: {fundamental_score:.1f}"
            )

        elif fundamental_score <= 35:
            short_score += 20
            short_reasons.append(
                f"Weak fundamentals: {fundamental_score:.1f}"
            )

        elif fundamental_score <= 50:
            short_score += 10
            short_reasons.append(
                f"Negative fundamentals: {fundamental_score:.1f}"
            )
            # Technical confirmation bonus
        if technical_score >= 90:
            technical_bonus = 10
        elif technical_score >= 80:
            technical_bonus = 7
        elif technical_score >= 70:
            technical_bonus = 4
        else:
            technical_bonus = 0

        if technical_bonus > 0:
            if long_score > short_score:
                long_score += technical_bonus
                long_reasons.append(
                    f"Technical confirmation bonus: +{technical_bonus}"
                )

            elif short_score > long_score:
                short_score += technical_bonus
                short_reasons.append(
                    f"Technical confirmation bonus: +{technical_bonus}"
                )

               # Final directional decision
        action = "WAIT"
        confidence = max(long_score, short_score)

        score_gap = abs(long_score - short_score)

        long_evidence_count = len(long_reasons)
        short_evidence_count = len(short_reasons)

        if (
            long_score >= 60
            and long_score > short_score
            and score_gap >= 15
            and long_evidence_count >= 3
        ):
            action = "LONG"
            confidence = long_score

        elif (
            short_score >= 60
            and short_score > long_score
            and score_gap >= 15
            and short_evidence_count >= 3
        ):
            action = "SHORT"
            confidence = short_score

        # Entry quality filter
        entry_action = "WAIT"
        entry_reasons = []

        if action == "LONG":
            if rsi is not None and rsi >= 72:
                entry_reasons.append(
                    f"RSI too extended for LONG entry: {rsi:.2f}"
                )

            if (
                price is not None
                and ema20 is not None
                and ema20 > 0
            ):
                distance_from_ema20 = ((price - ema20) / ema20) * 100

                if distance_from_ema20 >= 2.0:
                    entry_reasons.append(
                        f"Price too extended above EMA20: {distance_from_ema20:.2f}%"
                    )

        elif action == "SHORT":
            if rsi is not None and rsi <= 28:
                entry_reasons.append(
                    f"RSI too extended for SHORT entry: {rsi:.2f}"
                )

            if (
                price is not None
                and ema20 is not None
                and ema20 > 0
            ):
                distance_from_ema20 = ((ema20 - price) / ema20) * 100

                if distance_from_ema20 >= 2.0:
                    entry_reasons.append(
                        f"Price too extended below EMA20: {distance_from_ema20:.2f}%"
                    )

        # Final entry decision
        if action == "LONG":
            if len(entry_reasons) == 0:
                entry_action = "ENTER_LONG"
            else:
                entry_action = "WAIT_FOR_PULLBACK"

        elif action == "SHORT":
            if len(entry_reasons) == 0:
                entry_action = "ENTER_SHORT"
            else:
                entry_action = "WAIT_FOR_PULLBACK"

        else:
            entry_action = "WAIT"

        # Compatibility score for the rest of the program
        final_score = confidence

        return {
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 2),
            "long_score": round(long_score, 2),
            "short_score": round(short_score, 2),
            "score_gap": round(score_gap, 2),
            "long_evidence_count": long_evidence_count,
            "short_evidence_count": short_evidence_count,
            "long_reasons": long_reasons,
            "short_reasons": short_reasons,
            "entry_action": entry_action,
            "entry_reasons": entry_reasons,
            "final_score": round(final_score, 2),
        }