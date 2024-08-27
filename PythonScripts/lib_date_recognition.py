"""
Module de Reconnaissance de dates dans du texte basé sur des règles syntaxiques.

Auteur: Nathan Cerisara
"""

from typing import Optional, Callable
import re
from datetime import datetime, timedelta
import locale
from lib_number_converter import NumberTextToDigitsConverter
from language_translation import detect_language
import calendar

# Define language-specific patterns and time units outside the class

# Supported languages set
SUPPORTED_LANGS: set[str] = {"fr", "en"}

# dictionary for time units in different languages
TIME_UNITS: dict[str, dict[str, str]] = {
    'en': {
        'second': 'second|seconds|sec|secs',
        'minute': 'minute|minutes|min|mins',
        'hour': 'hour|hours|hr|hrs',
        'day': 'day|days',
        'week': 'week|weeks',
        'month': 'month|months',
        'year': 'year|years',
    },
    'fr': {
        'second': 'seconde|secondes|sec|secs',
        'minute': 'minute|minutes|min|mins',
        'hour': 'heure|heures|hr|hrs',
        'day': 'jour|jours',
        'week': 'semaine|semaines',
        'month': 'mois',
        'year': 'an|année|ans|années',
    },
    # Add more languages here
}

#
INTERVAL_PATTERNS: dict[str, dict[str, str]] = {
    "en": {
        "last": "last",
        "next": "next",
        "in": "in",
        "from": "from",
        "to": "to"
    },
    "fr": {
        "last": "dernier|dernière",
        "next": "prochain",
        "in": "dans",
        "from": "de|depuis",
        "to": "à|jusqu'à|jusqu'au"
    }
}

# dictionary for relative date patterns in different languages
RELATIVE_PATTERNS: dict[str, dict[str, timedelta | str]] = {
    'en': {
        'today|this morning|in the morning|this afternoon|in the afternoon': timedelta(days=0),
        'tomorrow': timedelta(days=1),
        'day after tomorrow': timedelta(days=2),
        'yesterday': timedelta(days=-1),
        'day before yesterday': timedelta(days=-2),
        'next week': timedelta(weeks=1),
        'last week': timedelta(weeks=-1),
        'next month': timedelta(days=30), # Approximation
        'last month': timedelta(days=-30), # Approximation
        'next year': timedelta(days=365), # Approximation
        'last year': timedelta(days=-365), # Approximation
    },
    'fr': {
        "aujourd'hui|ce matin|dans la matinée|cet aprem|dans l'après midi"
        'demain|le lendemain': timedelta(days=1),
        'après-demain|le surlendemain': timedelta(days=2),
        'hier|la veille': timedelta(days=-1),
        'avant-hier': timedelta(days=-2),
        'la semaine prochaine': timedelta(weeks=1),
        'la semaine dernière': timedelta(weeks=-1),
        'le mois prochain': timedelta(days=30), # Approximation
        'le mois dernier': timedelta(days=-30), # Approximation
        'l\'année prochaine': timedelta(days=365), # Approximation
        'l\'année dernière': timedelta(days=-365), # Approximation
    },
    # Add more languages here
}

# dictionary for connection words used in relative dates
CONNECTION_AFTER_WORDS: dict[str, str] = {
    "en": "in|after",
    "fr": "dans|après",
    # Add more languages here
}

# dictionary for connection words used in relative dates
CONNECTION_BEFORE_WORDS: dict[str, str] = {
    "en": "before|there was",
    "fr": "avant|il y a",
    # Add more languages here
}

DAYS_OF_WEEK: dict[str, dict[int, str]] = {
    'en': {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    },
    'fr': {
        0: 'lundi',
        1: 'mardi',
        2: 'mercredi',
        3: 'jeudi',
        4: 'vendredi',
        5: 'samedi',
        6: 'dimanche'
    }
    # Add more languages as needed
}


class DateDetected:
    def __init__(self, start_date: datetime, end_date: Optional[datetime] = None):
        self.start_date = start_date
        self.end_date = end_date
        self.is_interval = end_date is not None

    def __str__(self):
        if self.is_interval:
            return f"Interval: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
        return f"Point Date: {self.start_date.strftime('%Y-%m-%d')}"

