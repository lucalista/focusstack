import cv2
import numpy as np
import matplotlib.pyplot as plt
from focusstack.config.constants import constants
from focusstack.algorithms.align import align_images

def create_test_image(size=(512, 512), color=False):
    """Create test image, optionally color"""
    if color:
        img = np.zeros((*size, 3), dtype=np.uint8)
        white = (255, 255, 255)
    else:
        img = np.zeros(size, dtype=np.uint8)
        white = 255
    
    # Draw elements
    cv2.rectangle(img, (50, 50), (150, 150), white, 2)
    cv2.circle(img, (400, 150), 60, white, 2)
    cv2.line(img, (200, 400), (300, 300), white, 2)
    cv2.line(img, (200, 300), (300, 400), white, 2)
    
    # Add noise
    noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
    return cv2.add(img, noise)

def apply_transform(img, angle=15, tx=30, ty=20):
    """Apply transformation to any format"""
    h, w = img.shape[:2]
    center = (w//2, h//2)
    
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    M[0,2] += tx
    M[1,2] += ty
    
    return cv2.warpAffine(img, M, (w, h)), M

def ensure_3channel(img):
    """Convert to 3-channel BGR if needed"""
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 1:  # Single-channel color image
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img

def compare_transformations(M_true, M_aligned):
    """Compare two transformation matrices"""
    print("\nTrue transformation matrix:")
    print(M_true)
    print("\nRecovered transformation matrix:")
    print(M_aligned)
    
    # Convert to 3x3 homography matrices for better comparison
    M_true_hom = np.vstack([M_true, [0, 0, 1]])
    M_aligned_hom = np.vstack([M_aligned, [0, 0, 1]])
    
    # Calculate the difference in rotation angle
    angle_true = np.degrees(np.arctan2(M_true[1,0], M_true[0,0]))
    angle_aligned = np.degrees(np.arctan2(M_aligned[1,0], M_aligned[0,0]))
    angle_diff = abs(angle_true - angle_aligned)
    
    # Calculate translation difference
    tx_diff = abs(M_true[0,2] - M_aligned[0,2])
    ty_diff = abs(M_true[1,2] - M_aligned[1,2])
    
    print(f"\nRotation difference: {angle_diff:.2f} degrees")
    print(f"Translation X difference: {tx_diff:.2f} pixels")
    print(f"Translation Y difference: {ty_diff:.2f} pixels")
    
    # Calculate scale difference (should be ~1 for rigid transform)
    scale_true = np.sqrt(M_true[0,0]**2 + M_true[1,0]**2)
    scale_aligned = np.sqrt(M_aligned[0,0]**2 + M_aligned[1,0]**2)
    print(f"Scale difference: {abs(scale_true - scale_aligned):.4f}")

def test_alignment(color_test=False):
    # 1. Create image
    original = create_test_image(color=color_test)
    
    # 2. Apply transformation
    transformed, M_true = apply_transform(original)
    
    # 3. Convert to 3-channel BGR
    original_bgr = ensure_3channel(original)
    transformed_bgr = ensure_3channel(transformed)
    
    # 4. Alignment
    try:
        n_matches, M_recovered, aligned = align_images(
            transformed_bgr,
            original_bgr,
            alignment_config={'transform': constants.ALIGN_RIGID}
        )
    except Exception as e:
        print(f"Alignment failed: {e}")
        return

    # 6. Compare transformations
    compare_transformations(M_true, M_recovered)
    
    # 7. Visualization
    display_img = aligned.copy()
    if not color_test:
        display_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2GRAY)
    
    titles = ['Original', 'Transformed', 'Aligned']
    images = [original, transformed, display_img]
    
    plt.figure(figsize=(15,5))
    for i, (title, img) in enumerate(zip(titles, images)):
        plt.subplot(1,3,i+1)
        if len(img.shape) == 2:
            plt.imshow(img, cmap='gray')
        else:
            plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title(title)
    plt.show()

if __name__ == "__main__":
    print("=== TEST GRAYSCALE ===")
    test_alignment(color_test=False)
    
    print("\n=== TEST COLOR ===")
    test_alignment(color_test=True)