import os
import cv2
from paddleocr import PaddleOCR

def test_ocr():
    sample_path = r"C:\Users\jaque\OneDrive\Documents\Desktop\6th sem\krid\backend\sample-card.jpg"
    if not os.path.exists(sample_path):
        sample_path = r"C:\Users\jaque\.gemini\antigravity\brain\f3a60f2c-6ed9-4922-9589-dbf75df327e3\sample_business_card_1782851745329.jpg"
        
    print(f"Loading image from: {sample_path}")
    img = cv2.imread(sample_path)
    if img is None:
        print("Error: Unable to load image.")
        return
        
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    
    print("Running text detection...")
    result = ocr.ocr(img, cls=True)
    
    print("=== Detected Text ===")
    if result and result[0]:
        for line in result[0]:
            print(f"Text: {line[1][0]} | Conf: {line[1][1]:.2f}")
    else:
        print("No text detected.")

if __name__ == "__main__":
    test_ocr()
