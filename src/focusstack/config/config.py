class _Config:
    _initialized = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_defaults()
        return cls._instance

    def _init_defaults(self):
        self._DISABLE_TQDM = False
        self._COMBINED_APP = False
        self._DONT_USE_NATIVE_MENU = True
        try:
            __IPYTHON__ # noqa
            self._JUPYTER_NOTEBOOK = True
        except Exception:
            self._JUPYTER_NOTEBOOK = False

    def init(self, **kwargs):
        if self._initialized:
            raise RuntimeError("Config already initialized")
        for k, v in kwargs.items():
            if hasattr(self, f"_{k}"):
                setattr(self, f"_{k}", v)
            else:
                raise AttributeError(f"Invalid config key: {k}")
        self._initialized = True

    @property
    def DISABLE_TQDM(self):
        return self._DISABLE_TQDM

    @property
    def JUPYTER_NOTEBOOK(self):
        return self._JUPYTER_NOTEBOOK

    @property
    def DONT_USE_NATIVE_MENU(self):
        return self._DONT_USE_NATIVE_MENU

    @property
    def COMBINED_APP(self):
        return self._COMBINED_APP

    def __setattr__(self, name, value):
        if self._initialized and name.startswith('_'):
            raise AttributeError("Can't change config after initialization")
        super().__setattr__(name, value)


config = _Config()
