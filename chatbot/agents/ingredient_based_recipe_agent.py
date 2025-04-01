import os
import sys
import requests
from crewai import Agent
from crewai.tools.base_tool import Tool
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")

class IngredientBasedRecipeAgent:
    def __init__(self, api_url=DATABASE_URL, llm=None):
        """
        Initialize the product search agent with API URL and LLM model
        
        Args:
            api_url: Base URL for the product search API
            model_name: Name of the Ollama model to use
        """
        logger.info(f"IngredientBasedRecipeAgent.__init__: Initializing with api_url={api_url}")
        self.api_url = api_url
        self.llm = llm
        self.setup_agent()
    
    def setup_agent(self):
        """Set up the CrewAI agent with the appropriate tools and configuration"""
        logger.info(f"IngredientBasedRecipeAgent.setup_agent: Setting up agent")
        self.agent = Agent(
            role="Ingredient-Based Recipe Assistant",
            goal="Suggest recipes based on the ingredients provided by the user",
            backstory="I am an AI assistant that helps customers find recipes based on the ingredients they want.",
            verbose=True,
            allow_delegation=False,
            tools=[
                Tool(
                    name="suggest_recipes",
                    description="Suggest recipes based on a list of ingredients",
                    func=self.suggest_recipes
                )
            ],
            llm=self.llm
        )
    
    def suggest_recipes(self, ingredients: List[str]) -> Dict[str, Any]:
        """
        Suggest recipes based on a list of ingredients and provide product details with locations.
        
        Args:
            ingredients: A list of ingredient names
            
        Returns:
            Dict containing the best recipe and product details with locations
        """
        try:
            # Convert ingredient names to product IDs
            product_ids = self.get_product_ids(ingredients)
            product_ids = [pid for pid in product_ids if pid]  # Filter out None values
            
            if not product_ids:
                return {"error": "Nessun prodotto trovato per gli ingredienti forniti."}
            
            # Prepare the payload for the API request
            ingredient_ids_query = "&".join([f"ingredient_ids={pid}" for pid in product_ids])
            
            # Call the API to get the best recipe by ingredients
            response = requests.post(
                f"{self.api_url}/recipes/best-by-ingredients?{ingredient_ids_query}"
            )
            
            if response.status_code != 200:
                return {"error": f"API returned status code {response.status_code}", "details": response.text}
            
            best_recipe = response.json()
            
            if "error" in best_recipe:
                return {"error": best_recipe["error"]}
            
            # Extract the recipe ID from the response
            recipe_id = best_recipe.get("id")
            if not recipe_id:
                return {"error": "Nessun ID ricetta trovato nella risposta dell'API."}
            
            # Call the API to get detailed recipe information, including product locations
            recipe_details_response = requests.get(f"{self.api_url}/recipes/{recipe_id}")
            
            if recipe_details_response.status_code != 200:
                return {"error": f"API returned status code {recipe_details_response.status_code} for recipe details", "details": recipe_details_response.text}
            
            recipe_details = recipe_details_response.json()
            
            # Return the detailed recipe information
            return recipe_details
        
        except Exception as e:
            return {"error": str(e)}
        
    def process_query(self, query: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query and return a response with the best recipe and product details.
        
        Args:
            query: The user's query (e.g., "What can I cook with eggs and flour?")
            client_id: Optional client ID for sending updates
            
        Returns:
            A dictionary containing the text response and the raw search results
        """
        logger.info(f"IngredientBasedRecipeAgent.process_query: Processing query: {query}, client_id: {client_id}")
        # Extract ingredients from the query
        ingredients = self._extract_ingredients(query)
        
        if not ingredients:
            return {
                "text": "Non sono riuscito a identificare gli ingredienti dalla tua richiesta. Per favore, riprova specificando gli ingredienti.",
                "results": None
            }
        
        # Search for the best recipe based on the ingredients
        result = self.suggest_recipes(ingredients)
        
        if "error" in result:
            return {
                "text": f"Mi dispiace, non sono riuscito a cercare le ricette. Errore: {result['error']}",
                "results": None
            }
        
        recipe = result.get("recipe")
        ingredients_details = result.get("ingredients_details", [])
        
        if not recipe:
            return {
                "text": "Mi dispiace, non ho trovato nessuna ricetta corrispondente agli ingredienti forniti.",
                "results": None
            }

        transformed_results = self._transform_recipe_results(recipe, ingredients_details)

        return {
            "text": None,
            "results": transformed_results
        }

    # todo: refactor = centralize all the transformations methods 
    def _transform_recipe_results(self, recipe_details: Dict[str, Any], ingredients_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the raw recipe results into a more structured format
        
        Args:
            recipe_details: The raw recipe details from the API
            
        Returns:
            A transformed version of the recipe details
        """
        logger.info(f"IngredientBasedRecipeAgent._transform_recipe_results: Transforming recipe details")
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
        recipe_data = recipe_details
        
        transformed_results["recipe"] = {
            "id": recipe_data.get("id", ""),
            "name": recipe_data.get("name", ""),
            "description": recipe_data.get("description", "")
        }
        
        # Process ingredients if they exist
        if ingredients_details:
            for ingredient_info in ingredients_details:
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

    def _extract_ingredients(self, query: str) -> List[str]:
        """
        Extract a list of ingredients from a natural language query
        
        Args:
            query: The natural language query (e.g., "What can I cook with eggs and flour?")
            
        Returns:
            A list of extracted ingredients
        """
        logger.info(f"IngredientBasedRecipeAgent._extract_ingredients: Extracting from query: {query}")
        # Use the LLM to extract ingredients
        extraction_prompt = [
            {"role": "system", "content": "Extract the list of ingredients from the following query. Respond with ONLY the ingredients as a comma-separated list."},
            {"role": "user", "content": query}
        ]
        
        ingredients_response = self.llm.generate(extraction_prompt).strip().lower()
        ingredients = [ingredient.strip() for ingredient in ingredients_response.split(",") if ingredient.strip()]
        
        return ingredients
    
    def get_product_ids(self, ingredient_names: List[str]) -> List[Optional[str]]:
        """
        Retrieve product IDs for a list of ingredient names using the API.
        
        Args:
            ingredient_names: A list of ingredient names to search for.
            
        Returns:
            A list of product IDs corresponding to the ingredient names, or None if not found.
        """
        logger.info(f"IngredientBasedRecipeAgent.get_product_ids: Getting product IDs for: {ingredient_names}")
        product_ids = []
        for name in ingredient_names:
            try:
                response = requests.get(f"{self.api_url}/products/", params={"name": name})
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        # Assume the first matching product is the correct one
                        product_ids.append(products[0]["id"])
                    else:
                        product_ids.append(None)  # No match found
                else:
                    print(f"Errore API per l'ingrediente '{name}': {response.status_code}")
                    product_ids.append(None)  # API error
            except requests.exceptions.RequestException as e:
                print(f"Errore di connessione all'API per l'ingrediente '{name}': {str(e)}")
                product_ids.append(None)  # Connection error
        return product_ids

if __name__ == "__main__":
    agent = IngredientBasedRecipeAgent()
    response = agent.process_query("Cosa posso cucinare con pepe nero, uova e spaghetti?")
    print("Response: ", response)