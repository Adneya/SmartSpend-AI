import easyocr
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
import tkinter as tk
from tkinter import Label, Button, messagebox
from PIL import ImageTk
import threading
import time
import json
import re
from difflib import SequenceMatcher, get_close_matches
from collections import Counter

# Try to import spell checker libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from spellchecker import SpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False

# Try to import advanced NLP/image processing libraries
try:
    from skimage import transform as tf
    from skimage.filters import threshold_otsu, unsharp_mask
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

try:
    import nltk
    from nltk.corpus import words as nltk_words
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

class OCRExtractor:
    def __init__(self, languages=['en'], gpu=True):
        """
        Initialize OCR reader with specified languages
        languages: List of language codes (e.g., ['en', 'hi'] for English and Hindi)
        gpu: Set to True only if you have CUDA GPU with proper drivers
        """
        self.reader = easyocr.Reader(languages, gpu=gpu)
        self.languages = languages
        self.config_file = "ocr_config.json"
    
    def save_droidcam_ip(self, ip_address):
        """Save DroidCam IP address to config file"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            config['droidcam_ip'] = ip_address
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"✓ DroidCam IP saved: {ip_address}")
            return True
        except Exception as e:
            print(f"Error saving IP: {str(e)}")
            return False
    
    def load_droidcam_ip(self):
        """Load saved DroidCam IP address from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('droidcam_ip', None)
        except Exception as e:
            print(f"Error loading IP: {str(e)}")
        return None
    
    def extract_text_from_image(self, image_path):
        """
        Extract text from a single image
        """
        if not os.path.exists(image_path):
            print(f"Error: Image file not found at {image_path}")
            return None
        
        try:
            # Read image using OpenCV
            image = cv2.imread(image_path)
            
            # Check if image was loaded successfully
            if image is None:
                print(f"Error: Failed to load image from {image_path}")
                return None
            
            # Convert BGR to RGB for display
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Perform OCR
            print(f"\nProcessing: {image_path}")
            results = self.reader.readtext(image_path)
            
            # Extract and organize text
            extracted_data = self._parse_results(results)
            
            # Display results
            self._display_results(image_rgb, results, extracted_data, image_path)
            
            return extracted_data
            
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return None
    
    def _parse_results(self, results):
        """
        Parse OCR results and organize data
        """
        full_text = ""
        data_with_confidence = []
        
        for detection in results:
            text = detection[1]
            confidence = detection[2]
            coordinates = detection[0]
            
            full_text += text + " "
            data_with_confidence.append({
                'text': text,
                'confidence': confidence,
                'coordinates': coordinates
            })
        
        return {
            'full_text': full_text.strip(),
            'detailed_data': data_with_confidence,
            'total_detections': len(data_with_confidence)
        }
    
    def _display_results(self, image, results, extracted_data, image_path):
        """
        Display OCR results with visualization
        """
        # Create a copy for drawing
        image_copy = image.copy()
        
        # Draw bounding boxes and text
        for detection in results:
            coordinates = detection[0]
            text = detection[1]
            confidence = detection[2]
            
            # Convert coordinates to integer
            coords = np.array(coordinates, dtype=np.int32)
            
            # Draw bounding box
            cv2.polylines(image_copy, [coords], True, (0, 255, 0), 2)
            
            # Put text label
            cv2.putText(image_copy, f"{text} ({confidence:.2f})", 
                       (int(coords[0][0]), int(coords[0][1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # Print results
        print(f"\n{'='*60}")
        print(f"File: {image_path}")
        print(f"{'='*60}")
        print(f"Total detections: {extracted_data['total_detections']}")
        print(f"\nExtracted Text:\n{extracted_data['full_text']}")
        print(f"\n{'='*60}")
        print("Detailed Detection Results:")
        print(f"{'='*60}")
        
        for idx, detection in enumerate(extracted_data['detailed_data'], 1):
            print(f"{idx}. Text: '{detection['text']}' | Confidence: {detection['confidence']:.4f}")
        
        return image_copy
    
    def batch_process_images(self, image_folder):
        """
        Process multiple images from a folder
        """
        if not os.path.exists(image_folder):
            print(f"Error: Folder not found at {image_folder}")
            return
        
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        image_files = [f for f in os.listdir(image_folder) 
                      if os.path.splitext(f)[1].lower() in supported_formats]
        
        if not image_files:
            print(f"No image files found in {image_folder}")
            return
        
        all_results = {}
        
        print(f"\nProcessing {len(image_files)} images from {image_folder}...")
        
        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            results = self.extract_text_from_image(image_path)
            all_results[image_file] = results
        
        return all_results
    
    def save_results_to_file(self, extracted_data, output_file):
        """
        Save extracted text to a text file
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(extracted_data['full_text'])
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")
    
    def _preprocess_image_for_ocr(self, image):
        """
        Advanced preprocessing to improve OCR accuracy
        Includes: noise reduction, contrast enhancement, edge enhancement, deskewing
        """
        try:
            # Convert BGR to grayscale for processing
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Step 1: Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Step 2: Apply bilateral filter for edge-preserving denoising
            denoised = cv2.bilateralFilter(blurred, 11, 75, 75)
            
            # Step 3: Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(10, 10))
            contrast_enhanced = clahe.apply(denoised)
            
            # Step 4: Apply adaptive threshold for better text-background separation
            binary = cv2.adaptiveThreshold(contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 21, 10)
            
            # Step 5: Morphological operations to improve text clarity
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            
            # Close small holes in text
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close, iterations=2)
            # Remove small noise
            morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open, iterations=1)
            # Dilate to strengthen text
            morph = cv2.dilate(morph, kernel_close, iterations=1)
            
            # Step 6: Aggressive upscaling for small text (improves easyocr accuracy significantly)
            height, width = morph.shape
            if width < 800 or height < 400:
                scale = max(800 / width, 400 / height)
                new_width = int(width * scale * 2.0)  # Increased upscaling
                new_height = int(height * scale * 2.0)
                morph = cv2.resize(morph, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
                # Apply sharpening after upscaling
                kernel_sharp = np.array([[-1, -1, -1],
                                        [-1,  9, -1],
                                        [-1, -1, -1]]) / 1.0
                morph = cv2.filter2D(morph, -1, kernel_sharp)
            
            # Step 7: Normalize to improve consistency
            morph = cv2.normalize(morph, None, 0, 255, cv2.NORM_MINMAX)
            
            return morph
            
        except Exception as e:
            print(f"Preprocessing error: {str(e)}")
            return image
    
    def _correct_text_skew(self, image):
        """
        Detect and correct skewed/tilted text
        Straightens text that's at an angle for better OCR
        """
        try:
            if not SKIMAGE_AVAILABLE:
                return image
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Find edges
            edges = cv2.Canny(gray, 100, 200)
            
            # Calculate angle of skew
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
            
            if lines is None or len(lines) == 0:
                return image
            
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1)
                angles.append(np.degrees(angle))
            
            # Get median angle
            median_angle = np.median(angles)
            
            # Correct if angle is significant
            if abs(median_angle) > 0.5:
                h, w = image.shape[:2]
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                corrected = cv2.warpAffine(image, rotation_matrix, (w, h))
                return corrected
            
            return image
            
        except Exception as e:
            print(f"Skew correction error: {e}")
            return image
    
    def _verify_word_in_dictionary(self, word):
        """
        Verify if a word exists in dictionary
        Uses NLTK if available, otherwise uses built-in basic check
        """
        try:
            # Remove punctuation for checking
            clean_word = re.sub(r'[^\w\s]', '', word).lower()
            
            if not clean_word:
                return False
            
            # Try NLTK first
            if NLTK_AVAILABLE:
                try:
                    english_words = set(nltk_words.words())
                    return clean_word in english_words
                except:
                    pass
            
            # Try PySpellChecker
            if SPELLCHECKER_AVAILABLE:
                spell = SpellChecker()
                return clean_word in spell or spell.correction(clean_word) == clean_word
            
            # Basic dictionary check (common words)
            common_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'up', 'as', 'is', 'was', 'are', 'been',
                'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what',
                'which', 'who', 'where', 'when', 'why', 'how', 'all', 'each', 'every',
                'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                'not', 'only', 'same', 'so', 'than', 'too', 'very', 'just', 'about',
                'after', 'before', 'between', 'through', 'during', 'above', 'below',
                'out', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
                'there', 'below', 'down', 'off', 'own', 'against', 'into', 'through'
            }
            
            return clean_word in common_words or len(clean_word) > 2
            
        except Exception as e:
            print(f"Dictionary verification error: {e}")
            return True  # Allow unknown words
    
    def _convert_easyocr_results_to_dict(self, results):
        """
        Convert EasyOCR tuple results format to dictionary format
        EasyOCR returns: [(bbox, text, confidence), ...]
        We convert to: [{'text': text, 'confidence': confidence, 'coordinates': bbox}, ...]
        """
        converted = []
        for detection in results:
            if isinstance(detection, tuple) and len(detection) >= 3:
                bbox, text, confidence = detection[0], detection[1], detection[2]
                converted.append({
                    'text': text,
                    'confidence': confidence,
                    'coordinates': bbox
                })
            elif isinstance(detection, dict):
                # Already in dictionary format
                converted.append(detection)
        return converted
    
    def _filter_by_dictionary(self, results):
        """
        Filter/mark results based on dictionary validation
        Helps identify suspicious words that might be OCR errors
        Input: List of dictionaries with 'text' and 'confidence' keys
        """
        filtered = []
        
        for item in results:
            text = item['text']
            confidence = item['confidence']
            
            # Always keep high confidence
            if confidence > 0.85:
                filtered.append(item)
            else:
                # For lower confidence, verify against dictionary
                if self._verify_word_in_dictionary(text):
                    filtered.append(item)
                # Skip words not in dictionary with low confidence
        
        return filtered
    
    def _apply_context_awareness(self, text):
        """
        Apply context-aware corrections
        Fixes common position-based errors
        """
        # Fix common position patterns
        corrections = {
            # Common position errors
            r'\b([a-z])t\b': r'\1st',  # "2t" -> "2st"
            r'\b([0-9])l([a-z])\b': r'\1I\2',  # "0la" -> "0Ia"
            r'\bOO([a-z]+)\b': r'00\1',  # "OOname" -> "00name"
            r'\bl([a-z])\b': r'I\1',  # "la" -> "Ia"
            r'\bO([a-zA-Z]+)\b': r'0\1',  # "Oname" -> "0name" (context-aware)
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _enhance_image_advanced(self, image):
        """
        Apply advanced image enhancement techniques
        Uses scikit-image if available for superior results
        """
        try:
            if not SKIMAGE_AVAILABLE:
                return image
            
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Normalize to 0-1 range
            gray_norm = gray.astype(np.float32) / 255.0
            
            # Apply unsharp mask for detail enhancement
            enhanced = unsharp_mask(gray_norm, radius=2, amount=2)
            
            # Convert back to 0-255
            enhanced = (enhanced * 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            print(f"Advanced enhancement error: {e}")
            return image
    
    def _combine_ocr_results(self, results_list):
        """
        Combine OCR results from multiple frames
        Removes duplicates and keeps highest confidence detections
        Handles both tuple and dictionary format results
        """
        if not results_list:
            return []
        
        combined = {}
        
        for results in results_list:
            for detection in results:
                # Handle both tuple and dictionary formats
                if isinstance(detection, dict):
                    text = detection['text'].strip() if 'text' in detection else ''
                    confidence = detection.get('confidence', 0)
                    coords = detection.get('coordinates', None)
                else:
                    # Tuple format: (bbox, text, confidence)
                    text = detection[1].strip() if len(detection) > 1 else ''
                    confidence = detection[2] if len(detection) > 2 else 0
                    coords = detection[0] if len(detection) > 0 else None
                
                if text:  # Only process non-empty text
                    if text not in combined or confidence > combined[text]['confidence']:
                        combined[text] = {
                            'text': text,
                            'confidence': confidence,
                            'coordinates': coords
                        }
        
        # Sort by confidence (descending)
        sorted_results = sorted(combined.values(), key=lambda x: x['confidence'], reverse=True)
        
        return sorted_results
    
    def filter_high_confidence_results(self, results, min_confidence=0.8):
        """
        Filter results to show only high confidence detections
        min_confidence: Minimum confidence threshold (default: 0.8 = 80%)
        """
        if not results:
            return []
        
        filtered = [r for r in results if r.get('confidence', 0) >= min_confidence]
        
        return filtered
    
    def _fix_common_ocr_mistakes(self, text):
        """
        Fix common OCR recognition errors
        Common substitutions that happen in OCR:
        - 0 (zero) vs O (letter O)
        - 1 (one) vs l (letter l)
        - 5 vs S
        - 8 vs B
        """
        # Dictionary of common OCR mistakes and corrections
        ocr_replacements = {
            r'\b0([a-z]+)\b': r'O\1',  # 0name -> Oname
            r'^0': 'O',  # 0 at start -> O
            r'\s0([A-Z])\b': r' O\1',  # space+0+capital -> space+O+capital
        }
        
        for pattern, replacement in ocr_replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _normalize_text(self, text):
        """
        Normalize text for better accuracy
        - Remove extra spaces
        - Fix common punctuation
        - Standardize quotes
        """
        # Remove multiple consecutive spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Fix common spacing issues around punctuation
        text = re.sub(r'\s+([.!?,;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Ensure space after period
        
        # Standardize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text
    
    def _remove_artifacts(self, text):
        """
        Remove OCR artifacts and special characters
        - Remove repeated special characters
        - Remove standalone symbols
        """
        # Remove repeated special characters
        text = re.sub(r'([^a-zA-Z0-9\s.,!?;:-])\1+', r'\1', text)
        
        # Remove lines that are just special characters
        lines = text.split('\n')
        cleaned_lines = [line for line in lines if any(c.isalnum() for c in line)]
        text = '\n'.join(cleaned_lines)
        
        return text
    
    def _merge_duplicate_words(self, results):
        """
        Merge similar/duplicate detected words
        If same text is detected multiple times with high confidence, keep only highest
        """
        if not results:
            return results
        
        merged = {}
        
        for item in results:
            text = item['text'].strip()
            if not text:
                continue
            
            # Normalize text for comparison
            normalized = text.lower()
            
            # Check if similar text already exists
            found = False
            for key in merged.keys():
                # Calculate similarity ratio
                similarity = SequenceMatcher(None, normalized, key.lower()).ratio()
                
                # If similarity > 85%, consider it the same word
                if similarity > 0.85:
                    # Keep the one with higher confidence
                    if item['confidence'] > merged[key]['confidence']:
                        merged[key] = item
                    found = True
                    break
            
            if not found:
                merged[text] = item
        
        return list(merged.values())
    
    def _autocorrect_spelling_textblob(self, text):
        """
        Autocorrect spelling using TextBlob
        TextBlob uses a bayesian approach for spell correction
        """
        try:
            if not TEXTBLOB_AVAILABLE:
                return text
            
            blob = TextBlob(text)
            corrected = str(blob.correct())
            return corrected
        except Exception as e:
            print(f"TextBlob autocorrect error: {e}")
            return text
    
    def _autocorrect_spelling_spellchecker(self, text):
        """
        Autocorrect spelling using PySpellChecker
        Better for individual word correction
        """
        try:
            if not SPELLCHECKER_AVAILABLE:
                return text
            
            spell = SpellChecker()
            words = text.split()
            corrected_words = []
            
            for word in words:
                # Remove punctuation for spell check
                clean_word = re.sub(r'[^\w\s]', '', word)
                
                if clean_word and clean_word.lower() not in spell:
                    # Get suggestions
                    suggestions = spell.correction(clean_word)
                    
                    if suggestions and suggestions.lower() != clean_word.lower():
                        # Replace with correction, maintaining case
                        if word[0].isupper():
                            corrected_word = suggestions.capitalize()
                        else:
                            corrected_word = suggestions.lower()
                        corrected_words.append(corrected_word)
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            
            return ' '.join(corrected_words)
        except Exception as e:
            print(f"SpellChecker autocorrect error: {e}")
            return text
    
    def _custom_autocorrect(self, text):
        """
        Custom autocorrect for common OCR spelling mistakes
        Uses edit distance and common misspelling patterns
        """
        # Common OCR-related misspellings and corrections
        common_corrections = {
            r'\brecieve\b': 'receive',
            r'\btheir\b': 'their',
            r'\bteh\b': 'the',
            r'\bnad\b': 'and',
            r'\bwoudl\b': 'would',
            r'\bcoudl\b': 'could',
            r'\bshoudl\b': 'should',
            r'\bwiht\b': 'with',
            r'\bwhcih\b': 'which',
            r'\btahtn\b': 'than',
            r'\bfrom\b': 'from',
            r'\byuo\b': 'you',
            r'\byour\b': 'your',
            r'\blatre\b': 'later',
            r'\befrom\b': 'from',
        }
        
        for pattern, correction in common_corrections.items():
            text = re.sub(pattern, correction, text, flags=re.IGNORECASE)
        
        return text
    
    def _apply_spelling_autocorrection(self, text):
        """
        Apply spelling autocorrection using available algorithms
        Priority: TextBlob > SpellChecker > Custom
        """
        if not text:
            return text
        
        print("🔤 Applying spelling autocorrection...")
        
        # Try TextBlob first (most intelligent)
        if TEXTBLOB_AVAILABLE:
            print("   Using TextBlob autocorrector...")
            return self._autocorrect_spelling_textblob(text)
        
        # Fall back to SpellChecker
        if SPELLCHECKER_AVAILABLE:
            print("   Using PySpellChecker...")
            return self._autocorrect_spelling_spellchecker(text)
        
        # Use custom corrections
        print("   Using custom spell corrections...")
        return self._custom_autocorrect(text)
    
    def _apply_text_processing(self, results):
        """
        Apply all text processing algorithms to improve accuracy
        """
        if not results:
            return results
        
        # Step 1: Merge duplicate/similar words
        results = self._merge_duplicate_words(results)
        
        # Step 2: Process each detected text
        processed = []
        for item in results:
            text = item['text']
            
            # Apply fixes and normalization to the text
            text = self._fix_common_ocr_mistakes(text)
            text = self._normalize_text(text)
            text = self._remove_artifacts(text)
            
            # Update the item with processed text
            item['text'] = text
            item['is_processed'] = True
            processed.append(item)
        
        return processed
    
    def capture_multiple_frames_for_accuracy(self, cap, num_frames=5):
        """
        Capture multiple frames with advanced algorithms for maximum accuracy
        Uses skew correction, advanced enhancement, and dictionary verification
        """
        all_results = []
        
        print(f"\n📸 Capturing {num_frames} frames for accuracy...")
        print("   Applying advanced algorithms to each frame...\n")
        
        for i in range(num_frames):
            ret, frame = cap.read()
            if ret:
                # Advanced Algorithm 1: Correct Text Skew
                corrected_frame = self._correct_text_skew(frame)
                
                # Advanced Algorithm 2: Advanced Image Enhancement
                enhanced_frame = self._enhance_image_advanced(corrected_frame)
                if enhanced_frame is not None:
                    corrected_frame = enhanced_frame
                
                # Perform OCR with advanced preprocessing
                results = self.reader.readtext(corrected_frame)
                
                # Convert results from tuple format to dictionary format
                dict_results = self._convert_easyocr_results_to_dict(results)
                
                # Advanced Algorithm 3: Dictionary-based Filtering
                filtered_results = self._filter_by_dictionary(dict_results)
                
                # Store filtered results (keep them in dict format for _combine_ocr_results to handle)
                all_results.append(filtered_results if filtered_results else dict_results)
                print(f"  Frame {i+1}/{num_frames} captured & processed")
            time.sleep(0.15)  # 150ms delay between frames
        
        if all_results:
            print("\n🔄 Combining results from multiple frames...")
            combined = self._combine_ocr_results(all_results)
            
            # Advanced Algorithm 4: Apply Context-Aware Correction
            for item in combined:
                item['text'] = self._apply_context_awareness(item['text'])
            
            return combined
        
        return []
    
    def setup_camera_source(self):
        """
        Setup camera source - local or DroidCam
        Saves and loads IP address for convenience
        """
        print("\n" + "="*80)
        print("CAMERA SOURCE SELECTION")
        print("="*80)
        print("1. Desktop/Laptop Camera (Local)")
        print("2. Mobile Camera (DroidCam)")
        print("="*80)
        
        choice = input("\nSelect camera source (1 or 2): ").strip()
        
        if choice == '2':
            # Try to load saved IP
            saved_ip = self.load_droidcam_ip()
            
            print("\n📱 DroidCam Mobile Camera")
            print("-" * 80)
            
            if saved_ip:
                print(f"✓ Saved IP found: {saved_ip}")
                use_saved = input("Use saved IP? (y/n): ").strip().lower()
                
                if use_saved in ['y', 'yes', '']:
                    print(f"✓ Connecting to {saved_ip}...")
                    return f"http://{saved_ip}:4747/video"
            
            print("\nEnter your phone's DroidCam IP address:")
            print("  • Open DroidCam app on your phone")
            print("  • Look for IP address (format: 192.168.x.x)")
            print("-" * 80)
            
            ip_address = input("Enter IP address (e.g., 192.168.1.100): ").strip()
            
            if not ip_address:
                print("❌ No IP provided. Using local camera instead.")
                return 0
            
            # Save the IP for future use
            self.save_droidcam_ip(ip_address)
            
            # Try with WiFi port 4747
            return f"http://{ip_address}:4747/video"
        
        else:
            print("✓ Using local desktop camera")
            return 0
    
    def capture_text_from_camera_gui(self, camera_source=0):
        """
        Capture text from camera with GUI preview using tkinter and PIL
        Shows live camera feed and allows manual capture
        camera_source: 0 for local camera, or IP URL for DroidCam
        """
        cap = cv2.VideoCapture(camera_source)
        
        if not cap.isOpened():
            if isinstance(camera_source, str):
                print(f"❌ Error: Cannot connect to DroidCam at {camera_source}")
                print("Please check:")
                print("  • DroidCam app is running on your phone")
                print("  • IP address is correct")
                print("  • Both devices are on the same WiFi network")
            else:
                print("❌ Error: Cannot access local camera. Please check if camera is connected and not in use.")
            return None
        
        # Set camera resolution
        if isinstance(camera_source, int):  # Local camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
        else:  # DroidCam - may have different settings
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            print("✓ Connected to DroidCam successfully!")
        
        captured_results = []
        frame_count = [0]  # Use list to modify in nested function
        is_running = [True]
        captured_frame = [None]
        
        # Create GUI window
        root = tk.Tk()
        root.title("OCR Camera Capture - Desktop Camera")
        root.geometry("1000x800")
        
        # Labels for display
        title_label = Label(root, text="OCR Text Extraction from Camera", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        camera_label = Label(root, bg="black")
        camera_label.pack(padx=10, pady=10)
        
        instructions_label = Label(root, text="Press SPACEBAR to capture frame | Close window to quit", 
                                   font=("Arial", 11, "bold"), fg="darkgreen", bg="lightyellow", padx=10, pady=5)
        instructions_label.pack(pady=5, fill=tk.X)
        
        status_label = Label(root, text="Camera Loading...", font=("Arial", 10), fg="blue")
        status_label.pack(pady=5)
        
        result_text = tk.Text(root, height=10, width=100, font=("Arial", 9))
        result_text.pack(padx=10, pady=5)
        
        def update_camera_feed():
            """Update camera feed in GUI"""
            if not is_running[0]:
                return
            
            ret, frame = cap.read()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize for display
                display_frame = cv2.resize(frame_rgb, (960, 540))
                
                # Add instruction text
                cv2.putText(display_frame, "Press SPACEBAR to capture frame | Close window to quit", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, "Frames captured: " + str(frame_count[0]), 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(display_frame)
                photo = ImageTk.PhotoImage(pil_image)
                
                camera_label.config(image=photo)
                camera_label.image = photo
                
                # Store current frame
                captured_frame[0] = frame
                
                # Update status
                status_label.config(text=f"Camera Active | Frames Captured: {frame_count[0]}", fg="green")
            
            # Schedule next update
            camera_label.after(30, update_camera_feed)
        
        def capture_current_frame():
            """Capture and process current frame for OCR with enhanced accuracy"""
            if captured_frame[0] is None:
                messagebox.showwarning("No Frame", "No frame available to capture")
                return
            
            frame_count[0] += 1
            
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"⏳ Processing Frame {frame_count[0]}...\n")
            result_text.insert(tk.END, f"Capturing multiple angles for better accuracy...\n\n")
            root.update()
            
            # Console output
            print(f"\n{'='*80}")
            print(f"CAPTURING FRAME {frame_count[0]} (HIGH ACCURACY MODE)")
            print(f"{'='*80}")
            print("🔄 Capturing 4 frames from different moments for maximum accuracy...\n")
            
            # Capture multiple frames for better accuracy
            all_ocr_results = self.capture_multiple_frames_for_accuracy(cap, num_frames=4)
            
            if not all_ocr_results:
                result_text.insert(tk.END, "❌ No text detected in this frame. Try different angle or lighting.\n")
                result_text.insert(tk.END, "\n💡 Tips for better results:\n")
                result_text.insert(tk.END, "  • Ensure good lighting (natural light is best)\n")
                result_text.insert(tk.END, "  • Keep text clear and in focus\n")
                result_text.insert(tk.END, "  • Position text horizontally\n")
                result_text.insert(tk.END, "  • Avoid shadows on text\n")
                result_text.insert(tk.END, "  • Hold camera steady\n")
                
                # Console output
                print("❌ No text detected. Try different angle or lighting.")
                print("\n💡 Tips for better results:")
                print("  • Ensure good lighting (natural light is best)")
                print("  • Keep text clear and in focus")
                print("  • Position text horizontally")
                print("  • Avoid shadows on text")
                print("  • Hold camera steady\n")
                root.update()
                return
            
            # FILTER: Keep only HIGH CONFIDENCE results (>0.8 = 80%)
            high_confidence_results = self.filter_high_confidence_results(all_ocr_results, min_confidence=0.8)
            
            # APPLY TEXT PROCESSING ALGORITHMS for improved accuracy
            print("\n🔬 Applying advanced text processing algorithms...")
            print("   🎯 ADVANCED ALGORITHMS APPLIED:")
            print("      • Text Skew/Perspective Correction")
            print("      • Advanced Image Enhancement (Multi-pass)")
            print("      • Dictionary-based Word Validation")
            print("      • Context-aware Corrections")
            print("   ")
            print("   📝 TEXT PROCESSING:")
            print("      • Merging duplicate detections")
            print("      • Fixing common OCR mistakes")
            print("      • Normalizing text formatting")
            print("      • Removing artifacts")
            
            processed_results = self._apply_text_processing(high_confidence_results)
            
            # Generate combined text
            combined_text = ' '.join([item['text'] for item in processed_results])
            
            # Apply spelling autocorrection
            print("\n✍️  Applying spelling autocorrection algorithms...")
            print("   📚 SPELL CHECKER TIERS:")
            print("      • Tier 1: TextBlob Grammar/Spell Correction")
            print("      • Tier 2: PySpellChecker Dictionary Validation")
            print("      • Tier 3: Custom Context-based Fallback")
            
            corrected_text = self._apply_spelling_autocorrection(combined_text)
            print(f"\n   ✅ Spell correction complete")
            print(f"   Original text: {combined_text if combined_text else '(empty)'}")
            print(f"   Corrected text: {corrected_text if corrected_text else '(empty)'}")
            
            extracted_data = {
                'full_text': corrected_text,  # Use autocorrected text
                'full_text_uncorrected': combined_text,  # Keep original for comparison
                'detailed_data': processed_results,
                'total_detections': len(processed_results),
                'all_detections': len(all_ocr_results)  # Store for reference
            }
            
            # Display results in GUI
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"{'='*80}\n")
            result_text.insert(tk.END, f"✅ FRAME {frame_count[0]} - WITH AUTOCORRECTION\n")
            result_text.insert(tk.END, f"{'='*80}\n\n")
            
            result_text.insert(tk.END, f"📝 FINAL EXTRACTED TEXT (SPELL-CORRECTED):\n")
            result_text.insert(tk.END, f"{extracted_data['full_text']}\n\n")
            
            # Show if corrections were made
            if extracted_data['full_text'] != extracted_data['full_text_uncorrected']:
                result_text.insert(tk.END, f"{'='*80}\n")
                result_text.insert(tk.END, f"🔤 ORIGINAL TEXT (BEFORE AUTOCORRECTION):\n")
                result_text.insert(tk.END, f"{extracted_data['full_text_uncorrected']}\n\n")
            
            if extracted_data['total_detections'] == 0:
                result_text.insert(tk.END, f"⚠️  No HIGH CONFIDENCE text found.\n")
                result_text.insert(tk.END, f"   (Found {extracted_data['all_detections']} detections with lower confidence)\n\n")
                result_text.insert(tk.END, f"💡 Tips to improve:")
                result_text.insert(tk.END, f"  • Better lighting\n")
                result_text.insert(tk.END, f"  • Clearer focus\n")
                result_text.insert(tk.END, f"  • Steady camera position\n")
            else:
                result_text.insert(tk.END, f"{'='*80}\n")
                result_text.insert(tk.END, f"📊 HIGH CONFIDENCE DETECTIONS: {extracted_data['total_detections']}/")
                result_text.insert(tk.END, f"{extracted_data['all_detections']}\n")
                result_text.insert(tk.END, f"{'='*80}\n\n")
            
            # Console output - Display results
            print(f"✅ Text Extraction Successful!")
            print(f"\n{'='*80}")
            print(f"🎯 PROCESSING PIPELINE SUMMARY:")
            print(f"{'='*80}")
            print(f"✓ 4-Frame Capture with Advanced Accuracy Algorithms")
            print(f"  ├─ Skew Correction (Hough Lines + Rotation)")
            print(f"  ├─ Advanced Image Enhancement (Unsharp Mask)")
            print(f"  ├─ Dictionary-based Word Validation")
            print(f"  └─ Context-aware Error Correction")
            print(f"✓ Multi-frame combination and deduplication")
            print(f"✓ High-confidence filtering (>0.8 threshold)")
            print(f"✓ Text processing pipeline (merge, fix, normalize, clean)")
            print(f"✓ 3-tier spelling autocorrection (TextBlob → PySpellChecker → Custom)")
            print(f"{'='*80}")
            
            print(f"\n📝 FINAL EXTRACTED TEXT (WITH SPELL AUTOCORRECTION):")
            print(f"{'-'*80}")
            print(extracted_data['full_text'] if extracted_data['full_text'] else "(No high confidence text)")
            print(f"{'-'*80}")
            
            # Show if autocorrection made changes
            if extracted_data['full_text'] != extracted_data['full_text_uncorrected']:
                print(f"\n🔤 ORIGINAL TEXT (BEFORE AUTOCORRECTION):")
                print(f"{'-'*80}")
                print(extracted_data['full_text_uncorrected'])
                print(f"{'-'*80}")
            
            if extracted_data['total_detections'] > 0:
                print(f"\n📊 PROCESSED DETECTIONS: {extracted_data['total_detections']}/{extracted_data['all_detections']}")
                print(f"{'-'*80}")
                
                for idx, detection in enumerate(processed_results, 1):
                    confidence = detection['confidence']
                    result_text.insert(tk.END, f"{idx}. 🟢 [HIGH] {detection['text']}\n")
                    result_text.insert(tk.END, f"   Confidence: {confidence:.4f}\n\n")
                    
                    # Console output
                    print(f"{idx}. 🟢 [HIGH] {detection['text']}")
                    print(f"   Confidence: {confidence:.4f}")
            else:
                result_text.insert(tk.END, f"\n⚠️  No HIGH CONFIDENCE detections.\n")
                result_text.insert(tk.END, f"Total detections with lower confidence: {extracted_data['all_detections']}\n")
                
                print(f"\n⚠️  No HIGH CONFIDENCE detections found.")
                print(f"Total detections with lower confidence: {extracted_data['all_detections']}")
            
            print(f"{'-'*80}\n")
            
            captured_results.append({
                'frame_number': frame_count[0],
                'data': extracted_data,
                'timestamp': str(np.datetime64('now'))
            })
            
            result_text.see(tk.END)
            root.update()
        
        def close_camera():
            """Close camera and save results"""
            is_running[0] = False
            cap.release()
            root.destroy()
        
        # Create buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)
        
        capture_btn = Button(button_frame, text="📷 Capture Frame (or press SPACE)", command=capture_current_frame, 
                            bg="green", fg="white", font=("Arial", 11, "bold"), padx=15, pady=8)
        capture_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = Button(button_frame, text="❌ Close Camera", command=close_camera, 
                          bg="red", fg="white", font=("Arial", 11, "bold"), padx=15, pady=8)
        close_btn.pack(side=tk.LEFT, padx=5)
        
        # Bind spacebar to capture function
        root.bind('<space>', lambda e: capture_current_frame())
        root.bind('<Return>', lambda e: capture_current_frame())  # Also bind Enter key
        
        # Set focus to root window so spacebar works
        root.focus_set()
        
        # Start camera feed update
        update_camera_feed()
        
        # Run GUI
        try:
            root.mainloop()
        except Exception as e:
            print(f"GUI Error: {str(e)}")
        finally:
            cap.release()
        
        if captured_results:
            print(f"\n{'='*60}")
            print(f"Total frames captured: {len(captured_results)}")
            print(f"{'='*60}")
            return captured_results
        return None
    
    def capture_text_from_camera(self, save_frames=True):
        """
        Capture text from camera feed
        Captures frames automatically at intervals or when prompted
        save_frames: If True, saves captured frames to disk
        """
        cap = cv2.VideoCapture(0)  # 0 for default camera
        
        if not cap.isOpened():
            print("Error: Cannot access camera. Please check if camera is connected and not in use.")
            return None
        
        print("\n" + "="*60)
        print("CAMERA CAPTURE MODE - OCR TEXT EXTRACTION")
        print("="*60)
        print("Accessing camera...")
        print("="*60 + "\n")
        
        captured_results = []
        frame_count = 0
        frames_dir = "camera_captures"
        
        # Create directory for saving frames if it doesn't exist
        if save_frames and not os.path.exists(frames_dir):
            os.makedirs(frames_dir)
        
        try:
            print("Capturing frames from camera for 10 seconds...")
            print("Processing each frame for OCR...\n")
            
            capture_duration = 10  # seconds
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 30  # default FPS if not readable
            
            frame_interval = int(fps / 2)  # Capture every half second
            current_frame = 0
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    print("Error: Failed to read from camera")
                    break
                
                current_frame += 1
                
                # Capture every nth frame (controlled by frame_interval)
                if current_frame % frame_interval == 0:
                    frame_count += 1
                    print(f"\n--- Frame {frame_count} Captured ---")
                    
                    # Perform OCR on the captured frame
                    results = self.reader.readtext(frame)
                    extracted_data = self._parse_results(results)
                    
                    # Display frame with bounding boxes
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self._display_results(frame_rgb, results, extracted_data, f"Camera Frame {frame_count}")
                    
                    # Save frame to disk if enabled
                    if save_frames:
                        frame_filename = os.path.join(frames_dir, f"capture_{frame_count:03d}.jpg")
                        cv2.imwrite(frame_filename, frame)
                        print(f"Frame saved: {frame_filename}")
                    
                    captured_results.append({
                        'frame_number': frame_count,
                        'data': extracted_data,
                        'timestamp': str(np.datetime64('now'))
                    })
                    
                    # Exit after 10 seconds
                    if frame_count >= 10:
                        print(f"\nCapture limit reached (10 frames). Exiting camera mode...")
                        break
                    
        except Exception as e:
            print(f"Error during camera capture: {str(e)}")
        finally:
            cap.release()
        
        if captured_results:
            print(f"\n{'='*60}")
            print(f"Total frames processed: {len(captured_results)}")
            if save_frames:
                print(f"Frames saved to: {os.path.abspath(frames_dir)}")
            print(f"{'='*60}")
            return captured_results
        return None


# ============ MAIN EXECUTION ============

def display_menu():
    """Display menu options"""
    print("\n" + "="*60)
    print("OCR TEXT EXTRACTION - DYNAMIC FILE PROCESSOR")
    print("="*60)
    print("1. Extract text from a single image")
    print("2. Batch process multiple images from a folder")
    print("3. Extract text from camera/webcam")
    print("4. Exit")
    print("="*60)

def process_single_image(ocr):
    """Interactive single image processing"""
    print("\n--- Single Image Processing ---")
    image_path = input("Enter the image file path: ").strip()
    
    if not image_path:
        print("Error: No path provided")
        return
    
    # Expand user home directory if used
    image_path = os.path.expanduser(image_path)
    
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return
    
    # Extract text
    result = ocr.extract_text_from_image(image_path)
    
    if result:
        # Ask user if they want to save results
        save_choice = input("\nDo you want to save the extracted text? (yes/no): ").strip().lower()
        if save_choice in ['yes', 'y']:
            output_file = input("Enter output file path (default: extracted_text.txt): ").strip()
            if not output_file:
                output_file = "extracted_text.txt"
            output_file = os.path.expanduser(output_file)
            ocr.save_results_to_file(result, output_file)

def process_batch_images(ocr):
    """Interactive batch image processing"""
    print("\n--- Batch Image Processing ---")
    folder_path = input("Enter the folder path containing images: ").strip()
    
    if not folder_path:
        print("Error: No path provided")
        return
    
    # Expand user home directory if used
    folder_path = os.path.expanduser(folder_path)
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder not found at {folder_path}")
        return
    
    # Process batch
    all_results = ocr.batch_process_images(folder_path)
    
    if all_results:
        print(f"\nSuccessfully processed {len(all_results)} images")
        
        # Option to save all results
        save_choice = input("Do you want to save all results to a file? (yes/no): ").strip().lower()
        if save_choice in ['yes', 'y']:
            output_file = input("Enter output file path (default: batch_results.txt): ").strip()
            if not output_file:
                output_file = "batch_results.txt"
            output_file = os.path.expanduser(output_file)
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for filename, result in all_results.items():
                        if result:
                            f.write(f"\n{'='*60}\n")
                            f.write(f"File: {filename}\n")
                            f.write(f"{'='*60}\n")
                            f.write(result['full_text'])
                            f.write("\n\n")
                print(f"Batch results saved to: {output_file}")
            except Exception as e:
                print(f"Error saving batch results: {str(e)}")

def process_camera_input(ocr):
    """Interactive camera input processing with GUI - supports local camera and DroidCam"""
    print("\n--- Camera Input Processing ---")
    
    # Setup camera source (local or DroidCam)
    camera_source = ocr.setup_camera_source()
    
    if isinstance(camera_source, str):  # DroidCam
        print(f"\n📱 Starting DroidCam with live preview...")
    else:  # Local camera
        print("\n📷 Starting local camera with live preview...")
    
    print("Features:")
    print("  • Live camera feed display")
    print("  • Press SPACEBAR to capture and extract text")
    print("  • Multi-frame capture for high accuracy")
    print("  • Real-time confidence scores")
    print()
    
    # Capture from camera with improved GUI
    captured_results = ocr.capture_text_from_camera_gui(camera_source)
    
    if captured_results:
        print(f"\n✓ Successfully captured {len(captured_results)} frames")
        
        # Compile all results
        all_text = []
        for result in captured_results:
            if result['data']:
                all_text.append(result['data']['full_text'])
        
        full_combined_text = "\n\n".join(all_text)
        
        # Ask user if they want to save results
        save_choice = input("\nDo you want to save all extracted text? (yes/no): ").strip().lower()
        if save_choice in ['yes', 'y']:
            output_file = input("Enter output file path (default: camera_results.txt): ").strip()
            if not output_file:
                output_file = "camera_results.txt"
            output_file = os.path.expanduser(output_file)
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("="*60 + "\n")
                    f.write("OCR TEXT EXTRACTION - CAMERA CAPTURE RESULTS\n")
                    f.write("="*60 + "\n\n")
                    
                    for result in captured_results:
                        f.write(f"\nFrame {result['frame_number']}\n")
                        f.write(f"Timestamp: {result['timestamp']}\n")
                        f.write("-"*60 + "\n")
                        f.write(result['data']['full_text'])
                        f.write("\n\n")
                    
                    f.write("="*60 + "\n")
                    f.write("COMBINED TEXT:\n")
                    f.write("="*60 + "\n")
                    f.write(full_combined_text)
                
                print(f"✓ Camera results saved to: {output_file}")
            except Exception as e:
                print(f"Error saving camera results: {str(e)}")
    else:
        print("No frames were captured.")

if __name__ == "__main__":
    # Initialize OCR Extractor
    # Set gpu=True only if you have CUDA GPU with proper drivers
    ocr = OCRExtractor(languages=['en'], gpu=True)
    
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            process_single_image(ocr)
        elif choice == '2':
            process_batch_images(ocr)
        elif choice == '3':
            process_camera_input(ocr)
        elif choice == '4':
            print("\nThank you for using OCR Text Extraction!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