class SimpleDateExtractor:
    def __init__(self):
        # Initialize dictionaries for relative patterns, time units, and connection words
        self.relative_patterns: dict[str, timedelta | str] = {}
        self.time_units: dict[str, str] = {}
        self.connection_after_words: str = ""
        self.connection_before_words: str = ""

        #
        self.word_to_number_converter: NumberTextToDigitsConverter = NumberTextToDigitsConverter()

        # Define regex patterns for absolute dates
        self.absolute_patterns: list[str] = [
            r'(\d{4}/\d{2}/\d{2})',  # YYYY/MM/DD
            r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
            r'(\d{2}/\d{2}/\d{2})',  # MM/DD/YY
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\b\w+\s+\d{1,2},?\s+\d{4})',  # Month Day, Year
            r'(\d{1,2}\s+\b\w+\s+\d{4})',  # Day Month Year
        ]

        # Add new patterns for intervals
        self.interval_patterns: dict[str, dict[str, str]] = {}
        self.interval_patterns_extractors: dict[str, Callable] = {
            r'last (\w+)': self.extract_last_period,
            r'next (\w+)': self.extract_next_period,
            r'in (\w+)': self.extract_in_period,
            r'from (.+) to (.+)': self.extract_from_to,
        }

    def get_last_day(self, day: int) -> datetime:
        now = datetime.now()
        last_day = now - timedelta(days=(now.weekday() - day) % 7)
        return last_day

    def get_last_monday(self) -> datetime:
        return self.get_last_day(0)

    def get_last_tuesday(self) -> datetime:
        return self.get_last_day(1)

    def get_last_wednesday(self) -> datetime:
        return self.get_last_day(2)

    def get_last_thursday(self) -> datetime:
        return self.get_last_day(3)

    def get_last_friday(self) -> datetime:
        return self.get_last_day(4)

    def get_last_saturday(self) -> datetime:
        return self.get_last_day(5)

    def get_last_sunday(self) -> datetime:
        return self.get_last_day(6)

    def next_month(self, reference_date: datetime) -> datetime:
        # Calculate the date for the next month
        year: int = reference_date.year + (reference_date.month // 12)
        month: int = reference_date.month % 12 + 1
        return datetime(year, month, 1)

    def last_month(self, reference_date: datetime) -> datetime:
        # Calculate the date for the last month
        year: int = reference_date.year - (1 if reference_date.month == 1 else 0)
        month: int = 12 if reference_date.month == 1 else reference_date.month - 1
        return datetime(year, month, 1)

    def next_year(self, reference_date: datetime) -> datetime:
        # Calculate the date for the next year
        return datetime(reference_date.year + 1, reference_date.month, 1)

    def last_year(self, reference_date: datetime) -> datetime:
        # Calculate the date for the last year
        return datetime(reference_date.year - 1, reference_date.month, 1)

    def parse_date(self, date_str: str) -> Optional[datetime]:
        # Parse date from string using multiple formats
        formats: list[str] = [
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%m/%d/%y',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%d %B %Y'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def extract_relative_dates(self, text: str) -> list[DateDetected]:
        dates = []
        now = datetime.now()
        for pattern, delta in self.relative_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                if isinstance(delta, timedelta):
                    dates.append(DateDetected(now + delta))
                else:
                    delta_method = getattr(self, delta)
                    dates.append(DateDetected(delta_method(now)))
        return dates

    def extract_absolute_dates(self, text: str) -> list[DateDetected]:
        dates = []
        for pattern in self.absolute_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    date = self.parse_date(match)
                    if date:
                        dates.append(DateDetected(date))
                except ValueError:
                    continue
        return dates

    def extract_in_number_time(self, text: str) -> list[DateDetected]:
        now = datetime.now()
        dates = []
        for unit, pattern in self.time_units.items():
            # After words
            regex = rf'\b(?:{self.connection_after_words})\s+(\d+)\s+({pattern})\b'
            matches = re.findall(regex, text, re.IGNORECASE)
            for match in matches:
                number = int(match[0])
                delta = self.get_timedelta(unit, number)
                future_date = now + delta
                dates.append(DateDetected(future_date))
            # Before words
            regex = rf'\b(?:{self.connection_before_words})\s+(\d+)\s+({pattern})\b'
            matches = re.findall(regex, text, re.IGNORECASE)
            for match in matches:
                number = int(match[0])
                delta = self.get_timedelta(unit, number)
                future_date = now - delta
                dates.append(DateDetected(future_date))
        return dates

    def get_timedelta(self, unit: str, number: int) -> timedelta:
        if 'second' in unit:
            return timedelta(seconds=number)
        elif 'minute' in unit:
            return timedelta(minutes=number)
        elif 'hour' in unit:
            return timedelta(hours=number)
        elif 'day' in unit:
            return timedelta(days=number)
        elif 'week' in unit:
            return timedelta(weeks=number)
        elif 'month' in unit:
            return timedelta(days=number * 30)  # Approximation
        elif 'year' in unit:
            return timedelta(days=number * 365)  # Approximation
        return timedelta()

    def extract_last_period(self, period: str) -> DateDetected:
        now = datetime.now()
        if period == 'year':
            start = datetime(now.year - 1, 1, 1)
            end = datetime(now.year - 1, 12, 31)
        elif period == 'month':
            first_day = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day = now.replace(day=1) - timedelta(days=1)
            start, end = first_day, last_day
        elif period == 'week':
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
        else:
            return DateDetected(now - timedelta(days=1))
        return DateDetected(start, end)

    def extract_next_period(self, period: str) -> DateDetected:
        now = datetime.now()
        if period == 'year':
            start = datetime(now.year + 1, 1, 1)
            end = datetime(now.year + 1, 12, 31)
        elif period == 'month':
            start = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
            end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period == 'week':
            start = now + timedelta(days=7 - now.weekday())
            end = start + timedelta(days=6)
        else:
            return DateDetected(now + timedelta(days=1))
        return DateDetected(start, end)

    def extract_in_period(self, period: str) -> Optional[DateDetected]:
        now = datetime.now()
        if period.isdigit():
            year = int(period)
            if 1000 <= year <= 9999:  # Ensure it's a valid 4-digit year
                return DateDetected(datetime(year, 1, 1), datetime(year, 12, 31))
        else:
            # Check if the period is a number of months
            match = re.match(r'(\d+)\s+(\w+)', period)
            if match:
                number, unit = match.groups()
                number = int(number)
                if any(month_unit in unit.lower() for month_unit in self.time_units['month'].split('|')):
                    future_date = now + timedelta(days=number * 30)  # Approximation
                    return DateDetected(future_date)

            try:
                month = list(calendar.month_name).index(period.capitalize())
                year = now.year if month >= now.month else now.year + 1
                start = datetime(year, month, 1)
                end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                return DateDetected(start, end)
            except ValueError:
                return None
        return None

    def extract_from_to(self, from_date: str, to_date: str) -> Optional[DateDetected]:
        start = self.parse_date_or_day(from_date)
        end = self.parse_date_or_day(to_date)
        if start and end:
            return DateDetected(start, end)
        return None

    def parse_date_or_day(self, date_str: str) -> Optional[datetime]:
        date = self.parse_date(date_str)
        if date:
            return date

        for lang, days in DAYS_OF_WEEK.items():
            for day_num, day_name in days.items():
                if day_name in date_str.lower():
                    return getattr(self, f'get_last_{day_name}')()
        return None

    def extract_intervals(self, text: str) -> list[DateDetected]:
        intervals = []
        for pattern, extractor in self.interval_patterns_extractors.items():
            for ip, ip_regex in self.interval_patterns.items():
                if ip in pattern:
                    pattern = pattern.replace(ip, ip_regex)
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    interval = extractor(*match)
                else:
                    interval = extractor(match)
                if interval:
                    intervals.append(interval)
        return intervals

    def preprocess_text(self, text: str, lang: str) -> str:
        # Convert written numbers to digits in the text
        return self.word_to_number_converter.convert(text, lang)

    def extract_dates(self, text: str) -> list[DateDetected]:
        text = text.lower()
        language = detect_language(text)
        print(f"Detected Language: {language}")
        if language not in SUPPORTED_LANGS:
            return []

        locale.setlocale(locale.LC_TIME, language)
        self.relative_patterns = RELATIVE_PATTERNS.get(language, {})
        self.time_units = TIME_UNITS.get(language, {})
        self.connection_after_words = CONNECTION_AFTER_WORDS.get(language, "")
        self.connection_before_words = CONNECTION_BEFORE_WORDS.get(language, "")
        self.interval_patterns = INTERVAL_PATTERNS.get(language, "")

        preprocessed_text = self.preprocess_text(text, language)
        relative_dates = self.extract_relative_dates(preprocessed_text)
        absolute_dates = self.extract_absolute_dates(preprocessed_text)
        in_number_time_dates = self.extract_in_number_time(preprocessed_text)
        intervals = self.extract_intervals(preprocessed_text)

        return relative_dates + absolute_dates + in_number_time_dates + intervals

# Pour pouvoir tester rapidement ce module
if __name__ == "__main__":
    extractor = SimpleDateExtractor()
    text = input(">>> ")
    while text not in ["q", "exit", "quit"]:
        extracted_dates = extractor.extract_dates(text)
        for date in extracted_dates:
            print(date)
        text = input(">>> ")