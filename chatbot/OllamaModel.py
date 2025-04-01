import os
import ollama
class OllamaModel:
    def __init__(self, model):
        self.model = model
        
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        os.environ["OLLAMA_HOST"] = self.ollama_host 

    def generate(self, messages):
        """
        Genera una risposta utilizzando il modello di Ollama.
        """
        response = ollama.chat(model=self.model, messages=messages)
        return response['message']['content']

if __name__ == "__main__":
    model = OllamaModel("qwen2.5:7b")
    messages = [{"role": "user", "content": "Ciao, come posso aiutarti?"}]
    response = model.generate(messages)
    print(response)
