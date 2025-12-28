"""LangGraph workflow orchestrating persona discovery and travel research."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.bright_data_client import bright_data_client
from app.llm_factory import get_chat_llm
from app.prompts import (
    BING_FINAL_ANALYSIS_PROMPT,
    BING_PERSONALITY_ANALYSIS_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
    GOOGLE_FINAL_ANALYSIS_PROMPT,
    GOOGLE_PERSONALITY_ANALYSIS_PROMPT,
    INTEREST_EXPLORATION_PROMPT,
    REDDIT_FINAL_ANALYSIS_PROMPT,
    REDDIT_PERSONALITY_ANALYSIS_PROMPT,
    REDDIT_URL_SELECTION_PROMPT,
)

logger = logging.getLogger(__name__)


def _keep_existing(old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return old if old is not None else new


def _set_latest(_old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return new


def _extend_list(old: Optional[List[Any]], new: Optional[List[Any]]) -> List[Any]:
    combined = list(old or [])
    combined.extend(new or [])
    return combined


def _merge_dicts(old: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(old or {})
    for key, value in (new or {}).items():
        merged[key] = value
    return merged


def _merge_dicts_of_lists(
    old: Optional[Dict[str, List[Any]]],
    new: Optional[Dict[str, List[Any]]],
) -> Dict[str, List[Any]]:
    merged: Dict[str, List[Any]] = {key: list(values) for key, values in (old or {}).items()}
    for key, values in (new or {}).items():
        merged.setdefault(key, [])
        merged[key].extend(values or [])
    return merged


class PersonaDiscoveryState(TypedDict, total=False):
    """State container for the persona discovery LangGraph pipeline."""

    user_id: Annotated[str, _keep_existing]
    email: Annotated[str, _keep_existing]
    first_name: Annotated[str, _keep_existing]
    last_name: Annotated[str, _keep_existing]
    full_name: Annotated[str, _keep_existing]
    search_queries: Annotated[Dict[str, str], _merge_dicts]
    search_results: Annotated[Dict[str, Any], _merge_dicts]
    search_completion: Annotated[List[str], _extend_list]
    search_ready: Annotated[bool, _set_latest]
    bright_data_profile: Annotated[Dict[str, Any], _merge_dicts]
    collected_comments: Annotated[Dict[str, List[str]], _merge_dicts_of_lists]
    initial_analyses: Annotated[Dict[str, Any], _merge_dicts]
    final_analyses: Annotated[Dict[str, Any], _merge_dicts]
    personality_traits: Annotated[Dict[str, float], _merge_dicts]
    planning_profile: Annotated[Dict[str, Any], _merge_dicts]
    community_signals: Annotated[Dict[str, Any], _merge_dicts]
    interest_queries: Annotated[Dict[str, List[str]], _merge_dicts_of_lists]
    interest_results: Annotated[Dict[str, Any], _merge_dicts]
    unspoken_hook: Annotated[str, _set_latest]
    reddit_urls: Annotated[List[str], _set_latest]
    reddit_url_rationale: Annotated[List[str], _set_latest]
    reddit_comments: Annotated[Dict[str, List[str]], _merge_dicts_of_lists]
    final_output: Annotated[Dict[str, Any], _merge_dicts]
    errors: Annotated[List[str], _extend_list]
    log: Annotated[List[str], _extend_list]


class PersonaDiscoveryWorkflow:
    """Configures and executes the multi-stage LangGraph workflow."""

    def __init__(self) -> None:
        self._llm = get_chat_llm(temperature=0.25)
        self.graph = self._build_graph()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def run(
        self,
        *,
        user_id: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> PersonaDiscoveryState:
        """Execute the full persona discovery flow."""
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        initial_state: PersonaDiscoveryState = {
            "user_id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name or email,
        }
        return await self.graph.ainvoke(initial_state)

    # ------------------------------------------------------------------ #
    # Graph Definition
    # ------------------------------------------------------------------ #
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(PersonaDiscoveryState)

        workflow.add_node("initialize", self._initialize_state)
        workflow.add_node("google_search", self._google_search)
        workflow.add_node("reddit_search", self._reddit_search)
        workflow.add_node("facebook_search", self._facebook_search)
        workflow.add_node("search_barrier", self._search_barrier)
        workflow.add_node("data_retrieval", self._retrieve_profile_details)
        workflow.add_node("google_analysis", self._google_analysis)
        workflow.add_node("bing_analysis", self._bing_analysis)
        workflow.add_node("reddit_analysis", self._reddit_analysis)
        workflow.add_node("interest_exploration", self._interest_exploration)
        workflow.add_node("reddit_url_selection", self._reddit_url_selection)
        workflow.add_node("reddit_comment_retrieval", self._reddit_comment_retrieval)
        workflow.add_node("google_final_analysis", self._google_final_analysis)
        workflow.add_node("bing_final_analysis", self._bing_final_analysis)
        workflow.add_node("reddit_final_analysis", self._reddit_final_analysis)
        workflow.add_node("final_synthesis", self._final_synthesis)

        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "google_search")
        workflow.add_edge("initialize", "reddit_search")
        workflow.add_edge("initialize", "facebook_search")

        workflow.add_edge("google_search", "search_barrier")
        workflow.add_edge("reddit_search", "search_barrier")
        workflow.add_edge("facebook_search", "search_barrier")

        workflow.add_edge("search_barrier", "data_retrieval")
        workflow.add_edge("data_retrieval", "google_analysis")
        workflow.add_edge("google_analysis", "bing_analysis")
        workflow.add_edge("bing_analysis", "reddit_analysis")
        workflow.add_edge("reddit_analysis", "interest_exploration")
        workflow.add_edge("interest_exploration", "reddit_url_selection")
        workflow.add_edge("reddit_url_selection", "reddit_comment_retrieval")
        workflow.add_edge("reddit_comment_retrieval", "google_final_analysis")
        workflow.add_edge("google_final_analysis", "bing_final_analysis")
        workflow.add_edge("bing_final_analysis", "reddit_final_analysis")
        workflow.add_edge("reddit_final_analysis", "final_synthesis")
        workflow.add_edge("final_synthesis", END)

        return workflow.compile()

    # ------------------------------------------------------------------ #
    # Graph Nodes
    # ------------------------------------------------------------------ #
    async def _initialize_state(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        full_name = state.get("full_name") or state.get("email")
        return {
            "search_queries": {
                "google": f'"{full_name}" travel preferences "{state.get("email")}"',
                "reddit": f'{full_name} travel recommendations Bacolod',
                "facebook": f'{full_name} Bacolod traveler stories',
            },
            "log": ["Initialized persona discovery workflow."],
        }

    async def _google_search(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        query = state.get("search_queries", {}).get("google", state.get("full_name", ""))
        response = await bright_data_client.search_public("google", query, limit=6)
        return self._build_search_update("google", response)

    async def _reddit_search(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        query = state.get("search_queries", {}).get("reddit", state.get("full_name", ""))
        response = await bright_data_client.search_public("reddit", query, limit=6)
        return self._build_search_update("reddit", response)

    async def _facebook_search(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        query = state.get("search_queries", {}).get("facebook", state.get("full_name", ""))
        response = await bright_data_client.search_public("facebook", query, limit=4)
        return self._build_search_update("facebook", response)

    async def _search_barrier(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        expected = {"google", "reddit", "facebook"}
        completed = set(state.get("search_completion", []))
        remaining = expected - completed
        ready = not remaining
        message = (
            "Initial parallel searches complete."
            if ready
            else f"Waiting on searches: {', '.join(sorted(remaining))}"
        )
        return {"search_ready": ready, "log": [message]}

    async def _retrieve_profile_details(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        if not state.get("search_ready"):
            return {}

        handles = self._extract_handles(state)
        response = await bright_data_client.fetch_person_details(
            email=state["email"],
            full_name=state["full_name"],
            handles=handles if handles else None,
        )
        if response.get("success"):
            update: PersonaDiscoveryState = {
                "bright_data_profile": response,
                "log": ["Retrieved Bright Data profile details."],
            }
            comments = response.get("public_comments") or []
            if comments:
                update["collected_comments"] = {"profile": comments}
            return update
        return {
            "errors": [f"Bright Data details error: {response.get('error')}"],
            "log": ["Bright Data profile lookup failed; continuing with existing context."],
        }

    async def _google_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(state, sources=["google", "profile"])
        payload = {
            "full_name": state.get("full_name"),
            "email": state.get("email"),
            "comments": self._format_comments(comments),
        }
        analysis = await self._invoke_llm_json(GOOGLE_PERSONALITY_ANALYSIS_PROMPT, payload)
        if analysis:
            traits = analysis.get("traits") or {}
            updates: PersonaDiscoveryState = {
                "initial_analyses": {"google": analysis},
                "log": ["Google analysis complete."],
            }
            if traits:
                updates["personality_traits"] = self._merge_traits(
                    state.get("personality_traits"), traits
                )
            return updates
        return {}

    async def _bing_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(state, sources=["google", "facebook", "profile"])
        payload = {"comments": self._format_comments(comments)}
        analysis = await self._invoke_llm_json(BING_PERSONALITY_ANALYSIS_PROMPT, payload)
        if analysis:
            planning_profile = {
                "planning_style": analysis.get("planning_style"),
                "social_energy": analysis.get("social_energy"),
                "risk_appetite": analysis.get("risk_appetite"),
            }
            return {
                "initial_analyses": {"bing": analysis},
                "planning_profile": planning_profile,
                "log": ["Bing persona profiling complete."],
            }
        return {}

    async def _reddit_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(state, sources=["reddit"])
        payload = {"comments": self._format_comments(comments)}
        analysis = await self._invoke_llm_json(REDDIT_PERSONALITY_ANALYSIS_PROMPT, payload)
        if analysis:
            return {
                "initial_analyses": {"reddit": analysis},
                "community_signals": analysis,
                "log": ["Reddit behavioral cues extracted."],
            }
        return {}

    async def _interest_exploration(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        insights_blob = json.dumps(
            {
                "traits": state.get("personality_traits"),
                "planning": state.get("planning_profile"),
                "community": state.get("community_signals"),
            },
            indent=2,
            default=str,
        )
        payload = {"insights": insights_blob}
        analysis = await self._invoke_llm_json(INTEREST_EXPLORATION_PROMPT, payload)

        google_queries = (analysis or {}).get("google_queries") or []
        reddit_queries = (analysis or {}).get("reddit_queries") or []

        interest_results: Dict[str, List[Any]] = {"google": [], "reddit": []}
        for query in google_queries:
            result = await bright_data_client.search_public("google", query, limit=4)
            if result.get("success"):
                interest_results["google"].append(result)
        for query in reddit_queries:
            result = await bright_data_client.search_public("reddit", query, limit=4)
            if result.get("success"):
                interest_results["reddit"].append(result)

        updates: PersonaDiscoveryState = {
            "interest_queries": {"google": google_queries, "reddit": reddit_queries},
            "interest_results": interest_results,
            "log": ["Interest exploration searches completed."],
        }
        unsaid_hook = (analysis or {}).get("unsaid_hook")
        if unsaid_hook:
            updates["unspoken_hook"] = unsaid_hook
        return updates

    async def _reddit_url_selection(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        reddit_results = state.get("interest_results", {}).get("reddit", [])
        serialized = json.dumps(reddit_results, indent=2, default=str)
        payload = {"reddit_results": serialized, "limit": 5}
        selection = await self._invoke_llm_json(REDDIT_URL_SELECTION_PROMPT, payload)

        urls = (selection or {}).get("selected_urls") or []
        rationale = (selection or {}).get("rationale") or []
        if not urls:
            urls = self._fallback_reddit_urls(reddit_results)
        return {
            "reddit_urls": urls,
            "reddit_url_rationale": rationale,
            "log": [f"Selected {len(urls)} Reddit threads for deep dive."],
        }

    async def _reddit_comment_retrieval(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        urls = state.get("reddit_urls") or []
        if not urls:
            return {}

        response = await bright_data_client.fetch_reddit_comments(urls, limit=40)
        if response.get("success"):
            bucket = response.get("comments", {})
            collected = [
                comment for comments in bucket.values() for comment in comments or []
            ]
            updates: PersonaDiscoveryState = {
                "reddit_comments": bucket,
                "log": ["Downloaded Reddit comments for selected threads."],
            }
            if collected:
                updates["collected_comments"] = {"reddit_deep_dive": collected}
            return updates
        return {
            "errors": [f"Reddit comment retrieval failed: {response.get('error')}"],
            "log": ["Reddit comment retrieval failed; continuing without deep dive comments."],
        }

    async def _google_final_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(state, sources=["interest_google"])
        payload = {"comments": self._format_comments(comments)}
        analysis = await self._invoke_llm_json(GOOGLE_FINAL_ANALYSIS_PROMPT, payload)
        if analysis:
            return {
                "final_analyses": {"google": analysis},
                "log": ["Google final analysis complete."],
            }
        return {}

    async def _bing_final_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(
            state,
            sources=["google", "interest_google", "reddit_deep_dive"],
        )
        payload = {"comments": self._format_comments(comments)}
        analysis = await self._invoke_llm_json(BING_FINAL_ANALYSIS_PROMPT, payload)
        if analysis:
            return {
                "final_analyses": {"bing": analysis},
                "log": ["Bing final analysis complete."],
            }
        return {}

    async def _reddit_final_analysis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        comments = self._aggregate_comments(state, sources=["reddit_deep_dive"])
        payload = {"comments": self._format_comments(comments)}
        analysis = await self._invoke_llm_json(REDDIT_FINAL_ANALYSIS_PROMPT, payload)
        if analysis:
            return {
                "final_analyses": {"reddit": analysis},
                "log": ["Reddit final analysis complete."],
            }
        return {}

    async def _final_synthesis(self, state: PersonaDiscoveryState) -> PersonaDiscoveryState:
        payload = {
            "traits": json.dumps(state.get("personality_traits"), indent=2, default=str),
            "initial_analyses": json.dumps(state.get("initial_analyses"), indent=2, default=str),
            "interest_results": json.dumps(state.get("interest_results"), indent=2, default=str),
            "reddit_findings": json.dumps(state.get("reddit_comments"), indent=2, default=str),
            "final_analyses": json.dumps(state.get("final_analyses"), indent=2, default=str),
        }
        synthesis = await self._invoke_llm_json(FINAL_SYNTHESIS_PROMPT, payload)
        if synthesis:
            unspoken = synthesis.get("unspoken", {}) or {}
            unspoken["title"] = "UNSPOKEN"
            if not unspoken.get("recommendation") and state.get("unspoken_hook"):
                unspoken["recommendation"] = state["unspoken_hook"]
            synthesis["unspoken"] = unspoken
            return {
                "final_output": synthesis,
                "log": ["Final synthesis complete."],
            }
        return {}

    # ------------------------------------------------------------------ #
    # Helper Methods
    # ------------------------------------------------------------------ #
    def _build_search_update(self, source: str, result: Dict[str, Any]) -> PersonaDiscoveryState:
        if result.get("success"):
            update: PersonaDiscoveryState = {
                "search_results": {source: result},
                "search_completion": [source],
                "log": [f"{source.title()} search complete."],
            }
            comments = self._extract_comments(result)
            if comments:
                update["collected_comments"] = {source: comments}
            return update
        return {
            "errors": [f"{source.title()} search failed: {result.get('error')}"],
            "log": [f"{source.title()} search failed; continuing with fallback data."],
        }

    def _extract_handles(self, state: PersonaDiscoveryState) -> List[str]:
        handles: List[str] = []
        for result in state.get("search_results", {}).values():
            for item in result.get("results", []) or []:
                handle = item.get("handle") or item.get("author")
                if handle and handle not in handles:
                    handles.append(handle)
        return handles

    def _extract_comments(self, result: Dict[str, Any]) -> List[str]:
        comments: List[str] = []
        for item in result.get("results", []) or []:
            snippet = item.get("snippet")
            if snippet:
                comments.append(snippet)
            for comment in item.get("comments") or []:
                comments.append(comment)
        return comments

    def _aggregate_comments(self, state: PersonaDiscoveryState, *, sources: List[str]) -> List[str]:
        all_comments: List[str] = []
        comment_bucket = state.get("collected_comments", {})

        for source in sources:
            if source == "interest_google":
                for entry in state.get("interest_results", {}).get("google", []):
                    all_comments.extend(self._extract_comments(entry))
            else:
                all_comments.extend(comment_bucket.get(source, []))

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for comment in all_comments:
            if comment not in seen:
                seen.add(comment)
                deduped.append(comment)
        return deduped[:120]

    def _fallback_reddit_urls(self, reddit_results: List[Dict[str, Any]]) -> List[str]:
        urls: List[str] = []
        for block in reddit_results:
            for entry in block.get("results", []) or []:
                url = entry.get("url")
                if url and url not in urls:
                    urls.append(url)
            if len(urls) >= 5:
                break
        return urls[:5]

    def _merge_traits(
        self,
        existing: Optional[Dict[str, float]],
        new_traits: Dict[str, Any],
    ) -> Dict[str, float]:
        traits = dict(existing or {})
        for key, value in new_traits.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue

            if key in traits:
                traits[key] = round((traits[key] + numeric) / 2, 4)
            else:
                traits[key] = round(numeric, 4)
        return traits

    def _format_comments(self, comments: List[str]) -> str:
        return "\n".join(f"- {comment}" for comment in comments) or "No comments available."

    async def _invoke_llm_json(self, prompt_template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        if not self._llm:
            return {}

        try:
            prompt = prompt_template.format(**variables)
        except KeyError as exc:
            self._record_error(None, f"Prompt formatting error: {exc}")
            return {}

        try:
            response = await self._llm.ainvoke(prompt)
            content = getattr(response, "content", None) or str(response)
            return self._extract_json(content)
        except Exception as exc:
            logger.exception("LLM invocation failed: %s", exc)
            return {}

    def _extract_json(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = content[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    pass
        return {"raw": content}

    def _record_error(self, state: Optional[PersonaDiscoveryState], message: str) -> None:
        logger.warning(message)
        if state is not None:
            state.setdefault("errors", [])
            state["errors"].append(message)


# Global instance reused by the authentication flow.
persona_onboarding_graph = PersonaDiscoveryWorkflow()
