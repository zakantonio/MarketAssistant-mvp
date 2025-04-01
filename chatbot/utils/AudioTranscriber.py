import requests
import os
import time

class AudioTranscriber:
    def __init__(self, service_url=None):
        self.service_url = service_url or os.environ.get("WHISPER_SERVICE_URL", "http://whisper-service:8102")
        
    def transcribe(self, audio_file, max_retries=3):
        """
        Sends the audio file to the Whisper service for transcription
        
        Args:
            audio_file: Path to the audio file to transcribe
            max_retries: Maximum number of retry attempts in case of error
        
        Returns:
            str: Transcribed text
        """
        # Verify that the file exists
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        retries = 0
        while retries < max_retries:
            try:
                # Prepare the file for sending
                with open(audio_file, 'rb') as f:
                    files = {'file': f}
                    
                    # Send the request to the Whisper service
                    print(f"Sending request to {self.service_url}/transcribe")
                    response = requests.post(
                        f"{self.service_url}/transcribe",
                        files=files,
                        timeout=120  # Increase timeout for long audio files
                    )
                
                # Handle the response
                if response.status_code != 200:
                    error_msg = response.json().get('error', 'Unknown error')
                    raise Exception(f"Error during transcription: {error_msg}")
                
                # Extract the transcribed text
                result = response.json()
                text = result.get('text', '')
                
                # Delete the audio file if it still exists
                try:
                    pass
                    #os.remove(audio_file)
                except:
                    print("Error while deleting the file")
                    
                return text
                
            except Exception as e:
                retries += 1
                print(f"Attempt {retries}/{max_retries} failed: {e}")
                if retries < max_retries:
                    # Wait before retrying
                    time.sleep(2)
                else:
                    raise Exception(f"Unable to transcribe audio after {max_retries} attempts: {e}")

if __name__ == "__main__":
    # Initialize the transcriber
    # For local testing, use localhost URL
    transcriber = AudioTranscriber(service_url="http://localhost:8102")
    
    # Path to the test audio file
    audio_file = ".\\piper.wav"
    
    # Test the transcription
    try:
        text = transcriber.transcribe(audio_file)
        print("Transcription result:")
        print(text)
    except Exception as e:
        print(f"Error during transcription: {e}")
