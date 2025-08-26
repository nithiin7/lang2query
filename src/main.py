from .agent_graph import build_graph
from .utils.logger import logger

def main():
    graph = build_graph()
    user_input = input("Enter your query: ")
    response = graph.invoke({"input": user_input})
    logger.info(f"Final Response: {response['output']}")

if __name__ == "__main__":
    main()
