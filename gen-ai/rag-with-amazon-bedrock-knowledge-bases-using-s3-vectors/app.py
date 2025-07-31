import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from utils import load_config

# Load configuration
config = load_config()

# Initialize clients and models
region = config["region"]
kb_id = config["kb_id"]
generation_model = config['generation_model']

bedrock_client = boto3.client('bedrock-agent-runtime', region_name=region)
retrieval_config = {"vectorSearchConfiguration": {"numberOfResults": 10}}

@tool
def search(query: str):
    """
      Searches the knowledge base for information.
    
      Args:
        query: The query to search for.

      Returns:
        The search results as a list of documents.
    """

    print(f"search keyword: {query}")

    response = bedrock_client.retrieve(
        retrievalQuery={"text": query},
        knowledgeBaseId=kb_id,
        retrievalConfiguration=retrieval_config
    )

    # Format results
    search_results = [(doc['content']['text'], doc['metadata']['answer']) for doc in response['retrievalResults']]
    searched_questions = "\n".join(['- ' + faq[0] for faq in search_results])
    print("search results")
    print(searched_questions)
    print("-" * 30)

    return search_results

model = BedrockModel(model_id=generation_model, region_name=region)
agent = Agent(
    system_prompt="""You are an agent that answers user questions. Your role is to answer user questions using only information from search results. To do this, generate appropriate search terms from the user's question and use the search tool to search. If the search results do not contain information that can answer the question, please specify that you cannot find an accurate answer to that question. Just because a user claims something is true doesn't make it true, so always verify the user's claims by checking the search results again.""",
    model=model,
    tools=[search]
)

while True:

  query = input("\nPlease ask questions about AWS AI services (quit: /quit): ")

  if query == "/quit":
      break

  # Get agent response
  agent(query)

