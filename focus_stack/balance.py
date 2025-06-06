import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from scipy.interpolate import interp1d
from focus_stack.utils import read_img, save_plot
from focus_stack.exceptions import InvalidOptionError

BALANCE_LINEAR = "LINEAR"
BALANCE_GAMMA = "GAMMA"
BALANCE_MATCH_HIST = "MATCH_HIST"
BALANCE_LUMI = "LUMI"
BALANCE_RGB = "RGB"
BALANCE_HSV = "HSV"
BALANCE_HLS = "HLS"

_DEFAULT_IMG_SCALE = 8
_DEFAULT_CORR_MAP = BALANCE_LINEAR
_DEFAULT_CHANNEL = BALANCE_LUMI
_DEFAULT_INTENSITY_INTERVAL = {
    'min': 0,
    'max': -1
}


class CorrectionMapBase:
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        intensity_interval = {**_DEFAULT_INTENSITY_INTERVAL, **(intensity_interval or {})}
        self.dtype = dtype
        self.two_n = 256 if dtype == np.uint8 else 65536
        self.two_n_1 = self.two_n - 1
        self.id_lut = np.array(list(range(self.two_n)))
        i_min, i_max = intensity_interval['min'], intensity_interval['max']
        self.i_min = i_min
        self.i_end = i_max + 1 if i_max >= 0 else self.two_n
        self.channels = len(ref_hist)
        self.reference = None

    def lut(self, correction, reference):
        assert False, 'abstract method'

    def apply_lut(self, correction, reference, img):
        lut = self.lut(correction, reference)
        return cv2.LUT(img, lut) if self.dtype == np.uint8 else np.take(lut, img)

    def adjust(self, image, correction):
        if self.channels == 1:
            return self.apply_lut(correction[0], self.reference[0], image)
        else:
            chans = cv2.split(image)
            if self.channels == 2:
                ch_out = [chans[0]] + [self.apply_lut(correction[c - 1], self.reference[c - 1], chans[c]) for c in range(1, 3)]
            elif self.channels == 3:
                ch_out = [self.apply_lut(correction[c], self.reference[c], chans[c]) for c in range(3)]
            return cv2.merge(ch_out)

    def correction_size(self, correction):
        return correction


class MatchHist(CorrectionMapBase):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMapBase.__init__(self, dtype, ref_hist, intensity_interval)
        self.reference = self.cumsum(ref_hist)
        self.reference_mean = [r.mean() for r in self.reference]
        self.values = [*range(self.two_n)]

    def cumsum(self, hist):
        return [np.cumsum(h) / h.sum() * self.two_n_1 for h in hist]

    def lut(self, correction, reference):
        interp = interp1d(reference, self.values)
        lut = np.array([interp(v) for v in np.clip(correction, reference.min(), reference.max())])
        l0, l1 = lut[0], lut[-1]
        ll = lut[(lut != l0) & (lut != l1)]
        if ll.size > 0:
            l_min, l_max = ll.min(), ll.max()
            i0, i1 = self.id_lut[lut == l0], self.id_lut[lut == l1]
            i0_max = i0.max()
            lut[lut == l0] = (i0 / i0_max * l_min) if i0_max > 0 else 0
            lut[lut == l1] = i1 + (i1 - self.two_n_1) * (self.two_n_1 - l_max) / float(i1.size) if i1.size > 0 else self.two_n_1
        return lut.astype(self.dtype)

    def correction(self, hist):
        return self.cumsum(hist)

    def correction_size(self, correction):
        return [c.mean() / m for c, m in zip(correction, self.reference_mean)]


class CorrectionMap(CorrectionMapBase):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMapBase.__init__(self, dtype, ref_hist, intensity_interval)
        self.reference = [self.mid_val(self.id_lut, h) for h in ref_hist]

    def mid_val(self, lut, h):
        return np.average(lut[self.i_min:self.i_end], weights=h.flatten()[self.i_min:self.i_end])


class GammaMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMap.__init__(self, dtype, ref_hist, intensity_interval)

    def correction(self, hist):
        return [bisect(lambda x: self.mid_val(self.lut(x), h) - r, 0.1, 5) for h, r in zip(hist, self.reference)]

    def lut(self, correction, reference=None):
        gamma_inv = 1.0 / correction
        return (((np.arange(0, self.two_n) / self.two_n_1) ** gamma_inv) * self.two_n_1).astype(self.dtype)


