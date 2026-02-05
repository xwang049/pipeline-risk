"""Prompt templates for credit risk prediction"""

from typing import Dict, Any


class PromptTemplates:
    """Templates for various LLM prompts"""

    @staticmethod
    def credit_risk_analysis_prompt(company_data: Dict[str, Any]) -> str:
        """
        Generate a comprehensive credit risk analysis prompt

        Args:
            company_data: Dictionary containing company information
                - ticker: Company ticker symbol
                - name: Company name
                - financial_metrics: Dict of financial ratios
                - recent_news: List of recent news articles
                - market_data: Dict of market indicators
                - network_info: (optional) Network relationships

        Returns:
            Formatted prompt string
        """
        ticker = company_data.get("ticker", "Unknown")
        name = company_data.get("name", "Unknown Company")
        financial_metrics = company_data.get("financial_metrics", {})
        recent_news = company_data.get("recent_news", [])
        market_data = company_data.get("market_data", {})

        prompt = f"""You are a senior credit risk analyst. Analyze the following company and predict its credit risk for the next 7 days.

Company: {name} ({ticker})

## Financial Metrics:
{PromptTemplates._format_financial_metrics(financial_metrics)}

## Market Data:
{PromptTemplates._format_market_data(market_data)}

## Recent News (Last 7 Days):
{PromptTemplates._format_news(recent_news)}

## Analysis Required:

1. **Risk Score (0-100)**: Provide a numerical risk score where:
   - 0-20: Very Low Risk
   - 21-40: Low Risk
   - 41-60: Moderate Risk
   - 61-80: High Risk
   - 81-100: Very High Risk

2. **Key Risk Factors**: Identify the top 3-5 factors contributing to credit risk

3. **Early Warning Signals**: Highlight any red flags or concerning trends

4. **Probability of Adverse Event**: Estimate the probability of:
   - Rating downgrade
   - Significant price drop (>20%)
   - Liquidity issues
   - Default risk

5. **Confidence Level**: Rate your confidence in this assessment (Low/Medium/High)

Please provide your analysis in a structured JSON format:
```json
{{
    "risk_score": <0-100>,
    "risk_level": "<Very Low/Low/Moderate/High/Very High>",
    "key_risk_factors": [
        "factor 1",
        "factor 2",
        "factor 3"
    ],
    "early_warning_signals": [
        "signal 1",
        "signal 2"
    ],
    "adverse_event_probabilities": {{
        "rating_downgrade": <0-1>,
        "price_drop_20pct": <0-1>,
        "liquidity_issues": <0-1>,
        "default_risk": <0-1>
    }},
    "confidence_level": "<Low/Medium/High>",
    "reasoning": "Brief explanation of your analysis"
}}
```
"""
        return prompt

    @staticmethod
    def _format_financial_metrics(metrics: Dict[str, Any]) -> str:
        """Format financial metrics for display"""
        if not metrics:
            return "No financial data available"

        lines = []
        for key, value in metrics.items():
            if value is not None:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines) if lines else "No financial data available"

    @staticmethod
    def _format_market_data(data: Dict[str, Any]) -> str:
        """Format market data for display"""
        if not data:
            return "No market data available"

        lines = []
        for key, value in data.items():
            if value is not None:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines) if lines else "No market data available"

    @staticmethod
    def _format_news(news_list: list) -> str:
        """Format news articles for display"""
        if not news_list:
            return "No recent news available"

        lines = []
        for i, article in enumerate(news_list[:10], 1):  # Limit to top 10
            title = article.get("title", "Untitled")
            date = article.get("date", "Unknown date")
            summary = article.get("summary", "")

            lines.append(f"{i}. [{date}] {title}")
            if summary:
                lines.append(f"   Summary: {summary[:200]}...")

        return "\n".join(lines) if lines else "No recent news available"

    @staticmethod
    def comparative_analysis_prompt(companies_data: list) -> str:
        """
        Generate a prompt for comparing multiple companies

        Args:
            companies_data: List of company data dictionaries

        Returns:
            Formatted prompt for comparative analysis
        """
        prompt = """You are a portfolio risk manager. Compare the following companies and rank them by credit risk.

Companies to analyze:
"""
        for i, company in enumerate(companies_data, 1):
            ticker = company.get("ticker", "Unknown")
            name = company.get("name", "Unknown")
            prompt += f"\n{i}. {name} ({ticker})"

        prompt += """

Please provide:
1. Risk ranking (most risky to least risky)
2. Comparative risk analysis
3. Sector-specific considerations
4. Portfolio-level risk assessment

Output in JSON format with rankings and explanations.
"""
        return prompt
