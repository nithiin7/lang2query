import pickle
from datetime import datetime
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph
from sqlalchemy import create_engine

from app.agents.customer import graph_final
from app.agents.helpers.customer_helper import (
    chain_filter_extractor,
    chain_query_extractor,
    chain_query_validator,
)
from app.agents.router import agent_2
from app.services.fuzzy import call_match

d_store = {
    "customer": ["customer", "sellers"],
    "orders": ["order_items", "order_payments", "order_reviews", "orders"],
    "product": ["products", "category_translation"],
}


with open("kb.pkl", "rb") as f:
    loaded_dict = pickle.load(f)

engine = create_engine("mysql+mysqlconnector://root:Indianarmy@localhost/txt2sql")


def remove_duplicates(f):
    s = set()
    final = []
    for k, v in f.items():
        if k in ("cust_out", "order_out", "product_out"):
            for item in v["column_extract"]:
                key = tuple(item)
                if key not in s:
                    final.append(item)
                    s.add(key)
    return final


class finalstate(TypedDict):
    user_query: str
    router_out: list[str]
    cust_out: str
    order_out: str
    product_out: str
    filtered_col: str
    filter_extractor: list[str]
    fuzz_match: list[str]
    sql_query: str
    final_query: str


### Defining Nodes


def router(state: finalstate):
    q = state["user_query"]
    o = agent_2(q)
    return {"router_out": eval(o)}


def route_request(state: finalstate):
    routes = state["router_out"]
    print("Routed request to" + str(routes) + " agents")
    return routes


def filter_condition(state: finalstate):
    if len(state["filter_extractor"]) == 1:
        return "no"
    else:
        return "yes"


def customer(state: finalstate):
    q = state["user_query"]
    print("Extracting relavant tables and columns from customer agent................")
    sub = graph_final.invoke({"user_query": q, "table_lst": d_store["customer"]})
    return {"cust_out": sub}


def orders(state: finalstate):
    q = state["user_query"]
    print("Extracting relavant tables and columns from orders agent................")
    sub = graph_final.invoke({"user_query": q, "table_lst": d_store["orders"]})
    return {"order_out": sub}


def product(state: finalstate):
    q = state["user_query"]
    print(q)

    print("Extracting relavant tables and columns from product agent................")
    sub = graph_final.invoke({"user_query": q, "table_lst": d_store["product"]})
    print(sub)
    return {"product_out": sub}


def filter_check(state: finalstate):
    q = state["user_query"]
    f = {}
    col_f = []
    for key in ["order_out", "cust_out", "product_out"]:
        if key in state:
            f[key] = state.get(key)
            col_f.append(state[key])
    col_details = remove_duplicates(f)
    print("Checking the need for filter................")
    response = chain_filter_extractor.invoke({"columns": str(col_details), "query": q}).replace(
        "```", ""
    )
    return {"filter_extractor": eval(response), "filtered_col": str(col_details)}


def fuzz_match(state: finalstate):
    val = state["filter_extractor"]
    print("Solving for getting right filter vaues.........")
    lst = call_match(val)
    print("done filtering...........................")
    return {"fuzz_match": lst}


def query_generation(state: finalstate):
    q = state["user_query"]
    tab_cols = state["filtered_col"]
    if state.get("fuzz_match"):
        filters = state.get("fuzz_match")
    else:
        filters = ""
    print("Generating SQL query.........")
    final_query = chain_query_extractor.invoke(
        {"columns": tab_cols, "query": q, "filters": filters}
    )
    return {"sql_query": final_query}


def query_validation(state: finalstate):
    print("validating and generating final query........")
    o = chain_query_validator.invoke(
        {
            "columns": state["filtered_col"],
            "query": state["user_query"],
            "filters": state.get("fuzz_match"),
            "sql_query": state["sql_query"],
        }
    )
    return {"final_query": o}


builder_final = StateGraph(finalstate)

builder_final.add_node("router", router)  # Add explicit node names

builder_final.add_node("customer", customer)
builder_final.add_node("orders", orders)
builder_final.add_node("product", product)

builder_final.add_node("filter_check", filter_check)
builder_final.add_node("fuzz_filter", fuzz_match)
builder_final.add_node("query_generator", query_generation)
builder_final.add_node("query_validation", query_validation)

builder_final.add_edge(START, "router")

builder_final.add_conditional_edges("router", route_request, ["customer", "orders", "product"])

builder_final.add_edge("customer", "filter_check")
builder_final.add_edge("orders", "filter_check")
builder_final.add_edge("product", "filter_check")

builder_final.add_conditional_edges(
    "filter_check", filter_condition, {"no": "query_generator", "yes": "fuzz_filter"}
)

builder_final.add_edge("fuzz_filter", "query_generator")

builder_final.add_edge("query_generator", "query_validation")

builder_final.add_edge("query_validation", END)

graph_main = builder_final.compile()


def safe_extract(record, key):
    return record.get(key) if key in record else None


def predict(q):
    f = graph_main.invoke({"user_query": q})

    normalized_records = []

    normalized = {
        "user_query": f.get("user_query"),
        "router_out": f.get("router_out"),
        "cust_out": f.get("cust_out") if f.get("cust_out") else None,
        "order_out": f.get("order_out") if f.get("cust_out") else None,
        "product_out": f.get("product_out") if f.get("cust_out") else None,
        "filtered_col": f.get("filtered_col"),
        "filter_extractor": f.get("filter_extractor"),
        "sql_query": f.get("sql_query"),
        "final_query": f.get("final_query"),
    }

    normalized_records.append(normalized)

    df_normalized = pd.DataFrame(normalized_records)
    df_normalized["inserted_at"] = datetime.now()
    df_normalized["version"] = "v1"

    return df_normalized, f


def main():
    # Example usage
    q = "Give me list of customers from  São Paulo state that made atleast 1 payment through credit card"
    df, f = predict(q)

    # Example complex query
    q2 = """For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery), 
and where the product price was above the average price of its category. Only include states with at least 100 such orders, 
and rank them from highest to lowest average score."""

    df2, f2 = predict(q2)

    # List of test queries
    lst = [
        "What are the total no. of orders made?",
        """For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery), 
    and where the product price was above the average price of its category. Only include states with at least 100 such orders, 
    and rank them from highest to lowest average score.""",
        """Among sellers who have sold at least 50 items, which seller had the highest percentage of orders with a 5-star review and what is that percentage? 
    Only include orders where the product was delivered on time (i.e., delivered on or before the estimated delivery date), and the payment was made in installments.""",
        """

    For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery),
    and where the product price was above the average price of its category.
    Only include states with at least 100 such orders, and rank them from highest to lowest average score.
    """,
    ]


if __name__ == "__main__":
    main()
