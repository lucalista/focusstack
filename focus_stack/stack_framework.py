from .framework import Job, ActionList, JobBase
from .utils import check_path_exists
from focus_stack.utils import read_img, write_img
from focus_stack.exceptions import ShapeError, BitDepthError
from termcolor import colored
import logging
import os


class StackJob(Job):
    def __init__(self, name, working_path, input_path=None, logger_name=None, log_file="logs/focusstack.log"):
        check_path_exists(working_path)
        self.working_path = working_path
        if input_path is None or input_path == '':
            self.paths = []
        else:
            self.paths = [input_path]
        Job.__init__(self, name, logger_name, log_file)

    def init(self, a):
        a.init(self)


class FramePaths(JobBase):
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

    def __init__(self, name, input_path=None, output_path=None, working_path=None, plot_path='plots', resample=1, reverse_order=False):
        JobBase.__init__(self, name)
        self.name = name
        self.working_path = working_path
        self.plot_path = plot_path
        self.input_path = input_path
        self.output_path = output_path
        self.resample = resample
        self.reverse_order = reverse_order

    def set_filelist(self):
        self.filenames = self.folder_filelist(self.input_dir)
        self.print_message(colored(": {} files ".format(len(self.filenames)) + "in folder: " + self.input_dir, 'blue'))
        self.print_message(colored("focus stacking", 'blue'))

    def init(self, job):
        if self.working_path is None:
            self.working_path = job.working_path
        check_path_exists(self.working_path)
        if self.output_path is None:
            self.output_path = self.name
        self.output_dir = self.working_path + ('' if self.working_path[-1] == '/' else '/') + self.output_path
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if self.plot_path is not None:
            self.plot_path = self.working_path + ('' if self.working_path[-1] == '/' else '/') + self.plot_path
            if not os.path.exists(self.plot_path):
                os.makedirs(self.plot_path)
        if self.input_path is None:
            assert len(job.paths) > 0, "No input path has been specified in " + job.name
            self.input_path = job.paths[-1]
        job.paths.append(self.output_path)