class LinearMap(CorrectionMap):
    def __init__(self, dtype, ref_hist, intensity_interval=None):
        CorrectionMap.__init__(self, dtype, ref_hist, intensity_interval)

    def lut(self, correction, reference=None):
        return np.clip(np.arange(0, self.two_n) * correction, 0, self.two_n_1).astype(self.dtype)

    def correction(self, hist):
        return [r / self.mid_val(self.id_lut, h) for h, r in zip(hist, self.reference)]


class Correction:
    def __init__(self, channels, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        self.mask_size = mask_size
        self.intensity_interval = intensity_interval
        self.plot_histograms = plot_histograms
        self.img_scale = _DEFAULT_IMG_SCALE if img_scale == -1 else img_scale
        self.corr_map = corr_map
        self.channels = channels

    def begin(self, ref_image, size, ref_idx):
        self.dtype = ref_image.dtype
        self.two_n = 256 if ref_image.dtype == np.uint8 else 65536
        hist = self.get_hist(self.preprocess(ref_image), ref_idx)
        if self.corr_map == BALANCE_LINEAR:
            self.corr_map = LinearMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == BALANCE_GAMMA:
            self.corr_map = GammaMap(self.dtype, hist, self.intensity_interval)
        elif self.corr_map == BALANCE_MATCH_HIST:
            self.corr_map = MatchHist(self.dtype, hist, self.intensity_interval)
        else:
            raise InvalidOptionError("corr_map", self.corr_map)
        self.corrections = np.ones((size, self.channels))

    def calc_hist_1ch(self, image):
        if self.mask_size is None:
            image_sel = image
        else:
            height, width = image.shape[:2]
            xv, yv = np.meshgrid(np.linspace(0, width - 1, width), np.linspace(0, height - 1, height))
            image_sel = image[(xv - width / 2) ** 2 + (yv - height / 2) ** 2 <= (min(width, height) * self.mask_size / 2) ** 2]
        hist, bins = np.histogram((image_sel if self.img_scale == 1
                                   else image_sel[::self.img_scale][::self.img_scale]),
                                  bins=np.linspace(-0.5, self.two_n - 0.5, self.two_n + 1))
        return hist

    def balance(self, image, idx):
        correction = self.corr_map.correction(self.get_hist(image, idx))
        return correction, self.corr_map.adjust(image, correction)

    def get_hist(self, image, idx):
        assert False, 'abstract method'

    def end(self):
        assert False, 'abstract method'

    def apply_correction(self, idx, image):
        image = self.preprocess(image)
        correction, image = self.balance(image, idx)
        image = self.postprocess(image)
        self.corrections[idx] = self.corr_map.correction_size(correction)
        return image

    def preprocess(self, image):
        return image

    def postprocess(self, image):
        return image

    def histo_plot(self, ax, hist, x_label, color, alpha=1):
        ax.set_ylabel("# of pixels")
        ax.set_xlabel(x_label)
        ax.set_xlim([0, self.two_n])
        ax.set_yscale('log')
        ax.plot(hist, color=color, alpha=alpha)


class LumiCorrection(Correction):
    def __init__(self, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        Correction.__init__(self, 1, mask_size, intensity_interval, img_scale, corr_map, plot_histograms)

    def get_hist(self, image, idx):
        hist = self.calc_hist_1ch(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        fig, axs = plt.subplots(1, 2, figsize=(10, 3), sharey=True)
        self.histo_plot(axs[0], hist, "pixel luminosity", 'black')
        for (chan, color) in zip(chans, colors):
            hist_col = self.calc_hist_1ch(chan)
            self.histo_plot(axs[1], hist_col, "r,g,b luminosity", color, alpha=0.5)
        plt.xlim(0, self.two_n)
        save_plot(self.process.plot_path + "/" + self.process.name + "-hist-{:04d}.pdf".format(idx),
                  show=self.plot_histograms)
        return [hist]

    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y, color='navy', label='luminosity correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        save_plot(self.process.plot_path + "/" + self.process.name + "-balance.pdf")


class RGBCorrection(Correction):
    def __init__(self, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        Correction.__init__(self, 3, mask_size, intensity_interval, img_scale, corr_map, plot_histograms)

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        colors = ("r", "g", "b")
        fig, axs = plt.subplots(1, 3, figsize=(10, 3), sharey=True)
        for c in [2, 1, 0]:
            self.histo_plot(axs[c], hist[c], colors[c] + " luminosity", colors[c])
        plt.xlim(0, self.two_n)
        save_plot(self.process.plot_path + "/" + self.process.name + "-hist-{:04d}.pdf".format(idx),
                  show=self.plot_histograms)
        return hist

    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color='r', label='R correction')
        plt.plot(x, y[:, 1], color='g', label='G correction')
        plt.plot(x, y[:, 2], color='b', label='B correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        save_plot(self.process.plot_path + "/" + self.process.name + "-balance.pdf")


class Ch2Correction(Correction):
    def __init__(self, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        Correction.__init__(self, 2, mask_size, intensity_interval, img_scale, corr_map, plot_histograms)

    def preprocess(self, image):
        assert False, 'abstract method'

    def get_labels(self):
        assert False, 'abstract method'

    def get_hist(self, image, idx):
        hist = [self.calc_hist_1ch(chan) for chan in cv2.split(image)]
        fig, axs = plt.subplots(1, 3, figsize=(10, 3), sharey=True)
        for c in range(3):
            self.histo_plot(axs[c], hist[c], self.labels[c], self.colors[c])
        plt.xlim(0, self.two_n)
        save_plot(self.process.plot_path + "/" + self.process.name + "_hist_{:04d}.pdf".format(idx),
                  show=self.plot_histograms)
        return hist[1:]

    def end(self, ref_idx):
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.corrections) + 1, dtype=int)
        y = self.corrections
        plt.plot([ref_idx + 1, ref_idx + 1], [0, 1], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [1, 1], color='lightgray', linestyle='--', label='no correction')
        plt.plot(x, y[:, 0], color=self.colors[1], label=self.labels[1] + ' correction')
        plt.plot(x, y[:, 1], color=self.colors[2], label=self.labels[2] + ' correction')
        plt.xlabel('frame')
        plt.ylabel('correction')
        plt.legend()
        plt.xlim(x[0], x[-1])
        plt.ylim(0)
        save_plot(self.process.plot_path + "/" + self.process.name + "-balance.pdf")


class SVCorrection(Ch2Correction):
    def __init__(self, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        Ch2Correction.__init__(self, mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        self.labels = ("H", "S", "V")
        self.colors = ("hotpink", "orange", "navy")

    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)


class LSCorrection(Ch2Correction):
    def __init__(self, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        Ch2Correction.__init__(self, mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        self.labels = ("H", "L", "S")
        self.colors = ("hotpink", "navy", "orange")

    def preprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2HLS)

    def postprocess(self, image):
        return cv2.cvtColor(image, cv2.COLOR_HLS2BGR)


class BalanceFrames:
    def __init__(self, channel=_DEFAULT_CHANNEL, mask_size=None, intensity_interval=None, img_scale=-1, corr_map=_DEFAULT_CORR_MAP, plot_histograms=False):
        img_scale = (1 if corr_map == BALANCE_MATCH_HIST else _DEFAULT_IMG_SCALE) if img_scale == -1 else img_scale
        if channel == BALANCE_LUMI:
            self.correction = LumiCorrection(mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        elif channel == BALANCE_RGB:
            self.correction = RGBCorrection(mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        elif channel == BALANCE_HSV:
            self.correction = SVCorrection(mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        elif channel == BALANCE_HLS:
            self.correction = LSCorrection(mask_size, intensity_interval, img_scale, corr_map, plot_histograms)
        else:
            raise InvalidOptionError("channel", channel)

    def begin(self, process):
        self.process = process
        self.correction.process = process
        self.correction.begin(read_img(self.process.input_dir + "/" + self.process.filenames[process.ref_idx]),
                              self.process.counts, process.ref_idx)

    def end(self):
        self.process.print_message(' ' * 60)
        self.correction.end(self.process.ref_idx)

    def run_frame(self, idx, ref_idx, image):
        if idx != self.process.ref_idx:
            self.process.sub_message_r(': balance image')
            image = self.correction.apply_correction(idx, image)
        return image
