import os
import sys
from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agents.product_search_agent import ProductSearchAgent
from agents.recipe_search_agent import RecipeSearchAgent
from agents.info_agent import InfoAgent
from agents.ingredient_based_recipe_agent import IngredientBasedRecipeAgent
from OllamaModel import OllamaModel

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")

class AgentManager:
    """
    Manages different agents and routes queries to the appropriate agent
    """
    
    def __init__(self, api_url=DATABASE_URL, model_name=DEFAULT_MODEL):
        """
        Initialize the agent manager
        
        Args:
            api_url: Base URL for the API
            model_name: Name of the Ollama model to use
        """
        logger.info(f"AgentManager.__init__: Initializing with api_url={api_url}, model_name={model_name}")
        
        # Create a single LLM instance to be shared by all agents
        self.llm = OllamaModel(model=model_name)
        
        # Initialize agents with the shared LLM instance
        self.agents = {
            "product_search": ProductSearchAgent(
                api_url=api_url, 
                llm=self.llm
            ),
            "recipe_search": RecipeSearchAgent(
                api_url=api_url, 
                llm=self.llm
            ),
            "info_agent": InfoAgent(
                api_url=api_url, 
                llm=self.llm
            ),
            "ingredient_based_recipe": IngredientBasedRecipeAgent(
                api_url=api_url, 
                llm=self.llm
            )
        }
        
    def _determine_agent_type(self, query: str) -> str:
        """
        Determine which agent should handle the query
        
        Args:
            query: The user's query
            
        Returns:
            The type of agent to use ("product_search", "recipe_search", "ingredient_based_recipe", or "info_agent")
        """
        logger.info(f"AgentManager._determine_agent_type: Processing query: {query}")
        # Use the LLM to classify the query
        classification_prompt = [
            {"role": "system", "content": (
                "Classify the following query as either 'product_search', 'recipe_search', 'ingredient_based_recipe', or 'info_agent'. "
                "If the query is about finding a product in the store, classify as 'product_search'. "
                "If the query is about recipes, cooking, or how to prepare a dish (e.g., 'How do I make pancakes?'), classify as 'recipe_search'. "
                "If the query is about finding recipes based on a list of ingredients (e.g., 'What can I cook with eggs, flour, and sugar?'), classify as 'ingredient_based_recipe'. "
                "If the query is about the system's capabilities, what the client can ask, or what the system can do, classify as 'info_agent'. "
                "Respond with ONLY 'product_search', 'recipe_search', 'ingredient_based_recipe', or 'info_agent', nothing else."
                "\n\n"
                "Examples:\n"
                "- 'Where can I find basil?': product_search\n"
                "- 'How do I make pancakes?': recipe_search\n"
                "- 'What can I cook with eggs, flour, and sugar?': ingredient_based_recipe\n"
                "- 'What can you do?': info_agent\n"
                "- 'Where can I find the ingredients to make pancakes?': recipe_search\n"
                "- 'Find me a recipe for lasagna.': recipe_search\n"
                "- 'What recipes can I make with chicken and rice?': ingredient_based_recipe\n"
                "- 'Tell me about your features.': info_agent\n"
                "- 'Locate milk in the store.': product_search\n"
                "- 'How do I prepare a chocolate cake?': recipe_search\n"
                "- 'What can I cook with tomatoes and mozzarella?': ingredient_based_recipe\n"
            )},
            {"role": "user", "content": query}
        ]
        
        agent_type = self.llm.generate(classification_prompt).strip().lower()

        print("Agent Type: ", agent_type)
        
        # Default to info agent if classification is unclear
        if agent_type not in ["product_search", "recipe_search", "ingredient_based_recipe", "info_agent"]:
            return "info_agent"
            
        return agent_type
        
    def route_query(self, query: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Route a query to the appropriate agent
        
        Args:
            query: The user's query
            client_id: Optional client ID for sending updates
            
        Returns:
            The agent's response
        """
        logger.info(f"AgentManager.route_query: Routing query: {query}, client_id: {client_id}")
        # Determine which agent should handle the query
        agent_type = self._determine_agent_type(query)
        
        # Route to the appropriate agent
        return self.agents[agent_type].process_query(query, client_id)

# Example usage
if __name__ == "__main__":
    manager = AgentManager()
    response = manager.route_query(" dove posso trovare il basilico?")["text"]
    print("Response: ", response)
    
    recipe_response = manager.route_query("dove trovo gli ingredienti per fare i pancake?")["text"]
    print("Recipe Response: ", recipe_response)
    
    recipe_response = manager.route_query("Cosa puoi fare")["text"]
    print("Info Response: ", recipe_response)
    
    ingredient_response = manager.route_query("cosa posso cucinare con uova, farina, e zucchero?")["text"]
    print("Ingredient-Based Recipe Response: ", ingredient_response)