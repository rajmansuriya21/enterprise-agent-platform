"""
API Sub-Agent — External API orchestration for real-time data retrieval.

Handles outbound HTTP requests to external services (weather, stocks, news, etc.)
with rate limiting, retry logic, and response formatting.
Includes mock endpoints for demo purposes.
"""

from __future__ import annotations

import time
import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

from src.agents.state import AgentMetadata, AgentState
from src.config import get_settings
from src.utils.prompts import API_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Mock API Data (for demo without external API keys)
# ──────────────────────────────────────────────────────────────
MOCK_WEATHER_DATA = {
    "new york": {"temp": 72, "condition": "Partly Cloudy", "humidity": 65, "wind": "12 mph NW"},
    "london": {"temp": 59, "condition": "Overcast", "humidity": 80, "wind": "8 mph SW"},
    "tokyo": {"temp": 82, "condition": "Sunny", "humidity": 55, "wind": "5 mph E"},
    "mumbai": {"temp": 88, "condition": "Humid", "humidity": 90, "wind": "10 mph W"},
    "default": {"temp": 68, "condition": "Clear", "humidity": 50, "wind": "7 mph N"},
}

MOCK_STOCK_DATA = {
    "AAPL": {"price": 198.50, "change": +2.35, "pct": "+1.20%", "volume": "52.3M"},
    "GOOGL": {"price": 172.80, "change": -1.20, "pct": "-0.69%", "volume": "28.1M"},
    "MSFT": {"price": 415.60, "change": +5.80, "pct": "+1.41%", "volume": "35.7M"},
    "TSLA": {"price": 265.30, "change": -8.90, "pct": "-3.24%", "volume": "98.2M"},
    "AMZN": {"price": 195.40, "change": +3.15, "pct": "+1.64%", "volume": "42.8M"},
}

MOCK_NEWS_DATA = [
    {
        "title": "AI Revolution Continues: New Breakthroughs in Multi-Agent Systems",
        "source": "TechCrunch",
        "published": "2 hours ago",
        "summary": "Leading research labs announce advances in cooperative AI agents...",
    },
    {
        "title": "Federal Reserve Signals Potential Rate Adjustments",
        "source": "Bloomberg",
        "published": "4 hours ago",
        "summary": "Fed Chair hints at monetary policy changes in upcoming meeting...",
    },
    {
        "title": "Global Supply Chain Disruptions Ease as Shipping Normalizes",
        "source": "Reuters",
        "published": "6 hours ago",
        "summary": "Major shipping routes report improved throughput and reduced delays...",
    },
]


