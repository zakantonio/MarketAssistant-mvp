FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy necessary files
COPY requirements.txt .
COPY server.py .
COPY cuda_utils.py .

# Install PyTorch with CUDA support
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Create symbolic links for CUDA 11 compatibility
RUN mkdir -p /usr/local/cuda/lib64 && \
    find /usr/lib/x86_64-linux-gnu -name "libcudnn*.so*" -exec ln -sf {} /usr/local/cuda/lib64/ \; && \
    find /usr/lib/x86_64-linux-gnu -name "libcublas*.so*" -exec ln -sf {} /usr/local/cuda/lib64/ \; && \
    find /usr/lib/x86_64-linux-gnu -name "libcudart*.so*" -exec ln -sf {} /usr/local/cuda/lib64/ \; && \
    ln -sf /usr/local/cuda/lib64/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so.11 && \
    ln -sf /usr/local/cuda/lib64/libcublasLt.so.12 /usr/local/cuda/lib64/libcublasLt.so.11 && \
    ln -sf /usr/local/cuda/lib64/libcudart.so.12 /usr/local/cuda/lib64/libcudart.so.11 && \
    ln -sf /usr/local/cuda/lib64/libcudnn.so.8 /usr/local/cuda/lib64/libcudnn.so.7

# Update LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

# Expose port
EXPOSE 8102

# Start the server
CMD ["python3", "server.py"]