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
        # Clean text before translation
        cleaned_text = self._clean_for_translation(text)

        # If cleaned text is too short, return original
        if len(cleaned_text) < 2:
            return text

        try:
            # Convert to DeepL language codes
            target_deepl = DEEPL_LANGUAGES.get(target_lang_name, "EN-US")
            source_deepl = source_lang.upper()

            result = self.deepl_translator.translate_text(
                cleaned_text,
                source_lang=source_deepl,
                target_lang=target_deepl
            )

            if result.text:
                # Shorten the translation to keep it concise
                shortened = self._shorten_translation(result.text, max_words=3, max_chars=20)
                return shortened if shortened else result.text
            else:
                return text
        except Exception as e:
            print(f"⚠️  DeepL 번역 오류 ({text[:30]}...): {str(e)[:50]}")
            return text

    def _clean_for_translation(self, text: str) -> str:
        """Clean text for translation by removing emojis and special characters"""
        import re

        # Remove all emojis and special symbols
        cleaned = re.sub(r'[🎮🎯🔥💯👍❤️😊😂🤣😭🥰😍🤔💪🎉🎊✨⭐🌟💖💕💗💝💘💓💞💟☀️🌙⛅🌈🎵🎶🎤🎧🎬📺📷📸🎨🖼️⚡💥🏆🥇🥈🥉🎁🎀]+', '', text)
        cleaned = re.sub(r'[★☆♡♥→←↑↓■□●○◆◇▲△▼▽※]+', '', cleaned)

        # Remove brackets and parentheses with content
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)

        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove quotes
        cleaned = cleaned.replace('"', '').replace("'", '')

        return cleaned

    def _shorten_translation(self, translated_text: str, max_words: int = 3, max_chars: int = 20) -> str:
        """
        Shorten translated text to keep it concise

        Args:
            translated_text: Translated text
            max_words: Maximum number of words (default: 3)
            max_chars: Maximum characters (default: 20)

        Returns:
            Shortened translation
        """
        import re

        # Remove articles and possessives
        text = translated_text
        text = re.sub(r"\b(the|The|a|A|an|An)\b\s*", "", text)  # English articles
        text = re.sub(r"'s\b", "", text)  # Possessive 's
        text = re.sub(r"\bの\b", "", text)  # Japanese の (possessive)
        text = re.sub(r"\b的\b", "", text)  # Chinese 的 (possessive)

        # Split into words
        words = text.split()

        # Take first max_words
        if len(words) > max_words:
            words = words[:max_words]

        result = ' '.join(words)

        # If still too long, truncate by characters
        if len(result) > max_chars:
            result = result[:max_chars].rsplit(' ', 1)[0]  # Cut at last word boundary

        return result.strip()

    def _translate_google(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using Google Translate (free) with retry logic"""
        import time

        # Clean text before translation
        cleaned_text = self._clean_for_translation(text)

        # If cleaned text is too short, return original
        if len(cleaned_text) < 2:
            return text

        # Try translation with retry logic (max 3 attempts)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                result = translator.translate(cleaned_text)

                if result and len(result) > 0:
                    # Shorten the translation to keep it concise
                    shortened = self._shorten_translation(result, max_words=3, max_chars=20)
                    return shortened if shortened else result
                else:
                    # If no result, wait and retry
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        return text

            except Exception as e:
                if attempt < max_retries - 1:
                    # Retry with delay
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # Final attempt failed, return original
                    print(f"⚠️  Google 번역 오류 ({text[:30]}...): {str(e)[:50]}")
                    return text

        return text

    def translate_to_all_languages(self, text: str, source_lang: str = "ko") -> Dict[str, str]:
        """
        Translate text to all supported languages

        Returns:
            Dictionary mapping language names to translated text
        """
        import time

        translations = {}

        for lang_name in LANGUAGES.keys():
            # 한국어는 원문 그대로
            if lang_name == "한국어":
                translations[lang_name] = text
            else:
                translations[lang_name] = self.translate(text, lang_name, source_lang)
                # Small delay to avoid rate limiting (only for Google Translate)
                if not self.use_deepl:
                    time.sleep(0.1)

        return translations


class TrendsExplorer:
    """Explore YouTube trending keywords by category"""

    def __init__(self):
        self.pytrends = TrendReq(hl='ko-KR', tz=540)  # Korea timezone
        self.translator = TranslationManager()

    def _extract_keywords_from_titles(self, titles: List[str], num_keywords: int = 20) -> List[str]:
        """
        Extract trending keyword phrases from video titles
        Focus on EXTREMELY short 2-word phrases ONLY

        Args:
            titles: List of video titles
            num_keywords: Number of keywords to extract

        Returns:
            List of extracted keyword phrases (EXACTLY 2 words, 4-12 characters)
        """
        keywords = []
        seen = set()

        # Korean particles (조사) to remove from word endings
        particles = ['의', '를', '을', '이', '가', '에', '도', '와', '과', '로', '으로', '에서', '부터', '까지']

        # Korean stopwords to remove
        stopwords = {
            '하는', '되는', '한', '된', '있는', '없는', '위한', '대한', '위해', '대해',
            '있다', '없다', '하다', '되다', '천천히', '빠르게', '정말', '진짜',
            '완전', '너무', '아주', '매우', '봐야', '보면', '보이는', '보는', '본', '보고',
            '중', '속', '안', '밖', '위', '아래', '앞', '뒤'
        }

        def remove_particles(word):
            """Remove Korean particles from word endings"""
            for particle in particles:
                if word.endswith(particle) and len(word) > len(particle) + 1:
                    return word[:-len(particle)]
            return word

        # Clean and prepare titles
        cleaned_titles = []
        for title in titles:
            # Remove emojis and special characters
            cleaned = re.sub(r'[🎮🎯🔥💯👍❤️😊😂🤣😭🥰😍🤔💪🎉🎊✨⭐🌟💖💕💗💝💘💓💞💟☀️🌙⛅🌈🎵🎶🎤🎧🎬📺📷📸🎨🖼️⚡💥🏆🥇🥈🥉🎁🎀]+', '', title)
            cleaned = re.sub(r'[★☆♡♥→←↑↓■□●○◆◇▲△▼▽※]+', '', cleaned)

            # Remove hashtags (everything after #)
            if '#' in cleaned:
                cleaned = cleaned.split('#')[0]

            # Remove brackets and parentheses with content
            cleaned = re.sub(r'\[.*?\]', '', cleaned)
            cleaned = re.sub(r'\(.*?\)', '', cleaned)

            # Remove quotes and exclamation marks
            cleaned = re.sub(r'["""\'\'!?]+', '', cleaned)

            # Remove numbers and uppercase letters like "4M", "TRUE"
            cleaned = re.sub(r'\b[A-Z0-9]+\b', '', cleaned)
            cleaned = re.sub(r'\b\d+\w*\b', '', cleaned)

            # Remove multiple spaces
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            if len(cleaned) >= 5:
                cleaned_titles.append(cleaned)

        # STRATEGY 1: Extract core 2-word phrases ONLY (frequency-based)
        phrase_counter = Counter()

        for title in cleaned_titles:
            # Split and remove particles
            words = []
            for w in title.split():
                if w not in stopwords and len(w) > 1:
                    clean_word = remove_particles(w)
                    if clean_word and len(clean_word) > 1:
                        words.append(clean_word)

            # Extract ONLY 2-word phrases (no 3-word!)
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i + 2])

                # Filter by length (4-12 characters - very short!)
                if 4 <= len(phrase) <= 12:
                    # Skip if mostly numbers
                    if sum(c.isdigit() for c in phrase) < len(phrase) * 0.3:
                        phrase_counter[phrase] += 1

        # Add most common 2-word phrases ONLY
        for phrase, count in phrase_counter.most_common(num_keywords * 2):
            phrase_lower = phrase.lower()
            # Check word count (must be EXACTLY 2 words)
            word_count = len(phrase.split())
            if word_count == 2:
                if not any(phrase_lower in s or s in phrase_lower for s in seen):
                    keywords.append(phrase)
                    seen.add(phrase_lower)
                    if len(keywords) >= num_keywords:
                        return keywords

        # STRATEGY 2: Extract 2-word phrases from title beginnings
        for title in cleaned_titles:
            words = []
            for w in title.split():
                if w not in stopwords and len(w) > 1:
                    clean_word = remove_particles(w)
                    if clean_word and len(clean_word) > 1:
                        words.append(clean_word)

            # ONLY 2-word phrases from beginning
            if len(words) >= 2:
                phrase = ' '.join(words[:2])
                phrase_lower = phrase.lower()

                # Check length (4-12 characters)
                if 4 <= len(phrase) <= 12:
                    if not any(phrase_lower in s or s in phrase_lower for s in seen):
                        keywords.append(phrase)
                        seen.add(phrase_lower)
                        if len(keywords) >= num_keywords:
                            return keywords

        # STRATEGY 3: Single meaningful words as last resort
        for title in cleaned_titles:
            words = []
            for w in title.split():
                if w not in stopwords and len(w) > 2:
                    clean_word = remove_particles(w)
                    if clean_word and len(clean_word) > 2:
                        words.append(clean_word)

            for word in words[:3]:  # Take first 3 meaningful words
                if 3 <= len(word) <= 8:  # Single words: 3-8 characters
                    word_lower = word.lower()
                    if not any(word_lower in s or s in word_lower for s in seen):
                        keywords.append(word)
                        seen.add(word_lower)
                        if len(keywords) >= num_keywords:
                            return keywords

        # Calculate average word count
        avg_words = sum(len(k.split()) for k in keywords) / len(keywords) if keywords else 0
        avg_len = sum(len(k) for k in keywords) / len(keywords) if keywords else 0
        print(f"✅ 추출된 구문: {len(keywords)}개 (평균 단어 수: {avg_words:.1f}개, 평균 길이: {avg_len:.1f}자)")

        return keywords[:num_keywords]

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
        """
        Generate keywords for a category using YouTube search (fallback)
        Uses search API to find real trending content instead of templates
        """
        print(f"🔍 검색 API를 사용하여 '{category}' 관련 인기 콘텐츠를 찾는 중...")

        try:
            # Search for videos related to this category
            search_results = youtube_api.search_videos(
                query=category,
                max_results=50,
                order="viewCount"  # Order by view count for popular content
            )

            if search_results:
                # Get video IDs
                video_ids = [video['video_id'] for video in search_results]

                # Get detailed info
                videos = youtube_api.get_videos_info(video_ids)

                if videos:
                    # Extract titles
                    titles = [video['title'] for video in videos if video.get('title')]
                    print(f"✅ 검색으로 {len(titles)}개 영상 제목 수집 완료")

                    # Extract keywords from titles
                    keywords = self._extract_keywords_from_titles(titles, num_keywords)

                    if keywords:
                        print(f"✅ 검색 기반 {len(keywords)}개 키워드 생성 완료")
                        return keywords

        except Exception as e:
            print(f"⚠️  검색 API 오류: {e}")

        # Ultimate fallback: use templates
        print(f"⚠️  템플릿 기반 키워드 생성 중...")
        templates = {
            "게임": [
                "인기 게임 리뷰", "게임 공략 가이드", "게임 하이라이트 모음",
                "신작 게임 플레이", "게임 팁과 요령", "게임 업데이트 소식",
                "게임 명장면 모음", "게임 리뷰 추천", "인기 게임 순위",
                "게임 스트리밍 방송"
            ],
            "스포츠": [
                "스포츠 하이라이트 모음", "경기 명장면 분석", "선수 인터뷰 모음",
                "스포츠 뉴스 속보", "경기 리뷰 분석", "스포츠 훈련 영상",
                "명경기 다시보기", "스포츠 해설 방송", "선수 기량 분석",
                "스포츠 매거진 리뷰"
            ],
            "음악": [
                "신곡 뮤직비디오 모음", "인기 음악 차트", "라이브 공연 영상",
                "음악 커버 모음", "가수 무대 영상", "콘서트 실황 중계",
                "음악 방송 출연", "신곡 발매 소식", "음악 리뷰 평가",
                "히트곡 메들리 모음"
            ],
            "영화/애니메이션": [
                "영화 예고편 모음", "애니메이션 리뷰", "영화 명장면 분석",
                "영화 해석 영상", "애니메이션 추천", "영화 줄거리 요약",
                "영화 엔딩 해석", "시리즈 총정리", "애니메이션 명장면",
                "영화 비평 리뷰"
            ],
            "교육": [
                "쉬운 교육 강의", "초보자를 위한 설명", "기초부터 배우는 가이드",
                "실전 활용 강의", "단계별 학습 방법", "핵심 개념 정리",
                "입문자 강의 추천", "고급 심화 학습", "실습 강의 모음",
                "핵심 요약 정리"
            ],
            "과학/기술": [
                "최신 기술 리뷰", "과학 원리 설명", "기술 작동 원리",
                "제품 비교 분석", "신기술 소개 영상", "과학 실험 영상",
                "기술 뉴스 속보", "제품 개봉 리뷰", "과학 다큐멘터리",
                "기술 트렌드 분석"
            ],
            "노하우/스타일": [
                "패션 스타일 가이드", "뷰티 메이크업 팁", "DIY 만들기 영상",
                "인테리어 꾸미기", "요리 레시피 모음", "생활 꿀팁 정리",
                "스타일링 노하우", "취미 배우기 강좌", "실용 정보 모음",
                "전문가 팁 공유"
            ],
            "뉴스/정치": [
                "오늘의 뉴스 속보", "정치 이슈 분석", "시사 토론 영상",
                "뉴스 해설 방송", "정치 뉴스 정리", "사회 이슈 리뷰",
                "국제 뉴스 속보", "정책 분석 영상", "뉴스 브리핑 모음",
                "현안 이슈 정리"
            ],
            "비영리/사회운동": [
                "사회 공헌 활동", "봉사 활동 영상", "캠페인 홍보 영상",
                "환경 보호 활동", "기부 문화 소개", "사회 운동 현장",
                "자선 행사 영상", "공익 광고 모음", "나눔 문화 실천",
                "사회 변화 운동"
            ],
            "애완동물/동물": [
                "반려동물 일상 브이로그", "귀여운 동물 영상", "동물 훈련 가이드",
                "반려동물 키우기 팁", "동물 다큐멘터리", "동물 행동 분석",
                "펫 케어 정보", "동물 병원 정보", "반려동물 용품 리뷰",
                "동물 놀이 영상"
            ],
            "엔터테인먼트": [
                "예능 프로그램 모음", "인기 방송 클립", "연예인 인터뷰",
                "예능 명장면 모음", "토크쇼 영상", "버라이어티 쇼",
                "코미디 영상 모음", "리얼리티 쇼", "방송 비하인드",
                "예능 하이라이트"
            ],
            "여행/이벤트": [
                "여행지 추천 영상", "여행 브이로그", "이벤트 현장 영상",
                "관광지 소개", "여행 정보 가이드", "축제 현장 리포트",
                "해외 여행 팁", "국내 여행지 추천", "여행 경비 절약법",
                "이벤트 참여 후기"
            ]
        }

        # Get templates for this category
        category_templates = templates.get(
            category,
            [
                "인기 영상 모음", "추천 콘텐츠", "베스트 영상 순위",
                "핫한 영상 모음", "재미있는 영상", "화제의 영상",
                "놓치면 안되는 영상", "인기 순위 모음", "트렌드 영상",
                "화제의 콘텐츠"
            ]
        )

        # Return as many templates as requested
        keywords = category_templates[:num_keywords]

        # If we need more, repeat with variations
        while len(keywords) < num_keywords:
            for template in category_templates:
                if len(keywords) >= num_keywords:
                    break
                keywords.append(template)

        return keywords[:num_keywords]

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
