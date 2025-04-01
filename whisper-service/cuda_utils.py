import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

def check_cuda_libraries():
    """
    Check CUDA availability and create symbolic links if needed.
    Returns True if CUDA is available, False otherwise.
    """
    logger.info("Checking CUDA availability...")
    
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA is available. CUDA version: {torch.version.cuda}")
            logger.info(f"PyTorch CUDA device count: {torch.cuda.device_count()}")
            logger.info(f"PyTorch CUDA device name: {torch.cuda.get_device_name(0)}")
            
            # Check for libcublas.so.11 (required by faster-whisper)
            cuda_lib_dir = '/usr/local/cuda/lib64'
            libcublas_path = os.path.join(cuda_lib_dir, 'libcublas.so.11')
            
            if not os.path.exists(libcublas_path):
                logger.warning(f"libcublas.so.11 not found at {libcublas_path}")
                
                # Look for libcublas.so.12
                libcublas12_path = os.path.join(cuda_lib_dir, 'libcublas.so.12')
                if os.path.exists(libcublas12_path):
                    try:
                        # Create symbolic link
                        os.symlink(libcublas12_path, libcublas_path)
                        logger.info(f"Created symbolic link: {libcublas_path} -> {libcublas12_path}")
                    except Exception as e:
                        logger.error(f"Error creating symbolic link: {e}")
            else:
                logger.info(f"libcublas.so.11 found at {libcublas_path}")
                
            return True
        else:
            logger.warning("CUDA not available through PyTorch")
            return False
    except Exception as e:
        logger.error(f"Error checking CUDA: {e}")
        return False