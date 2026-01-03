"""
YouTube Trends & Translation Module
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pytrends.request import TrendReq
from deep_translator import GoogleTranslator
import deepl
from dotenv import load_dotenv

load_dotenv()

# YouTube Category IDs (official YouTube category mapping)
YOUTUBE_CATEGORIES = {
    "게임": 20,
    "과학/기술": 28,
    "교육": 27,
    "노하우/스타일": 26,
    "뉴스/정치": 25,
    "비영리/사회운동": 29,
    "스포츠": 17,
    "애완동물/동물": 15,
    "엔터테인먼트": 24,
    "여행/이벤트": 19,
    "영화/애니메이션": 1,
    "음악": 10
}

# Language codes for translation
LANGUAGES = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
    "중국어": "zh",
    "스페인어": "es",
    "힌디어": "hi",
    "러시아어": "ru"
}

# DeepL language codes (different from Google)
DEEPL_LANGUAGES = {
    "한국어": "ko",
    "영어": "en-US",
    "일본어": "ja",
    "중국어": "zh",
    "스페인어": "es",
    "힌디어": "hi",
    "러시아어": "ru"
}


class TrendsError(Exception):
    """Trends API error"""
    pass


class TranslationManager:
    """Manages translation using DeepL (if API key available) or Google Translate (free)"""

    def __init__(self):
        self.deepl_api_key = os.getenv("DEEPL_API_KEY", "")
        self.use_deepl = bool(self.deepl_api_key)

        if self.use_deepl:
            try:
                self.deepl_translator = deepl.Translator(self.deepl_api_key)
                print("✅ DeepL API 활성화 (고품질 번역)")
            except Exception as e:
                print(f"⚠️  DeepL API 오류: {e}")
                print("📝 Google Translate로 전환 (무료)")
                self.use_deepl = False

    def translate(self, text: str, target_lang: str, source_lang: str = "ko") -> str:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'en', 'ja')
            source_lang: Source language code (default: 'ko')

        Returns:
            Translated text
        """
        # Skip if target is same as source
        if target_lang == source_lang:
            return text

        try:
            if self.use_deepl:
                return self._translate_deepl(text, target_lang, source_lang)
            else:
                return self._translate_google(text, target_lang, source_lang)
        except Exception as e:
            print(f"⚠️  번역 실패 ({text}): {e}")
            return text

    def _translate_deepl(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using DeepL API"""
        # Convert to DeepL language codes
        target_deepl = DEEPL_LANGUAGES.get(target_lang, target_lang)
        source_deepl = DEEPL_LANGUAGES.get(source_lang, source_lang)

        result = self.deepl_translator.translate_text(
            text,
            source_lang=source_deepl,
            target_lang=target_deepl
        )
        return result.text

    def _translate_google(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using Google Translate (free)"""
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)

    def translate_to_all_languages(self, text: str, source_lang: str = "ko") -> Dict[str, str]:
        """
        Translate text to all supported languages

        Returns:
            Dictionary mapping language names to translated text
        """
        translations = {}

        for lang_name, lang_code in LANGUAGES.items():
            translations[lang_name] = self.translate(text, lang_code, source_lang)

        return translations


