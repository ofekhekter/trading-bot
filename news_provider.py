from datetime import datetime


class NewsProvider:
    def get_company_news(self, symbol: str) -> list[dict]:
        """
        Temporary mock data.

        Later this function will request real news
        from IBKR / another news provider.
        """

        return [
            {
                "symbol": symbol,
                "headline": f"{symbol} reports strong demand",
                "source": "TEST",
                "published_at": datetime.now(),
            },
            {
                "symbol": symbol,
                "headline": f"{symbol} beats estimates and raises guidance",
                "source": "TEST",
                "published_at": datetime.now(),
            },
        ]