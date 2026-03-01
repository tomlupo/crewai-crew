"""Custom YFinance tool for fetching stock/financial data."""


from crewai.tools import BaseTool


class YFinanceTool(BaseTool):
    name: str = "YFinance Stock Data"
    description: str = (
        "Fetch stock market data and financial metrics for a given ticker symbol. "
        "Returns current price, valuation metrics, price performance, and optionally "
        "full financial statements. Use this for any quantitative financial research."
    )

    def _run(
        self,
        ticker: str,
        period: str = "3mo",
        include_financials: bool = False,
    ) -> str:
        """Fetch stock data for the given ticker.

        Args:
            ticker: Stock ticker symbol (e.g. NVDA, AAPL, MSFT).
            period: Price history period — 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max.
            include_financials: If True, include full income statement and balance sheet.
        """
        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance is not installed. Run: pip install yfinance"

        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info

            if (
                not info
                or info.get("trailingPegRatio") is None
                and info.get("currentPrice") is None
            ):
                # Minimal check — yfinance returns an empty-ish dict for invalid tickers
                pass

            # --- Core metrics ---
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            lines = [
                f"=== {ticker.upper()} Summary ===",
                f"Name: {info.get('shortName', 'N/A')}",
                f"Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}",
                f"Current Price: ${current_price}"
                if current_price
                else "Current Price: N/A",
                f"Market Cap: ${info.get('marketCap', 'N/A'):,}"
                if info.get("marketCap")
                else "Market Cap: N/A",
                f"52-Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}",
                f"P/E (Trailing): {info.get('trailingPE', 'N/A')}",
                f"P/E (Forward): {info.get('forwardPE', 'N/A')}",
                f"EPS (Trailing): {info.get('trailingEps', 'N/A')}",
                f"EPS (Forward): {info.get('forwardEps', 'N/A')}",
                f"Revenue (TTM): ${info.get('totalRevenue', 'N/A'):,}"
                if info.get("totalRevenue")
                else "Revenue (TTM): N/A",
                f"Gross Margin: {info.get('grossMargins', 'N/A')}",
                f"Operating Margin: {info.get('operatingMargins', 'N/A')}",
                f"Profit Margin: {info.get('profitMargins', 'N/A')}",
                f"Free Cash Flow: ${info.get('freeCashflow', 'N/A'):,}"
                if info.get("freeCashflow")
                else "Free Cash Flow: N/A",
                f"Beta: {info.get('beta', 'N/A')}",
                f"Dividend Yield: {info.get('dividendYield', 'N/A')}",
            ]

            # --- Price history ---
            hist = stock.history(period=period)
            if not hist.empty:
                start_price = hist["Close"].iloc[0]
                end_price = hist["Close"].iloc[-1]
                change_pct = ((end_price - start_price) / start_price) * 100
                lines.append(f"\n=== Price Performance ({period}) ===")
                lines.append(f"Start: ${start_price:.2f} | End: ${end_price:.2f}")
                lines.append(f"Change: {change_pct:+.2f}%")
                lines.append(f"Period High: ${hist['Close'].max():.2f}")
                lines.append(f"Period Low: ${hist['Close'].min():.2f}")

            # --- Full financials (optional) ---
            if include_financials:
                income = stock.income_stmt
                if income is not None and not income.empty:
                    lines.append("\n=== Income Statement (Recent Quarters) ===")
                    lines.append(income.to_string())

                balance = stock.balance_sheet
                if balance is not None and not balance.empty:
                    lines.append("\n=== Balance Sheet ===")
                    lines.append(balance.to_string())

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching data for {ticker}: {type(e).__name__}: {e}"
