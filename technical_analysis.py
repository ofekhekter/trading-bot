from typing import List


class TechnicalAnalyzer:
    def ema(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices")

        multiplier = 2 / (period + 1)
        ema_value = sum(prices[:period]) / period

        for price in prices[period:]:
            ema_value = (
                price * multiplier
                + ema_value * (1 - multiplier)
            )

        return ema_value

    def rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            raise ValueError(f"Need at least {period + 1} prices")

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]

            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        recent_gains = gains[-period:]
        recent_losses = losses[-period:]

        avg_gain = sum(recent_gains) / period
        avg_loss = sum(recent_losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def momentum_percent(
        self,
        prices: List[float],
        lookback: int = 10
    ) -> float:
        if len(prices) <= lookback:
            raise ValueError(
                f"Need more than {lookback} prices"
            )

        old_price = prices[-lookback - 1]
        current_price = prices[-1]

        return (
            (current_price - old_price)
            / old_price
        ) * 100

    def calculate_score(
        self,
        prices: List[float]
    ) -> dict:

        current_price = prices[-1]

        ema20 = self.ema(prices, 20)
        ema50 = self.ema(prices, 50)
        rsi14 = self.rsi(prices, 14)
        momentum = self.momentum_percent(
            prices,
            lookback=10
        )

        score = 50

        if current_price > ema20:
            score += 10
        else:
            score -= 10

        if ema20 > ema50:
            score += 15
        else:
            score -= 15

        if 50 <= rsi14 <= 70:
            score += 15

        elif 40 <= rsi14 < 50:
            score += 5

        elif rsi14 > 75:
            score -= 10

        elif rsi14 < 35:
            score -= 10

        if momentum > 2:
            score += 10

        elif momentum < -2:
            score -= 10

        score = max(0, min(100, score))

        return {
            "current_price": round(current_price, 2),
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "rsi14": round(rsi14, 2),
            "momentum_percent": round(momentum, 2),
            "technical_score": score,
        }