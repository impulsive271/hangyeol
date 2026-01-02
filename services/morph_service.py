from kiwipiepy import Kiwi

class MorphService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MorphService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.analyzer = None
        self.use_mock = False
        self._load_kiwi()
        self._initialized = True

    def _load_kiwi(self):
        try:
            self.analyzer = Kiwi()
        except Exception as e:
            print(f"⚠️ Kiwi 로드 실패: {e}")
            self.analyzer = None
            self.use_mock = True

    def get_analyzer(self):
        return self.analyzer

    def analyze(self, text):
        if self.use_mock or not self.analyzer:
            # Mock implementation if needed, or just return empty
            return []
        return self.analyzer.analyze(text)
