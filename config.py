class SingletonMeta(type):
    def __call__(cls, *args, **kwargs):
        if hasattr(cls, '_instance'):
            return cls._instance
        else:
            obj = cls.__new__(cls, *args, **kwargs)
            obj.__init__(*args, **kwargs)
            cls._instance = obj
            return obj


class Config(metaclass=SingletonMeta):
    def __init__(self):
        self.use_emojis = True
        self.framerate = 60
        self.board_width = 16
        self.board_height = 16
        self.mine_count = 10


config = Config()