class TrendsExplorer:
    """Explore YouTube trending keywords by category"""

    def __init__(self):
        self.pytrends = TrendReq(hl='ko-KR', tz=540)  # Korea timezone
        self.translator = TranslationManager()

    def get_trending_keywords(
        self,
        category: str,
        num_keywords: int = 20,
        timeframe: str = 'now 7-d'
    ) -> List[str]:
        """
        Get trending keywords for a YouTube category

        Args:
            category: Category name (e.g., '게임', '스포츠')
            num_keywords: Number of keywords to return
            timeframe: Time range ('now 1-d', 'now 7-d', 'today 1-m', etc.)

        Returns:
            List of trending keywords
        """
        if category not in YOUTUBE_CATEGORIES:
            raise TrendsError(f"Unknown category: {category}")

        category_id = YOUTUBE_CATEGORIES[category]

        # Get trending searches for this category
        # Note: pytrends doesn't directly support YouTube categories,
        # so we'll use related search terms for the category name
        try:
            # Build payload for the category
            self.pytrends.build_payload(
                kw_list=[category],
                cat=category_id,  # YouTube category filter
                timeframe=timeframe,
                geo='KR'  # Korea region
            )

            # Get related queries
            related_queries = self.pytrends.related_queries()

            keywords = []

            # Extract rising and top queries
            if category in related_queries:
                queries_data = related_queries[category]

                # Get rising queries (trending up)
                if 'rising' in queries_data and queries_data['rising'] is not None:
                    rising = queries_data['rising']['query'].tolist()
                    keywords.extend(rising[:num_keywords // 2])

                # Get top queries (most searched)
                if 'top' in queries_data and queries_data['top'] is not None:
                    top = queries_data['top']['query'].tolist()
                    keywords.extend(top[:num_keywords // 2])

            # Remove duplicates and limit
            keywords = list(dict.fromkeys(keywords))[:num_keywords]

            # If we don't have enough keywords, generate some based on category
            if len(keywords) < 5:
                keywords = self._generate_category_keywords(category, num_keywords)

            return keywords

        except Exception as e:
            print(f"⚠️  트렌드 데이터 수집 오류: {e}")
            # Fallback: generate keywords
            return self._generate_category_keywords(category, num_keywords)

    def _generate_category_keywords(self, category: str, num_keywords: int) -> List[str]:
        """Generate basic keywords for a category (fallback)"""
        # Basic keyword templates for each category
        templates = {
            "게임": [
                "{} 하이라이트", "{} 공략", "{} 리뷰", "{} 플레이",
                "{} 신작", "{} 업데이트", "{} 팁", "{} 명장면"
            ],
            "스포츠": [
                "{} 하이라이트", "{} 경기", "{} 명장면", "{} 골",
                "{} 리뷰", "{} 분석", "{} 실시간", "{} 중계"
            ],
            "음악": [
                "{} 신곡", "{} 뮤직비디오", "{} 라이브", "{} 커버",
                "{} 노래", "{} 앨범", "{} 콘서트", "{} 무대"
            ],
            "영화/애니메이션": [
                "{} 예고편", "{} 리뷰", "{} 명장면", "{} 분석",
                "{} 해석", "{} 요약", "{} 결말", "{} 시리즈"
            ],
            "교육": [
                "{} 강의", "{} 설명", "{} 공부", "{} 배우기",
                "{} 이해하기", "{} 입문", "{} 기초", "{} 고급"
            ],
            "과학/기술": [
                "{} 리뷰", "{} 설명", "{} 작동원리", "{} 비교",
                "{} 분석", "{} 신기술", "{} 개발", "{} 발표"
            ]
        }

        # Get templates for this category or use generic ones
        category_templates = templates.get(
            category,
            ["{} 영상", "{} 리뷰", "{} 하는법", "{} 추천"]
        )

        # Generate keywords
        keywords = []
        for template in category_templates[:num_keywords]:
            # Use category name or leave as template
            keyword = template.format(category)
            keywords.append(keyword)

        return keywords

    def explore_category_with_translations(
        self,
        category: str,
        num_keywords: int = 20
    ) -> List[Dict[str, any]]:
        """
        Get trending keywords for a category with multi-language translations

        Returns:
            List of dictionaries with keyword and translations:
            [
                {
                    'keyword': '게임 하이라이트',
                    'translations': {
                        '한국어': '게임 하이라이트',
                        '영어': 'game highlights',
                        ...
                    }
                },
                ...
            ]
        """
        # Get trending keywords
        keywords = self.get_trending_keywords(category, num_keywords)

        # Translate each keyword
        results = []
        for keyword in keywords:
            translations = self.translator.translate_to_all_languages(keyword)
            results.append({
                'keyword': keyword,
                'translations': translations
            })

        return results
