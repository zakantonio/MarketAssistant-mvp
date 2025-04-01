import os
import sys
import json
import requests
from crewai import Agent
from crewai.tools.base_tool import Tool
from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")

class RecipeSearchAgent:
    def __init__(self, api_url=DATABASE_URL, llm=None):
        """
        Initialize the recipe search agent with API URL and LLM model
        
        Args:
            api_url: Base URL for the product search API
            model_name: Name of the Ollama model to use
            message_broker: Optional message broker for sending updates
        """
        logger.info(f"RecipeSearchAgent.__init__: Initializing with api_url={api_url}")
        self.api_url = api_url
        self.llm = llm
        self.setup_agent()
    
    def setup_agent(self):
        """Set up the CrewAI agent with the appropriate tools and configuration"""
        logger.info(f"RecipeSearchAgent.setup_agent: Setting up agent")
        self.agent = Agent(
            role="Recipe Search Assistant",
            goal="Help customers find recipes and locate all ingredients in the store",
            backstory="I am an AI assistant that helps customers find recipes and locate all the ingredients needed for those recipes in the store.",
            verbose=True,
            allow_delegation=False,
            tools=[
                Tool(
                    name="search_recipes",
                    description="Search for recipes in the database",
                    func=self.search_recipes
                ),
                Tool(
                    name="get_recipe_details",
                    description="Get detailed information about a specific recipe",
                    func=self.get_recipe_details
                )
                # Removed search_product tool as it's no longer needed
            ],
            llm=self.llm
        )
    
    def search_recipes(self, query: str):
        """
        Search for recipes in the database
        
        Args:
            query: The search query (recipe name)
            
        Returns:
            Dict containing search results
        """
        logger.info(f"RecipeSearchAgent.search_recipes: Searching for: {query}")
        try:
            # Extract recipe name from query
            recipe_name = self._extract_recipe_name(query)
            
            search_payload = {
                "name": recipe_name
            }
            # Call the search API
            response = requests.post(
                f"{self.api_url}/search_recipes/",
                json=search_payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status code {response.status_code}", "details": response.text}
        
        except Exception as e:
            return {"error": str(e)}
    
    def get_recipe_details(self, recipe_id: str):
        """
        Get detailed information about a specific recipe
        
        Args:
            recipe_id: The ID of the recipe
            
        Returns:
            Dict containing recipe details including ingredients
        """
        logger.info(f"RecipeSearchAgent.get_recipe_details: Getting details for recipe_id: {recipe_id}")
        try:
            response = requests.get(f"{self.api_url}/recipes/{recipe_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status code {response.status_code}", "details": response.text}
        
        except Exception as e:
            return {"error": str(e)}
    
    def search_product(self, product_id: str):
        """
        Search for a specific product in the store
        
        Args:
            product_id: The ID of the product
            
        Returns:
            Dict containing product details including location
        """
        logger.info(f"RecipeSearchAgent.search_product: Searching for product_id: {product_id}")
        try:
            response = requests.get(f"{self.api_url}/products/{product_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status code {response.status_code}", "details": response.text}
        
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_recipe_name(self, query: str) -> str:
        """
        Extract the recipe name from a natural language query
        
        Args:
            query: The natural language query (e.g., "How do I make banana bread?")
            
        Returns:
            The extracted recipe name (e.g., "banana bread")
        """
        logger.info(f"RecipeSearchAgent._extract_recipe_name: Extracting from query: {query}")
        # Use the LLM to extract the recipe name
        extraction_prompt = [
            {"role": "system", "content": "Extract the recipe name from the following query. Respond with ONLY the recipe name, nothing else."},
            {"role": "user", "content": query}
        ]
        
        recipe_name = self.llm.generate(extraction_prompt).strip().lower()
        
        return recipe_name
    
    def _transform_recipe_results(self, recipe_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the raw recipe results into a more structured format
        
        Args:
            recipe_details: The raw recipe details from the API
            
        Returns:
            A transformed version of the recipe details
        """
        logger.info(f"RecipeSearchAgent._transform_recipe_results: Transforming recipe details")
        transformed_results = {
            "recipe": {},
            "products": [],
            "metadata": {
                "query_time": "now",
                "source": "recipe_search_agent"
            }
        }
        
        # Handle error case
        if "error" in recipe_details:
            transformed_results["error"] = recipe_details["error"]
            return transformed_results
            
        # Process recipe if it exists
        if recipe_details and "recipe" in recipe_details:
            recipe_data = recipe_details["recipe"]
            
            transformed_results["recipe"] = {
                "id": recipe_data.get("id", ""),
                "name": recipe_data.get("name", ""),
                "description": recipe_data.get("description", "")
            }
            
            # Process ingredients if they exist
            if "ingredients_details" in recipe_details and recipe_details["ingredients_details"]:
                for ingredient_info in recipe_details["ingredients_details"]:
                    if not ingredient_info or "product" not in ingredient_info:
                        continue
                        
                    product = ingredient_info.get("product", {})
                    location = ingredient_info.get("location", {})
                    quantity = ingredient_info.get("quantity", 0)
                    unit = ingredient_info.get("unit", "")
                    
                    transformed_ingredient = {
                        "name": product.get("name", ""),
                        "quantity": quantity,
                        "unit": unit,
                        "location": {
                            "aisle": location.get("aisle", "") if location else "",
                            "section": location.get("section", "") if location else "",
                            "shelf": location.get("shelf", "") if location else ""
                        },
                        "details": {
                            "description": product.get("description", ""),
                            "category": product.get("category", ""),
                            "brand": product.get("attributes", {}).get("brand", ""),
                            "size": product.get("attributes", {}).get("size", "")
                        }
                    }
                    
                    transformed_results["products"].append(transformed_ingredient)
        
        return transformed_results

    def process_query(self, query: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query and return a response
        
        Args:
            query: The user's query (e.g., "How do I make banana bread?")
            client_id: Optional client ID for sending updates
            
        Returns:
            A dictionary containing the text response and the raw search results
        """
        logger.info(f"RecipeSearchAgent.process_query: Processing query: {query}, client_id: {client_id}")
        # First, search for recipes matching the query
        recipes = self.search_recipes(query)
        
        if "error" in recipes:
            text_response = f"Mi dispiace, non sono riuscito a cercare la ricetta. Errore: {recipes['error']}"
            return {
                "text": text_response,
                "results": None
            }
        
        if not recipes or len(recipes) == 0:
            text_response = "Mi dispiace, non ho trovato nessuna ricetta corrispondente alla tua ricerca."
            return {
                "text": text_response,
                "results": None
            }
        
        # Get the first matching recipe - the API now returns complete information
        recipe_details = recipes[0]
        
        # Transform the recipe results
        transformed_results = self._transform_recipe_results(recipe_details)

        # Format a nice response with the recipe information
        # response_prompt = [
        #     {"role": "system", "content": "Sei un assistente di cucina utile. Rispondi al cliente in modo naturale e includi informazioni sulla ricetta e dove trovare gli ingredienti nel negozio."},
        #     {"role": "user", "content": f"Il cliente ha chiesto: '{query}'. Ecco i dettagli della ricetta: {json.dumps(transformed_results, ensure_ascii=False)}"}
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
    agent = RecipeSearchAgent()
    response = agent.process_query("dove trovo gli ingredienti per fare il pancake")["text"]
    print("Response: ", response)