import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

class TTS_Piper:
    
    def __init__(self):
        self.model=os.environ.get("PIPER_MODEL")
        self.configg=os.environ.get("PIPER_MODEL_JSON")
        self.output_file="piper.wav"
        self.piper_exe = os.environ.get("PIPER_EXE")
        

    def run_tts(self, text): 
        print("piper running...")

        command = f"echo '{text}' | \"{self.piper_exe}\" --model \"{self.model}\" --config \"{self.configg}\" --output_file {self.output_file}"
        subprocess.run(command, shell=True)
        
        print("piper terminated")
        
        return self.output_file

    def remove_audio(self):
        try:
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
        except:
            print("Error  deleting file")

if __name__ == "__main__":
    tts = TTS_Piper()
    tts.run_tts("Dove posso trovare il latte?")