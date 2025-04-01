import os
import sys
import json
import requests
from crewai import Agent, Task
from crewai.tools.base_tool import Tool
from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")

class ProductSearchAgent:
    def __init__(self, api_url=DATABASE_URL, llm=None):
        """
        Initialize the product search agent with API URL and LLM model
        
        Args:
            api_url: Base URL for the product search API
            model_name: Name of the Ollama model to use
            message_broker: Optional message broker for sending updates
        """
        logger.info(f"ProductSearchAgent.__init__: Initializing with api_url={api_url}")
        self.api_url = api_url
        self.llm = llm
        self.setup_agent()
        
    def setup_agent(self):
        """Set up the CrewAI agent with the appropriate tools and configuration"""
        logger.info(f"ProductSearchAgent.setup_agent: Setting up agent")
        self.agent = Agent(
            role="Product Search Assistant",
            goal="Help customers find products in the store",
            backstory="I am an AI assistant that helps customers find products in the store by searching the product database.",
            verbose=True,
            allow_delegation=False,
            tools=[Tool(
                name="search_products",
                description="Search for products in the store database",
                func=self.search_products
            )],
            llm=self.llm
        )
    
    def search_products(self, query: str):
        """
        Search for products in the database
        
        Args:
            query: The search query (product name)
            
        Returns:
            Dict containing search results
        """
        logger.info(f"ProductSearchAgent.search_products: Searching for: {query}")
        try:
            # Extract product name from query
            product_name = self._extract_product_name(query)
            
            # Call the search API
            search_payload = {
                "name": product_name
            }
            
            logger.info(f"ProductSearchAgent.search_products: Sending API request with payload: {search_payload}, api url is {self.api_url}")
            response = requests.post(
                f"{self.api_url}/search/",
                json=search_payload
            )
            logger.info(f"ProductSearchAgent.search_products: API response: {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status code {response.status_code}", "details": response.text}
        
        except Exception as e:
            logger.error(f"ProductSearchAgent.search_products: Error during search: {str(e)}")
            return {"error": str(e)}
    
    def _extract_product_name(self, query: str) -> str:
        """
        Extract the product name from a natural language query
        
        Args:
            query: The natural language query (e.g., "Where can I find bread?")
            
        Returns:
            The extracted product name (e.g., "bread")
        """
        logger.info(f"ProductSearchAgent._extract_product_name: Extracting from query: {query}")
        # Use the LLM to extract the product name
        extraction_prompt = [
            {"role": "system", "content": "Extract the product name from the following query. Respond with ONLY the product name, nothing else."},
            {"role": "user", "content": query}
        ]
        
        product_name = self.llm.generate(extraction_prompt).strip().lower()

        logger.info(f"ProductSearchAgent._extract_product_name: Extracted product name: {product_name}")
        
        return product_name
    
    def _transform_search_results(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the raw search results into a more structured format
        
        Args:
            search_results: The raw search results from the API
            
        Returns:
            A transformed version of the search results
        """
        logger.info(f"ProductSearchAgent._transform_search_results: Transforming search results")

        transformed_results = {
            "products": [],
            "total_count": 0,
            "metadata": {
                "query_time": "now",
                "source": "product_search_agent"
            }
        }
        
        # Handle error case
        if "error" in search_results:
            transformed_results["error"] = search_results["error"]
            return transformed_results
            
        # Process results if they exist
        if search_results and isinstance(search_results, list):
            
            transformed_results["total_count"] = len(search_results)
            
            for result in search_results:
                if (not result or not isinstance(result, dict)):
                    continue

                product_data = result.get("product", {})
                location_data = result.get("location", {})
                
                # Create a simplified product object
                transformed_product = {
                    "name": product_data.get("name", ""),
                    "location": {
                        "aisle": location_data.get("aisle", ""),
                        "section": location_data.get("section", ""),
                        "shelf": location_data.get("shelf", "")
                    },
                    "details": {
                        "description": product_data.get("description", ""),
                        "category": product_data.get("category", ""),
                        "brand": product_data.get("attributes", {}).get("brand", ""),
                        "size": product_data.get("attributes", {}).get("size", "")
                    }
                }
                
                transformed_results["products"].append(transformed_product)
                
        return transformed_results

    def process_query(self, query: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query and return a response
        
        Args:
            query: The user's query (e.g., "Where can I find bread?")
            client_id: Optional client ID for sending updates
            
        Returns:
            A dictionary containing the text response and the raw search results
        """
        logger.info(f"ProductSearchAgent.process_query: Processing query: {query}, client_id: {client_id}")
        # Execute the task
        search_results = self.search_products(query)
        
        # Transform the search results
        transformed_results = self._transform_search_results(search_results)
        
        # Format the response based on search results
        if "error" in search_results:
            text_response = f"Mi dispiace, non sono riuscito a cercare il prodotto. Errore: {search_results['error']}"
            return {
                "text": text_response,
                "results": None
            }
        
        if not search_results or len(search_results) == 0:
            text_response = "Mi dispiace, non ho trovato nessun prodotto corrispondente alla tua ricerca."
            return {
                "text": text_response,
                "results": None
            }
        
        # Format a nice response with the product information
        # response_prompt = [
        #     {"role": "system", "content": "Sei un assistente del negozio. Rispondi al cliente in modo naturale e includi informazioni come corsia, sezione e scaffale se disponibili."},
        #     {"role": "user", "content": f"Il cliente ha chiesto: '{query}'. Ecco i risultati della ricerca: {json.dumps(transformed_results, ensure_ascii=False)}"}
        # ]
        
        # try:
        #     # Generate the response using the LLM
        #     text_response = self.llm.generate(response_prompt).strip()
            
        #     # Handle empty or invalid responses
        #     if not text_response:
        #         text_response = "Mi dispiace, non sono riuscito a generare una risposta valida."
            
        # except Exception as e:
        #     text_response = f"Errore durante la generazione della risposta: {str(e)}"
        
        return {
            "text": None,
            "results": transformed_results
        }

# Example usage
if __name__ == "__main__":
    agent = ProductSearchAgent()
    response = agent.process_query("Dove posso trovare il pane?")["text"]
    print("Response: ", response)