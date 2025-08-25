import pandas as pd
from groq import Groq
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
from sqlalchemy import create_engine
import tqdm
import time
import pickle


from dotenv import load_dotenv

load_dotenv()

table_description = {


'order_items'  : '''It contains data related to no. of items in an order,product identifier, seller identifier and price and frieght value of a product in an order.
order item id sys no. of items of the product in a particular order.
shipping_limit_date: Shows the seller shipping limit date for handling the order over to the logistic partner.
price column tells about price of an item.
freight_value: item freight value per item.
''',
'customer' : '''It contains data related to customer id, location of a customer''',

'order_payments'  : '''Contains all the details related to payment and transaction value of a payment.
payment_sequential: A customer may pay an order with more than one payment method. If he does so, a sequence will be created like 1,2 denoting no. of times they paid through different payment methods.
payment_installments : customer can choose many installments like 1,2 or any. 
payment_value: payment value is value for each transaction.

''',
'order_reviews'  : '''Contains details related to reviews of an order''',
'orders'  : '''Contains all the details related to order delivery like when it is delivered, when it is ordered, if it is delivered or not etc.''',
'products'  : '''Contains all the details related to a product like its description, dimension, category in brazilian etc.''',
'sellers'  : '''Contains details about seller identifier and location''',
'category_translation' : '''Contains details related to product category translation from brazilian to english'''

}

engine = create_engine('mysql+mysqlconnector://root:Indianarmy@localhost/txt2sql')

def read_sql(table):

# Query to get shuffled rows and limit to 5
    query = "SELECT * FROM {} ORDER BY RAND() LIMIT 5;".format(table)

    # Execute and load into DataFrame
    df_sample = pd.read_sql(query, con=engine)
    return df_sample

llama = 'llama3-70b-8192'

#model = ChatGroq(temperature=0, model_name=llama) 

model = ChatAnthropic(temperature=0.4, model_name='claude-3-5-sonnet-20240620') 

template = ChatPromptTemplate.from_messages([
    ("system", """
You are an intelligent data annotator. Please annotate data as mentioned by human and give output without any verbose and without any additional explantion.
You will be given sql table description and sample columns from the sql table. The description that you generate will be given as input to text to sql automated system.
Output of project depends on how you generate description. Make sure your description has all possible nuances.

"""),

    ("human", '''

- Based on the column data, please generate description of entire table along with description for each column and sample values(1 or 2) for each column.
- While generating column descriptions, please look at sql table description given to you and try to include them in column description. 
- DONT write generic description like "It provides a comprehensive view of the order lifecycle from purchase to delivery". Just write description based on what you see in columns.

      
Context regarding the tables:
These tables ere provided by Olist, the largest department store in Brazilian marketplaces. Olist connects small businesses from all over Brazil to channels without hassle and with a single contract. Those merchants are able to sell their products through the Olist Store and ship them directly to the customers using Olist logistics partners.
After a customer purchases the product from Olist Store a seller gets notified to fulfill that order. Once the customer receives the product, or the estimated delivery date is due, the customer gets a satisfaction survey by email where he can give a note for the purchase experience and write down some comments.
    
An order might have multiple items.
Each item might be fulfilled by a distinct seller.
    

Output should look like below in form of list of strings and lists properly. MAKE SURE YOU CLOSE THE QUOTES in list of strings properly always.
["<table description based on all column values>" , [["<column 1> : Detail description of column along with datatype, <sample values:v1,v2 etc(indicate there are more values)>"],
["<column 2> : Detail description of column 2 along with datatype, <sample values:v1,v2 etc(indicate there are more values)>"]]  
]
     
SQL table description:
{description}

Sample rows from the table:
{data_sample}     

     ''')
])

# Fix the RunnableMap implementation
chain = (
    RunnableMap({
        "description": lambda x: x["description"],
        "data_sample": lambda x: x["data_sample"]
    })
    | template
    | model
    | StrOutputParser()
)

def main():
    kb_final = {}
    for k,v in tqdm.tqdm(table_description.items()):
        d = read_sql(k)
        d_dict = str(d.to_dict())

        response = chain.invoke({"description": v, "data_sample": d_dict}).replace('```', '')
        print(response)
        print('====================================================')
        kb_final[k] = eval(response)
        time.sleep(5)

    with open('kb.pkl', 'wb') as f:
        pickle.dump(kb_final, f)

if __name__ == "__main__":
    main()
