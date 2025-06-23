import numpy as np
import cv2
import pywt
from PIL import Image
import logging

def load_and_preprocess_image(image_path):
    """Load and preprocess image for fusion"""
    try:
        # Load image using PIL
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Convert RGB to grayscale for DWT processing
        if len(img_array.shape) == 3:
            img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_array
        
        return img_gray, img_array
    except Exception as e:
        logging.error(f"Error loading image {image_path}: {str(e)}")
        return None, None

def resize_images_to_same_size(images):
    """Resize all images to the same size (minimum dimensions)"""
    if not images:
        return []
    
    # Find minimum dimensions
    min_height = min(img.shape[0] for img in images)
    min_width = min(img.shape[1] for img in images)
    
    # Make dimensions even for DWT
    min_height = min_height - (min_height % 2)
    min_width = min_width - (min_width % 2)
    
    resized_images = []
    for img in images:
        resized = cv2.resize(img, (min_width, min_height))
        resized_images.append(resized)
    
    return resized_images

def dwt_fusion_two_images(img1, img2, wavelet='db4'):
    """Fuse two images using DWT"""
    try:
        # Perform DWT on both images
        coeffs1 = pywt.dwt2(img1, wavelet)
        coeffs2 = pywt.dwt2(img2, wavelet)
        
        # Extract approximation and detail coefficients
        cA1, (cH1, cV1, cD1) = coeffs1
        cA2, (cH2, cV2, cD2) = coeffs2
        
        # Fusion rules:
        # For approximation coefficients: average
        cA_fused = (cA1 + cA2) / 2
        
        # For detail coefficients: maximum absolute value
        cH_fused = np.where(np.abs(cH1) > np.abs(cH2), cH1, cH2)
        cV_fused = np.where(np.abs(cV1) > np.abs(cV2), cV1, cV2)
        cD_fused = np.where(np.abs(cD1) > np.abs(cD2), cD1, cD2)
        
        # Reconstruct the fused image
        coeffs_fused = (cA_fused, (cH_fused, cV_fused, cD_fused))
        fused_image = pywt.idwt2(coeffs_fused, wavelet)
        
        # Normalize to 0-255 range
        fused_image = np.clip(fused_image, 0, 255).astype(np.uint8)
        
        return fused_image
    except Exception as e:
        logging.error(f"Error in DWT fusion: {str(e)}")
        return None

def multi_image_dwt_fusion(images, wavelet='db4'):
    """Fuse multiple images using iterative DWT fusion"""
    if len(images) < 2:
        logging.error("Need at least 2 images for fusion")
        return None
    
    # Start with the first image
    fused = images[0].copy()
    
    # Iteratively fuse with remaining images
    for i in range(1, len(images)):
        fused = dwt_fusion_two_images(fused, images[i], wavelet)
        if fused is None:
            logging.error(f"Fusion failed at image {i}")
            return None
    
    return fused

def enhance_contrast(image, alpha=1.2, beta=10):
    """Enhance contrast of the fused image"""
    try:
        enhanced = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        return enhanced
    except Exception as e:
        logging.error(f"Error enhancing contrast: {str(e)}")
        return image

def process_fusion(image_paths, output_path):
    """Main function to process multi-image fusion"""
    try:
        logging.info(f"Starting fusion process with {len(image_paths)} images")
        
        # Load and preprocess images
        gray_images = []
        color_images = []
        
        for path in image_paths:
            gray_img, color_img = load_and_preprocess_image(path)
            if gray_img is None:
                logging.error(f"Failed to load image: {path}")
                return False
            gray_images.append(gray_img)
            color_images.append(color_img)
        
        # Resize images to same size
        gray_images = resize_images_to_same_size(gray_images)
        if not gray_images:
            logging.error("No valid images after resizing")
            return False
        
        logging.info(f"Images resized to: {gray_images[0].shape}")
        
        # Perform DWT fusion
        fused_gray = multi_image_dwt_fusion(gray_images)
        if fused_gray is None:
            logging.error("DWT fusion failed")
            return False
        
        # Enhance contrast
        fused_enhanced = enhance_contrast(fused_gray)
        
        # Convert to RGB for saving
        if len(fused_enhanced.shape) == 2:
            fused_rgb = cv2.cvtColor(fused_enhanced, cv2.COLOR_GRAY2RGB)
        else:
            fused_rgb = fused_enhanced
        
        # Save the result
        result_image = Image.fromarray(fused_rgb)
        result_image.save(output_path, 'PNG', quality=95)
        
        logging.info(f"Fusion completed successfully. Result saved to: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error in fusion process: {str(e)}")
        return False

def get_fusion_info():
    """Return information about the fusion algorithm"""
    return {
        'algorithm': 'Discrete Wavelet Transform (DWT) Fusion',
        'wavelet': 'Daubechies 4 (db4)',
        'fusion_rules': {
            'approximation_coefficients': 'Average',
            'detail_coefficients': 'Maximum absolute value'
        },
        'enhancement': 'Contrast enhancement with alpha=1.2, beta=10',
        'supported_formats': ['JPEG', 'PNG', 'TIFF']
    }
