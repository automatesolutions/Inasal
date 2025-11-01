"""Evaluation script for LLM response quality and safety"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List
from langchain_openai import ChatOpenAI

from app.config import settings
from app.rag_engine import RAGEngine
from app.chat_agent import ChatAgent


class LLMEvaluator:
    """Evaluator for LLM response quality and safety"""

    def __init__(self):
        self.rag_engine = RAGEngine()
        self.chat_agent = ChatAgent()

    def evaluate_response_quality(self, response: str, query: str) -> Dict:
        """Evaluate response quality metrics"""
        metrics = {
            "length": len(response),
            "word_count": len(response.split()),
            "has_local_context": any(
                keyword in response.lower()
                for keyword in ["bacolod", "negros", "philippines", "local"]
            ),
            "has_recommendation": any(
                keyword in response.lower()
                for keyword in ["recommend", "suggest", "visit", "try", "should"]
            ),
            "tone_check": self._check_tone(response),
        }
        return metrics

    def _check_tone(self, response: str) -> Dict:
        """Check if response maintains friendly local guide tone"""
        friendly_words = [
            "welcome",
            "friendly",
            "enjoy",
            "wonderful",
            "amazing",
            "great",
            "love",
        ]
        has_friendly_tone = any(word in response.lower() for word in friendly_words)

        return {
            "friendly": has_friendly_tone,
            "appropriate": True,  # Basic check - can be enhanced
        }

    async def evaluate_safety(self, response: str) -> Dict:
        """Evaluate response safety (content moderation)"""
        # Basic safety checks
        safety_metrics = {
            "contains_offensive_language": False,  # TODO: Implement actual check
            "contains_sensitive_info": False,
            "appropriate_length": 50 < len(response) < 2000,
        }

        # Check for potential sensitive information leaks
        sensitive_patterns = ["password", "api_key", "secret", "token"]
        if any(pattern in response.lower() for pattern in sensitive_patterns):
            safety_metrics["contains_sensitive_info"] = True

        return safety_metrics

    async def run_evaluation_suite(self, test_queries: List[str]) -> Dict:
        """Run evaluation suite on test queries"""
        results = []

        for query in test_queries:
            # Get response from RAG engine
            rag_response = await self.rag_engine.get_local_tips(query)

            # Evaluate quality
            quality_metrics = self.evaluate_response_quality(rag_response, query)
            safety_metrics = await self.evaluate_safety(rag_response)

            results.append(
                {
                    "query": query,
                    "response": rag_response,
                    "quality": quality_metrics,
                    "safety": safety_metrics,
                }
            )

        # Calculate aggregate scores
        avg_quality = {
            "avg_length": sum(r["quality"]["length"] for r in results) / len(results),
            "avg_word_count": sum(r["quality"]["word_count"] for r in results)
            / len(results),
            "local_context_rate": sum(
                1 for r in results if r["quality"]["has_local_context"]
            )
            / len(results),
            "recommendation_rate": sum(
                1 for r in results if r["quality"]["has_recommendation"]
            )
            / len(results),
        }

        return {
            "total_tests": len(test_queries),
            "results": results,
            "aggregate_scores": avg_quality,
        }

    def save_evaluation_report(self, evaluation: Dict, output_path: str):
        """Save evaluation report to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)

        print(f"✅ Evaluation report saved to {output_file}")


async def main():
    """Main evaluation function"""
    evaluator = LLMEvaluator()

    # Test queries covering different scenarios
    test_queries = [
        "What's the weather like in Bacolod?",
        "What should I pack for my trip?",
        "What are the best places to visit?",
        "Tell me about local food",
        "Are there any festivals happening?",
        "What's a hidden gem in Bacolod?",
    ]

    print("🚀 Running LLM response evaluation suite...")
    print(f"Testing {len(test_queries)} queries...\n")

    evaluation = await evaluator.run_evaluation_suite(test_queries)

    # Print summary
    print("\n📊 Evaluation Summary:")
    print(f"Total Tests: {evaluation['total_tests']}")
    print(
        f"Average Response Length: {evaluation['aggregate_scores']['avg_length']:.0f} chars"
    )
    print(
        f"Local Context Rate: {evaluation['aggregate_scores']['local_context_rate']*100:.1f}%"
    )
    print(
        f"Recommendation Rate: {evaluation['aggregate_scores']['recommendation_rate']*100:.1f}%"
    )

    # Save detailed report
    evaluator.save_evaluation_report(evaluation, "data/evaluation_report.json")


if __name__ == "__main__":
    asyncio.run(main())

