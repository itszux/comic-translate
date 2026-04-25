import asyncio
from typing import Any

from .base import TraditionalTranslation
from ..utils.textblock import TextBlock


class LocalGoogleTranslation(TraditionalTranslation):
    """Translation engine using Local Google Translate via googletrans."""
    
    def __init__(self):
        self.source_lang_code = None
        self.target_lang_code = None
        self.translator = None
        
    def initialize(self, settings: Any, source_lang: str, target_lang: str) -> None:
        try:
            from googletrans import Translator
            self._Translator = Translator
        except ImportError:
            print("googletrans is not installed. Please run: pip install googletrans==4.0.0-rc1")
            self._Translator = None
        
        raw_src = self.get_language_code(source_lang)
        raw_tgt = self.get_language_code(target_lang)
        self.source_lang_code = self.preprocess_language_code(raw_src)
        self.target_lang_code = self.preprocess_language_code(raw_tgt)
        if self._Translator:
            self.translator = self._Translator()
        
    def translate(self, blk_list: list[TextBlock]) -> list[TextBlock]:
        if getattr(self, '_Translator', None) is None:
            for blk in blk_list:
                blk.translation = 'Error: googletrans is not installed. Please install googletrans==4.0.0-rc1'
            return blk_list

        # Perform translations asynchronously inside the sync method
        async def translate_all():
            async with self._Translator() as translator:
                for blk in blk_list:
                    text = self.preprocess_text(blk.text, self.source_lang_code)
                    
                    if not text.strip():
                        blk.translation = ''
                        continue
                    
                    try:
                        result = await translator.translate(
                            text, 
                            src=self.source_lang_code, 
                            dest=self.target_lang_code
                        )
                        blk.translation = result.text
                    except Exception as e:
                        print(f"Local Google Translate error: {e}")
                        blk.translation = ''
        
        asyncio.run(translate_all())
        return blk_list 
    
    def preprocess_language_code(self, lang_code: str) -> str:
        if lang_code == 'zh-CN':
            return 'zh-cn'
        if lang_code == 'zh-TW':
            return 'zh-tw'
        return lang_code.lower() if lang_code else 'auto'
