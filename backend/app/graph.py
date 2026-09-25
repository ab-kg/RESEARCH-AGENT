from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ResearchState(TypedDict, total=False):
    question: str
    plan: list[str]
    findings: list[str]
    evidence_status: str
    report: dict


def plan_research(state: ResearchState) -> dict:
    """Create a small plan. This starter node is deterministic, before model setup."""
    question = state["question"]
    return {"plan": [
        f"Clarify the scope of: {question}",
        "Find recent, reliable sources for the key aspects",
        "Compare evidence and note uncertainty before summarizing",
    ]}


def gather_research(state: ResearchState) -> dict:
    """Placeholder node; real search is deliberately not simulated."""
    return {"findings": [], "evidence_status": "not_searched"}


def assess_evidence(state: ResearchState) -> dict:
    status = "insufficient" if not state.get("findings") else "ready"
    return {"evidence_status": status}

def write_report(state: ResearchState) -> dict:
    question = state["question"]
    report = {
        "title": question.rstrip(" ?.!"),
        "summary": (
            "The research workflow is connected, but its search and model providers are not configured yet. "
            "This preview confirms the question can travel through the LangGraph workflow and return a report. "
            "No web research has been performed, so this response makes no factual findings."
        ),
        "sections": [
            {"heading": "Research plan", "body": "\n".join(f"{i + 1}. {item}" for i, item in enumerate(state.get("plan", [])))},
            {"heading": "Evidence review", "body": "No sources have been collected yet. The next milestone connects a search tool, then adds model-based synthesis and evidence review."},
        ],
        "sources": [],
        "demo": True,
    }
    return {"report": report}


builder = StateGraph(ResearchState)
builder.add_node("plan", plan_research)
builder.add_node("research", gather_research)
builder.add_node("assess", assess_evidence)
builder.add_node("write", write_report)
builder.add_edge(START, "plan")
builder.add_edge("plan", "research")
builder.add_edge("research", "assess")
builder.add_edge("assess", "write")
builder.add_edge("write", END)
research_graph = builder.compile()
