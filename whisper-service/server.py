from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import logging
from cuda_utils import check_cuda_libraries

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run the CUDA check at startup
check_cuda_libraries()

# Import WhisperModel
from faster_whisper import WhisperModel
logger.info("Successfully imported WhisperModel")

app = Flask(__name__)
CORS(app)

class AudioTranscriber:
    def __init__(self, model_type="medium"):
        self.model = None
        self.model_type = model_type
        
        # Check if CPU is forced via environment variable
        force_cpu = os.environ.get("FORCE_CPU", "").lower() in ("true", "1", "yes")
        if force_cpu:
            logger.info("CPU usage forced by environment variable")
            self.device = "cpu"
            self.compute_type = "int8"
        else:
            # Simple CUDA check
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info("CUDA is available, using GPU")
                    self.device = "cuda"
                    self.compute_type = "float16"
                else:
                    logger.info("CUDA not available, using CPU")
                    self.device = "cpu"
                    self.compute_type = "int8"
            except Exception as e:
                logger.error(f"Error checking CUDA: {e}")
                self.device = "cpu"
                self.compute_type = "int8"
        
        logger.info(f"Final device configuration: device={self.device}, compute_type={self.compute_type}")
        self.load_model()

    def load_model(self):
        if self.model is None:
            try:
                logger.info(f"Loading model with: device={self.device}, compute_type={self.compute_type}")
                self.model = WhisperModel(
                    self.model_type,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model: {e}", exc_info=True)
                # If loading fails with any device, try CPU with int8
                if self.device != "cpu" or self.compute_type != "int8":
                    logger.info("Trying with CPU and int8")
                    self.device = "cpu"
                    self.compute_type = "int8"
                    try:
                        self.model = WhisperModel(
                            self.model_type,
                            device=self.device,
                            compute_type=self.compute_type
                        )
                        logger.info("Model loaded successfully with CPU")
                    except Exception as e2:
                        logger.error(f"Error loading model with CPU: {e2}", exc_info=True)

    def transcribe(self, audio_file):
        """
        Transcribe an audio file using the Whisper model.
        """
        self.load_model()
        
        if self.model is None:
            raise ValueError("Model not loaded.")   

        logger.info(f"Transcribing audio file: {audio_file}")
        segments, info = self.model.transcribe(
            audio_file,
            vad_filter=True,
            beam_size=5,
            language="it"
        )

        text = ""
        for segment in segments:
            text += segment.text

        logger.info("Transcription completed successfully")
        return text

# Initialize the transcriber at server startup
logger.info("Initializing AudioTranscriber")
transcriber = AudioTranscriber()

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    API endpoint to transcribe audio files.
    """
    logger.info("Received transcription request")
    
    if 'file' not in request.files:
        logger.warning("No file part in request")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.warning("No selected file")
        return jsonify({"error": "No selected file"}), 400
    
    logger.info(f"Processing file: {file.filename}")
    
    # Save the file temporarily
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    file.save(temp_file.name)
    temp_file.close()
    
    try:
        # Transcribe the audio
        logger.info(f"Starting transcription of temporary file: {temp_file.name}")
        text = transcriber.transcribe(temp_file.name)
        
        # Remove the temporary file
        os.unlink(temp_file.name)
        logger.info("Temporary file removed")
        
        logger.info("Transcription successful, returning result")
        return jsonify({"text": text})
    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        # Make sure to remove the temporary file even in case of error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
            logger.info("Temporary file removed after error")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    return jsonify({"status": "ok", "device": transcriber.device}), 200

if __name__ == '__main__':
    logger.info("Starting Whisper transcription service on port 8102")
    app.run(host='0.0.0.0', port=8102)