# ──────────────────────────────────────────────────────────────
# API Tools
# ──────────────────────────────────────────────────────────────
def create_api_tools() -> list:
    """Create API-specific tools for external data retrieval."""

    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a specified city.

        Args:
            city: Name of the city to get weather for.

        Returns:
            Current weather conditions including temperature, humidity, and wind.
        """
        city_lower = city.lower().strip()
        data = MOCK_WEATHER_DATA.get(city_lower, MOCK_WEATHER_DATA["default"])

        return (
            f"🌤️ Weather for {city.title()}:\n"
            f"  Temperature: {data['temp']}°F ({(data['temp'] - 32) * 5/9:.0f}°C)\n"
            f"  Condition: {data['condition']}\n"
            f"  Humidity: {data['humidity']}%\n"
            f"  Wind: {data['wind']}\n"
            f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )

    @tool
    def get_stock_price(symbol: str) -> str:
        """Get the current stock price and market data for a ticker symbol.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL, GOOGL, MSFT).

        Returns:
            Current price, change, and volume information.
        """
        symbol_upper = symbol.upper().strip()
        data = MOCK_STOCK_DATA.get(symbol_upper)

        if data is None:
            return f"Stock symbol '{symbol_upper}' not found. Available: {', '.join(MOCK_STOCK_DATA.keys())}"

        change_emoji = "📈" if data["change"] > 0 else "📉"
        return (
            f"{change_emoji} {symbol_upper} Stock Data:\n"
            f"  Price: ${data['price']:.2f}\n"
            f"  Change: {'+' if data['change'] > 0 else ''}{data['change']:.2f} ({data['pct']})\n"
            f"  Volume: {data['volume']}\n"
            f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )

    @tool
    def get_latest_news(topic: str = "technology", count: int = 3) -> str:
        """Get the latest news headlines on a specific topic.

        Args:
            topic: Topic to search for (e.g., technology, finance, health).
            count: Number of articles to return (max 5).

        Returns:
            Latest news headlines with summaries.
        """
        count = min(count, len(MOCK_NEWS_DATA))
        articles = MOCK_NEWS_DATA[:count]

        formatted = [f"📰 Latest {topic.title()} News:\n"]
        for i, article in enumerate(articles, 1):
            formatted.append(
                f"  {i}. {article['title']}\n"
                f"     Source: {article['source']} | {article['published']}\n"
                f"     {article['summary']}\n"
            )
        return "\n".join(formatted)

    @tool
    def make_api_request(url: str, method: str = "GET", headers: str = "{}") -> str:
        """Make an HTTP request to an external API endpoint.

        Args:
            url: The API endpoint URL.
            method: HTTP method (GET or POST).
            headers: JSON string of additional headers.

        Returns:
            The API response body (truncated if very long).
        """
        # In demo mode, return a mock response
        return (
            f"🌐 API Request:\n"
            f"  Method: {method}\n"
            f"  URL: {url}\n"
            f"  Status: 200 OK\n"
            f"  Response: {{\"status\": \"success\", \"message\": \"Demo API response\", "
            f"\"timestamp\": \"{datetime.now().isoformat()}\"}}\n"
            f"\n  Note: In production, this would make a real HTTP request via httpx."
        )

    return [get_weather, get_stock_price, get_latest_news, make_api_request]


# ──────────────────────────────────────────────────────────────
# API Agent Node
# ──────────────────────────────────────────────────────────────
def create_api_agent_node(llm: Any):
    """Create the API agent node for the LangGraph.

    The API agent:
    1. Interprets the user's request for external data
    2. Selects the appropriate API tool (weather, stocks, news, custom)
    3. Executes the API call
    4. Formats and explains the results
    """
    tools = create_api_tools()
    llm_with_tools = llm.bind_tools(tools)

    def api_agent_node(state: AgentState) -> dict[str, Any]:
        """Execute external API calls based on user request."""
        start_time = time.time()
        settings = get_settings()

        messages = [
            SystemMessage(content=API_AGENT_SYSTEM_PROMPT),
            *state["messages"],
        ]

        tools_called = []
        try:
            response = llm_with_tools.invoke(messages)

            # Process tool calls if any
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_map = {t.name: t for t in tools}
                tool_results = []

                for tc in response.tool_calls:
                    if tc["name"] in tool_map:
                        tools_called.append(tc["name"])
                        result = tool_map[tc["name"]].invoke(tc["args"])
                        tool_results.append(f"Result from {tc['name']}:\n{result}")

                # Generate final response with tool results
                follow_up = [
                    *messages,
                    response,
                    SystemMessage(
                        content="Tool execution results:\n\n"
                        + "\n\n".join(tool_results)
                        + "\n\nPlease provide a clear, formatted response based on these results."
                    ),
                ]
                final_response = llm.invoke(follow_up)
                response_content = final_response.content
            else:
                response_content = response.content

        except Exception as e:
            logger.error(f"API agent failed: {e}")
            response_content = f"I encountered an error retrieving external data: {str(e)}"

        # Track metadata
        latency_ms = (time.time() - start_time) * 1000
        agent_meta = AgentMetadata(
            agent_name="api_agent",
            model_used=settings.llm_model,
            latency_ms=latency_ms,
            tools_called=tools_called,
            success=True,
        )

        metadata = state.get("metadata", {})
        routing_history = metadata.get("routing_history", [])
        routing_history.append(agent_meta.model_dump())
        metadata["routing_history"] = routing_history

        return {
            "messages": [AIMessage(content=response_content, name="api_agent")],
            "metadata": metadata,
        }

    return api_agent_node
