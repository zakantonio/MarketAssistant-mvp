import os
import sys
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

class InfoAgent:
    """
    An agent that provides information about its capabilities.
    """
    def __init__(self, api_url=DATABASE_URL, llm= None):
        """
        Initialize the recipe search agent with API URL and LLM model
        
        Args:
            api_url: Base URL for the product search API
            model_name: Name of the Ollama model to use
            message_broker: Optional message broker for sending updates
        """
        logger.info(f"InfoAgent.__init__: Initializing with api_url={api_url}")
        self.api_url = api_url
        self.llm = llm
        self.setup_agent()

    def setup_agent(self):
        """Set up the CrewAI agent with the appropriate tools and configuration."""
        self.agent = Agent(
            role="Information Provider",
            goal="Respond to the question 'Cosa sai fare?' by listing the system's capabilities.",
            backstory="I am a simple assistant that informs users about the system's functionalities.",
            verbose=True,
            allow_delegation=False,
            tools=[
                Tool(
                    name="list_capabilities",
                    description="List the system's capabilities.",
                    func=self.list_capabilities
                )
            ]
        )

    def list_capabilities(self, query: str) -> str:
        """
        List the system's capabilities.
        
        Args:
            query: The user's query
            
        Returns:
            A string response listing the capabilities.
        """
        return (
            "Posso fare le seguenti cose:\n"
            "- Ricercare prodotti nel negozio\n"
            "- Riconoscere e fornire informazioni sulle ricette"
            "- Suggerire ricette in base agli ingredienti forniti"
        )

    def process_query(self, query: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query and return a response.
        
        Args:
            query: The user's query
            client_id: Optional client ID for sending updates
            
        Returns:
            A dictionary containing the text response.
        """
        logger.info(f"InfoAgent.process_query: Processing query: {query}, client_id: {client_id}")
        classification_prompt = [
            {"role": "system", "content": (
                "You are a classifier. Determine if the following query is asking about the system's capabilities. "
                "Examples of queries about capabilities include: 'Cosa sai fare?', 'Quali sono le tue capacità?', "
                "'Cosa può fare il sistema?'. Respond with 'yes' if the query is about capabilities, or 'no' otherwise."
            )},
            {"role": "user", "content": query}
        ]
        
        try:
            print("Sending prompt to LLM:", classification_prompt)
            llm_response = self.llm.generate(classification_prompt)
            print("LLM response:", llm_response)
            
            if llm_response:
                llm_response = llm_response.strip().lower()
            else:
                raise ValueError("LLM response is empty or invalid.")
            
            if llm_response == "yes":
                text_response = self.list_capabilities(query)
            elif llm_response == "no":
                text_response = "Mi dispiace, non posso rispondere alla tua domanda."
            else:
                text_response = "Non sono sicuro di come rispondere alla tua domanda. Puoi riformularla?"
        except Exception as e:
            print(f"Error during LLM query processing: {e}")
            # Fallback: Check for keywords only if the LLM fails completely
            keywords = ["cosa", "capacità", "può fare", "sai fare"]
            if any(keyword in query.lower() for keyword in keywords):
                text_response = self.list_capabilities(query)
            else:
                text_response = f"Si è verificato un errore durante l'elaborazione della query: {e}"

        return {
            "text": text_response,
            "results": None
        }

# Example usage
if __name__ == "__main__":
    agent = InfoAgent()
    response = agent.process_query("cosa sai fare?")
    print("Response: ", response["text"])