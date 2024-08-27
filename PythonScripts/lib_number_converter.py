"""
_summary

Auteur: Nathan Cerisara
"""

from typing import List, Dict, Tuple
import re

class NumberTextToDigitsConverter:
    def __init__(self):
        self.lang_data: Dict[str, Dict[str, int]] = {
            "en": {
                "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
                "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
                "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
                "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000, "million": 1000000
            },
            "fr": {
                "zéro": 0, "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
                "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
                "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
                "seize": 16, "dix-sept": 17, "dix-huit": 18, "dix-neuf": 19, "vingt": 20,
                "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
                "soixante-dix": 70, "quatre-vingt": 80, "quatre-vingt-dix": 90,
                "cent": 100, "mille": 1000, "million": 1000000
            }
        }
        self.connectors: Dict[str, List[str]] = {
            "en": ["and"],
            "fr": ["et"]
        }

    def detect_numbers(self, tokens: List[str], lang: str) -> List[List[str]]:
        """
        Detect number words in a list of tokens and group them.

        Args:
            tokens (List[str]): List of words from the input string.
            lang (str): Language code ('en' or 'fr').

        Returns:
            List[List[str]]: List of grouped number words.
        """
        state = "INITIAL"
        current_number = []
        numbers = []

        for token in tokens:
            lower_token = token.lower()
            if lower_token in self.lang_data[lang] or lower_token in self.connectors[lang]:
                if state == "INITIAL":
                    state = "IN_NUMBER"
                current_number.append(token)
            else:
                if state == "IN_NUMBER":
                    numbers.append(current_number)
                    current_number = []
                state = "INITIAL"

        if current_number:
            numbers.append(current_number)

        return numbers

    def word_to_number(self, words: List[str], lang: str) -> int:
        """
        Convert a list of number words to their numerical value.

        Args:
            words (List[str]): List of number words.
            lang (str): Language code ('en' or 'fr').

        Returns:
            int: Numerical value of the word list.
        """
        total = 0
        current = 0
        for word in words:
            lower_word = word.lower()
            if lower_word in self.lang_data[lang]:
                if self.lang_data[lang][lower_word] == 100:
                    current *= 100
                elif self.lang_data[lang][lower_word] in [1000, 1000000]:
                    current = current or 1
                    total += current * self.lang_data[lang][lower_word]
                    current = 0
                else:
                    current += self.lang_data[lang][lower_word]
            elif lower_word not in self.connectors[lang]:
                raise ValueError(f"Unknown number word: {word}")
        return total + current

    @staticmethod
    def preprocess_text(text: str, lang: str) -> str:
        """
        Preprocess the text by replacing hyphens between number words with spaces.

        Args:
            text (str): Input text.
            lang (str): Language code ('en' or 'fr').

        Returns:
            str: Preprocessed text with hyphens replaced by spaces where appropriate.
        """
        number_words = set()
        for word in NumberTextToDigitsConverter().lang_data[lang].keys():
            number_words.update(word.split('-'))

        pattern = r'\b(' + '|'.join(re.escape(word) for word in number_words) + r')-(?=\w)'
        return re.sub(pattern, r'\1 ', text)

    @staticmethod
    def convert(text: str, lang: str) -> str:
        """
        Convert textual numbers in a string to their numerical representation.

        Args:
            text (str): Input text containing textual numbers.
            lang (str): Language code ('en' or 'fr').

        Returns:
            str: Text with textual numbers converted to digits.
        """
        converter = NumberTextToDigitsConverter()

        # Preprocess the text to handle hyphenated number words
        text = NumberTextToDigitsConverter.preprocess_text(text, lang)

        tokens = re.findall(r'\b\w+(?:-\w+)*\b|\S', text)
        number_groups = converter.detect_numbers(tokens, lang)

        for group in number_groups:
            original = " ".join(group)
            numerical = str(converter.word_to_number(group, lang))
            text = text.replace(original, numerical, 1)

        return text

# Example usage
if __name__ == "__main__":
    print(NumberTextToDigitsConverter.convert("Il y a deux jours, on avait parlé d'IA", lang="fr"))
    print(NumberTextToDigitsConverter.convert("Le vingt-trois et le vingt quatre juillet, Robert avec montré son projet", lang="fr"))
    print(NumberTextToDigitsConverter.convert("The twenty-three and the twenty four july, Robert showed his project", lang="en"))
    print(NumberTextToDigitsConverter.convert("In two thousand eight hundred and seven days, Jean died in global sadness", lang="en"))