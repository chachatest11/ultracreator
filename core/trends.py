"""
YouTube Trends & Translation Module
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter
import re
from pytrends.request import TrendReq
from deep_translator import GoogleTranslator
import deepl
from dotenv import load_dotenv

# Import YouTube API
from . import youtube_api

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

# Language codes for translation (Google Translate codes)
LANGUAGES = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
    "중국어": "zh-CN",  # Chinese Simplified
    "스페인어": "es",
    "힌디어": "hi",
    "러시아어": "ru"
}

# DeepL language codes (different from Google)
DEEPL_LANGUAGES = {
    "한국어": "KO",
    "영어": "EN-US",
    "일본어": "JA",
    "중국어": "ZH",  # DeepL uses ZH for Chinese
    "스페인어": "ES",
    "힌디어": "HI",
    "러시아어": "RU"
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

    def translate(self, text: str, target_lang_name: str, source_lang: str = "ko") -> str:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_lang_name: Target language name (e.g., '영어', '중국어')
            source_lang: Source language code (default: 'ko')

        Returns:
            Translated text
        """
        # Get target language code
        target_lang = LANGUAGES.get(target_lang_name, "en")

        # Skip if target is same as source
        if target_lang == source_lang or target_lang_name == "한국어":
            return text

        try:
            if self.use_deepl:
                return self._translate_deepl(text, target_lang_name, source_lang)
            else:
                return self._translate_google(text, target_lang, source_lang)
        except Exception as e:
            print(f"⚠️  번역 실패 ({text[:20]}... → {target_lang_name}): {e}")
            return text

    def _translate_deepl(self, text: str, target_lang_name: str, source_lang: str) -> str:
        """Translate using DeepL API"""
        # Convert to DeepL language codes
        target_deepl = DEEPL_LANGUAGES.get(target_lang_name, "EN-US")
        source_deepl = source_lang.upper()

        result = self.deepl_translator.translate_text(
            text,
            source_lang=source_deepl,
            target_lang=target_deepl
        )
        return result.text

    def _translate_google(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using Google Translate (free)"""
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            return result if result else text
        except Exception as e:
            print(f"⚠️  Google 번역 오류: {e}")
            return text

    def translate_to_all_languages(self, text: str, source_lang: str = "ko") -> Dict[str, str]:
        """
        Translate text to all supported languages

        Returns:
            Dictionary mapping language names to translated text
        """
        translations = {}

        for lang_name in LANGUAGES.keys():
            # 한국어는 원문 그대로
            if lang_name == "한국어":
                translations[lang_name] = text
            else:
                translations[lang_name] = self.translate(text, lang_name, source_lang)

        return translations


class TrendsExplorer:
    """Explore YouTube trending keywords by category"""

    def __init__(self):
        self.pytrends = TrendReq(hl='ko-KR', tz=540)  # Korea timezone
        self.translator = TranslationManager()

    def _extract_keywords_from_titles(self, titles: List[str], num_keywords: int = 20) -> List[str]:
        """
        Extract trending keyword phrases from video titles using n-gram analysis

        Args:
            titles: List of video titles
            num_keywords: Number of keywords to extract

        Returns:
            List of extracted keyword phrases (2-4 words)
        """
        # Minimal stopwords - only remove very common filler words
        stopwords = {
            '영상', '동영상', '비디오', '클립', '쇼츠', '쇼트', 'shorts',
            '유튜브', 'youtube', '채널', 'channel',
            '입니다', '합니다', '있습니다', '없습니다',
            'the', 'a', 'an', 'and', 'or', 'but'
        }

        # Extract phrases of 2-5 words
        phrase_counter = Counter()

        for title in titles:
            # Clean and normalize title - keep most punctuation context
            # Remove brackets, parentheses, quotes but keep words
            cleaned = re.sub(r'[\[\]()「」『』【】\(\)《》""\'\']+', ' ', title)
            cleaned = re.sub(r'[|•★☆♡♥→←↑↓]+', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            # Split into words but preserve structure
            words = cleaned.split()

            # Create n-grams (2 to 5 words)
            for n in range(2, 6):  # 2, 3, 4, 5 word phrases
                for i in range(len(words) - n + 1):
                    phrase_words = words[i:i+n]

                    # Skip if contains too many stopwords
                    stopword_count = sum(1 for w in phrase_words if w.lower() in stopwords or w in stopwords)
                    if stopword_count > len(phrase_words) // 2:
                        continue

                    # Skip if too many numbers or too short
                    phrase = ' '.join(phrase_words)
                    if len(phrase) < 5:  # At least 5 characters
                        continue

                    # Skip if mostly numbers
                    if sum(c.isdigit() for c in phrase) > len(phrase) // 2:
                        continue

                    phrase_counter[phrase] += 1

        # Get most common phrases
        common_phrases = phrase_counter.most_common(num_keywords * 10)

        # Filter by frequency - at least appear in 2 videos OR in top popular
        min_frequency = max(2, len(titles) // 200)  # Very low threshold (0.5%)

        result_phrases = []
        seen_keywords = set()

        for phrase, count in common_phrases:
            if count < min_frequency:
                continue

            # Check if this phrase is too similar to existing ones
            phrase_lower = phrase.lower()
            is_duplicate = False

            for seen in seen_keywords:
                # Skip if this phrase is a subset or superset of existing phrase
                if phrase_lower in seen or seen in phrase_lower:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result_phrases.append(phrase)
                seen_keywords.add(phrase_lower)

            if len(result_phrases) >= num_keywords:
                break

        # If we don't have enough phrases, relax the filters
        if len(result_phrases) < num_keywords // 2:
            print(f"⚠️  추출된 구문이 부족합니다 ({len(result_phrases)}개). 더 많은 구문 추출 중...")

            # Add more phrases with lower frequency
            for phrase, count in common_phrases:
                if phrase in result_phrases:
                    continue

                phrase_lower = phrase.lower()
                is_duplicate = False
                for seen in seen_keywords:
                    if phrase_lower in seen or seen in phrase_lower:
                        is_duplicate = True
                        break

                if not is_duplicate and count >= 1:  # Just need to appear once
                    result_phrases.append(phrase)
                    seen_keywords.add(phrase_lower)

                if len(result_phrases) >= num_keywords:
                    break

        return result_phrases[:num_keywords]

    def get_trending_keywords(
        self,
        category: str,
        num_keywords: int = 20,
        timeframe: str = 'now 7-d'
    ) -> List[str]:
        """
        Get trending keywords for a YouTube category by analyzing popular videos

        Args:
            category: Category name (e.g., '게임', '스포츠')
            num_keywords: Number of keywords to return
            timeframe: Time range (not used with YouTube API)

        Returns:
            List of trending keywords
        """
        if category not in YOUTUBE_CATEGORIES:
            raise TrendsError(f"Unknown category: {category}")

        category_id = YOUTUBE_CATEGORIES[category]

        try:
            # Get popular videos from YouTube API
            print(f"📊 '{category}' 카테고리의 인기 영상 제목 분석 중...")

            # Fetch popular videos for this category
            video_ids = youtube_api.get_popular_videos_by_category(
                category_id,
                max_results=100,  # Analyze top 100 videos
                region_code='KR'  # Korea region
            )

            if not video_ids:
                print(f"⚠️  인기 영상을 찾을 수 없습니다. 대체 방법 사용...")
                return self._generate_category_keywords(category, num_keywords)

            # Get video details (titles)
            videos = youtube_api.get_videos_info(video_ids)

            if not videos:
                print(f"⚠️  영상 정보를 가져올 수 없습니다. 대체 방법 사용...")
                return self._generate_category_keywords(category, num_keywords)

            # Extract titles
            titles = [video['title'] for video in videos if video.get('title')]

            print(f"✅ {len(titles)}개 영상 제목 수집 완료")

            # Extract keywords from titles
            keywords = self._extract_keywords_from_titles(titles, num_keywords)

            if len(keywords) < 5:
                print(f"⚠️  추출된 키워드가 부족합니다. 대체 방법 사용...")
                return self._generate_category_keywords(category, num_keywords)

            print(f"✅ {len(keywords)}개 트렌딩 키워드 추출 완료")
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
