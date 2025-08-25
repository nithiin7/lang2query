from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap

from app.config import get_model_config, get_api_key

load_dotenv()

# Get model configuration
routing_config = get_model_config("routing")

# Model configurations
MIXTRAL_MODEL = "mixtral-8x7b-32768"
LLAMA_MODEL = "llama3-70b-8192"

# Initialize routing model based on configuration
if routing_config["provider"] == "anthropic":
    routing_model = ChatAnthropic(
        temperature=routing_config["temperature"], 
        model_name=routing_config["model"]
    )
elif routing_config["provider"] == "groq":
    from langchain_groq import ChatGroq
    routing_model = ChatGroq(
        temperature=routing_config["temperature"], 
        model_name=routing_config["model"]
    )
elif routing_config["provider"] == "openai":
    from langchain_openai import ChatOpenAI
    routing_model = ChatOpenAI(
        temperature=routing_config["temperature"], 
        model_name=routing_config["model"]
    )
else:
    # Default to Anthropic
    routing_model = ChatAnthropic(
        temperature=routing_config["temperature"], 
        model_name=routing_config["model"]
    )

# Router prompt template
router_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an intelligent router in a natural language to query system that understands the user question and 
determines which domain agents might have answers to the question based on agent descriptions. Multiple agents might answer a given user question. OUTPUT SHOULD BE IN FORM OF LIST OF strings.
Don't give any explanation or any other verbose in the output.
""",
        ),
        (
            "human",
            """
Below are descriptions of different domain agents.
customer agent : It contains all the details about customer and seller locations and their unique identifiers
orders agent : It contains details about all the orders like product identifier, order identifier, products in an order, no. of items of a product in order, price of order, freight value, order time, delivery status and its time, payment etc.
product agent : It contains details about product like product identifier, product category, description, dimensions of product

STEP BY STEP DOMAIN SELECTION PROCESS:
- Split the question into different subquestions.
- For each subquestion, very carefully go through each and every AGENT description, think which agent might have answer to this subquestion.
- At the end collect all the agents that you thought can answer the whole question in form of list of strings
- For a given question, if customer and orders agents can answer question, give output like below without any verbose.
['customer', 'orders']
- If only customer can answer a question, give output like below with one table in list
['customer']
- For a given question, if customer and orders and product agent can answer question, give output like below without any verbose.
['customer', 'orders', 'product']
     
User question:
{question}

      """,
        ),
    ]
)

# Build the routing chain
routing_chain = (
    RunnableMap({"question": lambda x: x["question"]})
    | router_prompt_template
    | routing_model
    | StrOutputParser()
)


def route_query_to_domains(user_query: str):
    """Route a user query to appropriate domain agents."""
    response = routing_chain.invoke({"question": user_query}).replace("```", "")
    return response
