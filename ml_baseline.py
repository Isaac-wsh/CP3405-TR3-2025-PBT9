"""
SmartSeat AI/ML Baseline
========================
This is a simplest AI/ML baseline example.
Goal: Simulate a "seat detection" function, which will be replaced
with a real computer vision model later.
"""

import random
import time


def detect_seat(image_path: str) -> str:
    """
    Simulates a seat detection function.
    Input: Image path (no need to actually read the image here, just a placeholder)
    Output: 'occupied' or 'empty'
    """
    # Randomly return results, pretending we are running a model
    return random.choice(["occupied", "empty"])


if __name__ == "__main__":
    print("=== SmartSeat ML Baseline ===")

    # Simulate input of 10 seat images
    sample_images = [f"seat_{i}.jpg" for i in range(1, 11)]

    for img in sample_images:
        result = detect_seat(img)
        print(f"Image {img} -> Seat status: {result}")
        time.sleep(0.5)  # Add a little delay, more like the real reasoning process
