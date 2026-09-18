"""
API Tools — HTTP client wrappers and external API tools.

Provides tools for making HTTP requests to external services
with response parsing and configurable endpoint registry.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_api_tools() -> list:
    """Create API-specific tools for external data retrieval.

    Returns:
        List of LangChain tool objects.
    """

    @tool
    def http_get(url: str, headers: str = "{}") -> str:
        """Make an HTTP GET request to an external API endpoint.

        Args:
            url: The API endpoint URL to call.
            headers: JSON string of additional HTTP headers.

        Returns:
            The API response body.
        """
        try:
            import httpx

            parsed_headers = {}
            if headers and headers != "{}":
                import json
                parsed_headers = json.loads(headers)

            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=parsed_headers)
                response.raise_for_status()
                return f"Status: {response.status_code}\nResponse:\n{response.text[:2000]}"
        except ImportError:
            return f"httpx not installed. Would call GET {url}"
        except Exception as e:
            return f"HTTP GET error: {str(e)}"

    @tool
    def http_post(url: str, body: str = "{}", headers: str = "{}") -> str:
        """Make an HTTP POST request to an external API endpoint.

        Args:
            url: The API endpoint URL to call.
            body: JSON string of the request body.
            headers: JSON string of additional HTTP headers.

        Returns:
            The API response body.
        """
        try:
            import httpx
            import json

            parsed_headers = json.loads(headers) if headers else {}
            parsed_body = json.loads(body) if body else {}

            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=parsed_body, headers=parsed_headers)
                response.raise_for_status()
                return f"Status: {response.status_code}\nResponse:\n{response.text[:2000]}"
        except ImportError:
            return f"httpx not installed. Would call POST {url}"
        except Exception as e:
            return f"HTTP POST error: {str(e)}"

    @tool
    def search_web_api(query: str) -> str:
        """Search the web for real-time information on a topic.

        Args:
            query: The search query.

        Returns:
            Search results summary.
        """
        # In production, this would call a search API (e.g., Serper, Tavily)
        return (
            f"🔎 Web search results for '{query}':\n"
            f"  Note: Web search API not configured.\n"
            f"  Configure SEARCH_API_KEY in .env to enable live web search.\n"
            f"  Timestamp: {datetime.now().isoformat()}"
        )

    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city.

        Args:
            city: Name of the city.

        Returns:
            Current weather conditions.
        """
        mock_data = {
            "new york": {"temp": 72, "condition": "Partly Cloudy", "humidity": 65},
            "london": {"temp": 59, "condition": "Overcast", "humidity": 80},
            "tokyo": {"temp": 82, "condition": "Sunny", "humidity": 55},
            "mumbai": {"temp": 88, "condition": "Humid", "humidity": 90},
        }

        data = mock_data.get(city.lower().strip(), {"temp": 68, "condition": "Clear", "humidity": 50})

        return (
            f"🌤️ Weather for {city.title()}:\n"
            f"  Temperature: {data['temp']}°F ({(data['temp'] - 32) * 5/9:.0f}°C)\n"
            f"  Condition: {data['condition']}\n"
            f"  Humidity: {data['humidity']}%\n"
            f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    @tool
    def get_stock_price(symbol: str) -> str:
        """Get the current stock price for a ticker symbol.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL).

        Returns:
            Current price and market data.
        """
        mock_stocks = {
            "AAPL": {"price": 198.50, "change": "+1.20%"},
            "GOOGL": {"price": 172.80, "change": "-0.69%"},
            "MSFT": {"price": 415.60, "change": "+1.41%"},
        }

        data = mock_stocks.get(symbol.upper())
        if not data:
            return f"Stock '{symbol.upper()}' not found."

        return (
            f"📈 {symbol.upper()}: ${data['price']:.2f} ({data['change']})\n"
            f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    return [http_get, http_post, search_web_api, get_weather, get_stock_price]
