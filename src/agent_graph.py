from langgraph.graph import END, StateGraph

from .agents.sample_agent import SampleAgent
from .config import settings
from .utils.logger import logger


# State definition
class State(dict):
    input: str
    output: str


# Agent node
def agent_node(state: State):
    agent = SampleAgent(api_key=settings.openai_api_key)
    result = agent.run(state["input"])
    logger.info(f"Agent output: {result}")
    return {"output": result}


# Build graph
def build_graph():
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    return builder.compile()
