import matplotlib.pyplot as plt
import cv2
import numpy as np
from focus_stack.utils import img_8bit, img_bw_8bit, save_plot
from focus_stack.exceptions import AlignmentError, InvalidOptionError
from focus_stack.utils import get_img_metadata, validate_image
import logging

ALIGN_HOMOGRAPHY = "ALIGN_HOMOGRAPHY"
ALIGN_RIGID = "ALIGN_RIGID"
BORDER_CONSTANT = "BORDER_CONSTANT"
BORDER_REPLICATE = "BORDER_REPLICATE"
BORDER_REPLICATE_BLUR = "BORDER_REPLICATE_BLUR"


class AlignFrames:
    def __init__(self, detector='SIFT', descriptor='SIFT', match_method='KNN', flann_idx_kdtree=2,
                 flann_trees=5, flann_checks=50, match_threshold=0.75, transform=ALIGN_RIGID,
                 rans_threshold=5.0, border_mode=BORDER_REPLICATE_BLUR, border_value=(0, 0, 0, 0),
                 border_blur=50, plot_matches=False):
        self.detector = detector
        self.descriptor = descriptor
        self.match_method = match_method
        self.flann_idx_kdtree = flann_idx_kdtree
        self.flann_trees = flann_trees
        self.flann_checks = flann_checks
        self.match_threshold = match_threshold
        self.transform = transform
        self.min_matches = 4 if self.transform == ALIGN_HOMOGRAPHY else 3
        self.rans_threshold = rans_threshold
        self.border_mode = border_mode
        if border_mode == BORDER_CONSTANT:
            self.cv2_border_mode = cv2.BORDER_CONSTANT
        elif border_mode == BORDER_REPLICATE:
            self.cv2_border_mode = cv2.BORDER_REPLICATE
        elif border_mode == BORDER_REPLICATE_BLUR:
            self.cv2_border_mode = cv2.BORDER_REPLICATE
        else:
            raise InvalidOptionError("border_mode", border_mode)
        self.border_blur = border_blur
        self.border_value = border_value
        self.plot_matches = plot_matches

    def detect_and_compute(self, img_0, img_1):
        img_bw_0, img_bw_1 = img_bw_8bit(img_0), img_bw_8bit(img_1)
        detector = None
        if self.detector == 'SIFT':
            detector = cv2.SIFT_create()
        elif self.detector == 'ORB':
            detector = cv2.ORB_create()
        elif self.detector == 'SURF':
            detector = cv2.FastFeatureDetector_create()
        elif self.detector == 'AKAZE':
            detector = cv2.AKAZE_create()
        else:
            raise InvalidOptionError("detector" + self.detector)
        descriptor = None
        if self.descriptor == 'ORB':
            descriptor = cv2.SIFT_create()
        elif self.descriptor == 'SIFT':
            descriptor = cv2.ORB_create()
        elif self.descriptor == 'AKAZE':
            descriptor = cv2.AKAZE_create()
        else:
            raise InvalidOptionError("descriptor", self.descriptor)
        if self.detector == self.descriptor and (self.detector == 'SIFT' or self.detector == 'AKAZE'):
            kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
            kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
        else:
            kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
            kp_1, des_1 = descriptor.compute(img_bw_1, detector.detect(img_bw_1, None))
        good_matches = self.get_good_matches(des_0, des_1)
        return kp_0, kp_1, good_matches

    def get_good_matches(self, des_0, des_1):
        if self.match_method == 'KNN':
            flann = cv2.FlannBasedMatcher(dict(algorithm=self.flann_idx_kdtree, 
                                               trees=self.flann_trees), dict(checks=self.flann_checks))
            matches = flann.knnMatch(des_0, des_1, k=2)
            good_matches = []
            for m, n in matches:
                if m.distance < self.match_threshold * n.distance:
                    good_matches.append(m)
        elif self.match_method == 'NORM_HAMMING':
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            good_matches = bf.match(des_0, des_1)
            good_matches = sorted(good_matches, key=lambda x: x.distance)
        return good_matches

    def find_transform(self, src_pts, dst_pts):
        if self.transform == ALIGN_HOMOGRAPHY:
            M, msk = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.rans_threshold)
        elif self.transform == ALIGN_RIGID:
            M, msk = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC,
                                                 ransacReprojThreshold=self.rans_threshold)
        else:
            raise InvalidOptionError("transform", self.transform)
        return M, msk

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.process.img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def align_images(self, idx, img_1, img_0):
        metadata = get_img_metadata(img_1)
        validate_image(img_0, *metadata)
        self.process.sub_message_r(': find matches')
        kp_0, kp_1, good_matches = self.detect_and_compute(img_0, img_1)
        n_good_matches = len(good_matches)
        self.n_matches[idx] = n_good_matches
        self.process.sub_message_r(": matches: {}".format(n_good_matches))
        if n_good_matches >= self.min_matches:
            src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, msk = self.find_transform(src_pts, dst_pts)
            h, w = img_0.shape[:2]
            # may be useful for future applications
            # pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1 ,2)
            self.process.sub_message_r(': align images')
            if self.transform == ALIGN_HOMOGRAPHY:
                # may be useful for future applications
                # dst = cv2.perspectiveTransform(pts, M)
                img_warp = cv2.warpPerspective(img_0, M, (w, h),
                                               borderMode=self.cv2_border_mode,
                                               borderValue=self.border_value)
                if self.border_mode == BORDER_REPLICATE_BLUR:
                    mask = cv2.warpPerspective(np.ones_like(img_0, dtype=np.uint8),
                                               M, (w, h), borderMode=cv2.BORDER_CONSTANT,
                                               borderValue=0)
            elif self.transform == ALIGN_RIGID:
                # may be useful for future applications
                # dst = cv2.transform(pts, M)
                img_warp = cv2.warpAffine(img_0, M, (img_0.shape[1], img_0.shape[0]),
                                          borderMode=self.cv2_border_mode,
                                          borderValue=self.border_value)
                if self.border_mode == BORDER_REPLICATE_BLUR:
                    mask = cv2.warpAffine(np.ones_like(img_0, dtype=np.uint8), M, (w, h),
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            if self.border_mode == BORDER_REPLICATE_BLUR:
                self.process.sub_message_r(': blur borders')
                mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
                blurred_warp = cv2.GaussianBlur(img_warp, (21, 21), sigmaX=self.border_blur)
                img_warp[mask == 0] = blurred_warp[mask == 0]
            if self.plot_matches:
                matches_mask = msk.ravel().tolist()
                draw_params = dict(matchColor=(0, 255, 0), singlePointColor=None,
                                   matchesMask=matches_mask, flags=2)
                img_match = cv2.cvtColor(cv2.drawMatches(img_0, kp_0, img_1, kp_1, good_matches,
                                                         None, **draw_params), cv2.COLOR_BGR2RGB)
                try:
                    __IPYTHON__  # noqa
                    plt.figure(figsize=(10, 5))
                    plt.imshow(img_match, 'gray')
                    plt.savefig(self.process.plot_path + "/" + self.process.name +
                                "-matches-{:04d}.pdf".format(idx))
                except Exception:
                    pass
            return img_warp
        else:
            self.process.sub_message(": image not aligned, too few matches found: {}".format(n_good_matches), level=logging.CRITICAL)
            raise AlignmentError(idx, f"too few matches found: {n_good_matches} < {self.min_matches}")
            return None

    def begin(self, process):
        self.process = process
        self.n_matches = np.zeros(process.counts)

    def end(self):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.n_matches) + 1, dtype=int)
        no_ref = (x != self.process.ref_idx + 1)
        x = x[no_ref]
        y = self.n_matches[no_ref]
        if self.process.ref_idx == 0:
            y_max = y[1]
        elif self.process.ref_idx == len(y) - 1:
            y_max = y[-1]
        else:
            y_max = (y[self.process.ref_idx - 1] + y[self.process.ref_idx]) / 2
        plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1], [0, y_max],
                 color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray',
                 linestyle='--', label='min. matches')
        plt.plot(x, y, color='navy', label='matches')
        plt.xlabel('frame')
        plt.ylabel('# of matches')
        plt.legend()
        plt.ylim(0)
        plt.xlim(x[0], x[-1])
        save_plot(self.process.plot_path + "/" + self.process.name + "-matches.pdf")