class FrameDirectory(FramePaths):
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

    def __init__(self, name, input_path=None, output_path=None, working_path=None, plot_path='plots', resample=1, reverse_order=False):
        FramePaths.__init__(self, name, input_path, output_path, working_path, plot_path, resample, reverse_order)

    def folder_filelist(self, path):
        src_contents = os.walk(self.input_dir)
        dirpath, _, filenames = next(src_contents)
        filelist = [name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
        filelist.sort()
        if self.reverse_order:
            filelist.reverse()
        if self.resample > 1:
            filelist = filelist[0::self.resample]
        return filelist

    def init(self, job):
        FramePaths.init(self, job)
        self.input_dir = self.working_path + ('' if self.working_path[-1] == '/' else '/') + self.input_path
        check_path_exists(self.input_dir)
        job.paths.append(self.output_path)


class FrameMultiDirectory:
    EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

    def __init__(self, name, input_path=None, output_path=None, working_path=None, plot_path='plots',
                 resample=1, reverse_order=False):
        FramePaths.__init__(self, name, input_path, output_path, working_path, plot_path, resample, reverse_order)

    def folder_list_str(self):
        if isinstance(self.input_dir, list):
            return "folder{}: ".format('s' if len(self.input_dir) > 1 else '') + ", ".join([i for i in self.input_dir])
        else:
            return "folder: " + self.input_dir

    def folder_filelist(self):
        if isinstance(self.input_dir, str):
            dirs = [self.input_dir]
            paths = [self.input_path]
        elif hasattr(self.input_dir, "__len__"):
            dirs = self.input_dir
            paths = self.input_path
        else:
            raise Exception("input_dir option must containa path or an array of paths")
        files = []
        for d, p in zip(dirs, paths):
            src_contents = os.walk(d)
            dirpath, _, filenames = next(src_contents)
            filelist = [p + "/" + name for name in filenames if os.path.splitext(name)[-1][1:].lower() in FrameDirectory.EXTENSIONS]
            if self.reverse_order:
                filelist.reverse()
            if self.resample > 1:
                filelist = filelist[0::self.resample]
            files += filelist
        return files

    def init(self, job):
        FramePaths.init(self, job)
        if isinstance(self.input_path, str):
            self.input_dir = self.working_path + ('' if self.working_path[-1] == '/' else '/') + self.input_path
            check_path_exists(self.input_dir)
        elif hasattr(self.input_path, "__len__"):
            self.input_dir = []
            for path in self.input_path:
                self.input_dir.append(self.working_path + ('' if self.working_path[-1] == '/' else '/') + path)
                check_path_exists(self.input_dir[-1])
        job.paths.append(self.output_path)


class FramesRefActions(FrameDirectory, ActionList):
    def __init__(self, name, input_path=None, output_path=None, working_path=None, plot_path='plots', resample=1, ref_idx=-1, step_process=False):
        FrameDirectory.__init__(self, name, input_path, output_path, working_path, plot_path, resample)
        ActionList.__init__(self, name)
        self.ref_idx = ref_idx
        self.step_process = step_process

    def begin(self):
        self.set_filelist()
        self.counts = len(self.filenames)
        if self.ref_idx == -1:
            self.ref_idx = len(self.filenames) // 2

    def run_frame(self, idx, ref_idx):
        assert False, 'abstract method'

    def run_step(self):
        if self.count == 1:
            self.__idx = self.ref_idx if self.step_process else 0
            self.__ref_idx = self.ref_idx
            self.__idx_step = +1
        ll = len(self.filenames)
        self.print_message_r(
            colored("step {}/{}: process file: {}, reference: {}".format(self.count, ll, self.filenames[self.__idx],
                                                                         self.filenames[self.__ref_idx]), "blue"))
        self.run_frame(self.__idx, self.__ref_idx)
        if self.__idx < ll:
            if self.step_process:
                self.__ref_idx = self.__idx
            self.__idx += self.__idx_step
        if self.__idx == ll:
            self.__idx = self.ref_idx - 1
            if self.step_process:
                self.__ref_idx = self.ref_idx
            self.__idx_step = -1


class Actions(FramesRefActions):
    def __init__(self, name, actions, input_path=None, output_path=None, working_path=None, plot_path='plots', resample=1, ref_idx=-1, step_process=True):
        FramesRefActions.__init__(self, name, input_path, output_path, working_path, plot_path, resample, ref_idx, step_process)
        self.__actions = []
        for a in actions:
            self.__actions.append(a)

    def begin(self):
        FramesRefActions.begin(self)
        for a in self.__actions:
            a.begin(self)

    def img_ref(self, idx):
        filename = self.filenames[idx]
        img = read_img((self.output_dir if self.step_process else self.input_dir) + "/" + filename)
        self.dtype = img.dtype
        self.shape = img.shape
        if img is None:
            raise Exception("Invalid file: " + self.input_dir + "/" + filename)
        return img

    def run_frame(self, idx, ref_idx):
        filename = self.filenames[idx]
        self.sub_message_r(': read imput image')
        img = read_img(self.input_dir + "/" + filename)
        if hasattr(self, 'dtype') and img.dtype != self.dtype:
            raise BitDepthError(img.dtype, self.dtype)
        if hasattr(self, 'shape') and img.shape != self.shape:
            raise ShapeError(img.shape, self.shape)
        if img is None:
            raise Exception("Invalid file: " + self.input_dir + "/" + filename)
        for a in self.__actions:
            img = a.run_frame(idx, ref_idx, img)
        self.sub_message_r(': write output image')
        if img is not None:
            write_img(self.output_dir + "/" + filename, img)
        else:
            self.print_message("No output file resulted from processing input file: " + self.input_dir + "/" + filename, level=logging.WARNING)

    def end(self):
        for a in self.__actions:
            a.end()
