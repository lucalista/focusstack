import cv2
import numpy as np
import matplotlib.pyplot as plt
from focusstack.config.constants import constants
from focusstack.algorithms.align import align_images, detect_and_compute, find_transform
import random

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

def apply_random_transform(img, max_angle=10, max_translation=20):
    """Apply random transformation within specified bounds"""
    h, w = img.shape[:2]
    center = (w//2, h//2)
    
    # Random rotation (-max_angle to +max_angle)
    angle = random.uniform(-max_angle, max_angle)
    
    # Random translation (-max_translation to +max_translation)
    tx = random.uniform(-max_translation, max_translation)
    ty = random.uniform(-max_translation, max_translation)
    
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    M[0,2] += tx
    M[1,2] += ty
    
    return cv2.warpAffine(img, M, (w, h)), M, (angle, tx, ty)

def ensure_3channel(img):
    """Convert to 3-channel BGR if needed"""
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img

def run_single_test(color_test=False):
    """Run one test iteration using only align.py defaults"""
    # Create and transform image
    original = create_test_image(color=color_test)
    transformed, M_true, true_params = apply_random_transform(original)
    
    # Convert to 3-channel BGR
    original_bgr = ensure_3channel(original)
    transformed_bgr = ensure_3channel(transformed)
    
    try:
        # Run alignment with all DEFAULT parameters
        n_matches, aligned = align_images(
            transformed_bgr,
            original_bgr,
            alignment_config={'transform': constants.ALIGN_RIGID}
        )
        
        # Get keypoints and matches using DEFAULT detectors/descriptors
        kp_0, kp_1, good_matches = detect_and_compute(
            original_bgr, 
            aligned  # Compare original with aligned result
        )
        
        if len(good_matches) < 4:
            return None
            
        # Get points using DEFAULT method
        src_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)
        dst_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
        
        # Estimate transform using DEFAULT parameters
        M_recovered, _ = find_transform(
            src_pts, dst_pts,
            transform=constants.ALIGN_RIGID
        )
        
        if M_recovered is None:
            return None
            
        # Calculate recovered parameters
        angle_recovered = np.degrees(np.arctan2(M_recovered[1,0], M_recovered[0,0]))
        tx_recovered = M_recovered[0,2]
        ty_recovered = M_recovered[1,2]
        
        # Calculate errors
        angle_error = true_params[0] - angle_recovered
        tx_error = true_params[1] - tx_recovered
        ty_error = true_params[2] - ty_recovered
        
        return angle_error, tx_error, ty_error
        
    except Exception as e:
        print(f"Alignment failed: {e}")
        return None

def run_multiple_tests(N=100, color_test=False):
    """Run N tests and collect statistics"""
    angle_errors = []
    tx_errors = []
    ty_errors = []
    successes = 0
    
    for i in range(N):
        print(f"test {i+1}/{N}")
        result = run_single_test(color_test)
        if result is not None:
            angle_error, tx_error, ty_error = result
            angle_errors.append(angle_error)
            tx_errors.append(tx_error)
            ty_errors.append(ty_error)
            successes += 1
    
    print(f"\nCompleted {successes}/{N} successful tests")
    
    if successes == 0:
        return
    
    # Plot histograms
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.hist(angle_errors, bins=20, color='blue', alpha=0.7)
    plt.title('Rotation Error (degrees)')
    plt.xlabel('Error (degrees)')
    plt.ylabel('Count')
    
    plt.subplot(1, 3, 2)
    plt.hist(tx_errors, bins=20, color='green', alpha=0.7)
    plt.title('X Translation Error (pixels)')
    plt.xlabel('Error (pixels)')
    
    plt.subplot(1, 3, 3)
    plt.hist(ty_errors, bins=20, color='red', alpha=0.7)
    plt.title('Y Translation Error (pixels)')
    plt.xlabel('Error (pixels)')
    
    plt.tight_layout()
    plt.show()
    
    # Print statistics
    print(f"\nRotation Error Statistics:")
    print(f"  Mean: {np.mean(angle_errors):.3f}°")
    print(f"  Median: {np.median(angle_errors):.3f}°")
    print(f"  Std Dev: {np.std(angle_errors):.3f}°")
    print(f"  Max: {np.max(angle_errors):.3f}°")
    
    print(f"\nX Translation Error Statistics:")
    print(f"  Mean: {np.mean(tx_errors):.3f} px")
    print(f"  Median: {np.median(tx_errors):.3f} px")
    print(f"  Std Dev: {np.std(tx_errors):.3f} px")
    print(f"  Max: {np.max(tx_errors):.3f} px")
    
    print(f"\nY Translation Error Statistics:")
    print(f"  Mean: {np.mean(ty_errors):.3f} px")
    print(f"  Median: {np.median(ty_errors):.3f} px")
    print(f"  Std Dev: {np.std(ty_errors):.3f} px")
    print(f"  Max: {np.max(ty_errors):.3f} px")

if __name__ == "__main__":
    N_TESTS = 20
    
    print("=== TEST GRAYSCALE ===")
    run_multiple_tests(N=N_TESTS, color_test=False)
    
    print("\n=== TEST COLOR ===")
    run_multiple_tests(N=N_TESTS, color_test=True)