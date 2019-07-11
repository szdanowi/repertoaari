#!/usr/bin/env python3
import argparse
import os
import random
import re


class SetUpFailed(Exception):
    def __init__(self, code, *args):
        self.code = code
        self.args = args


class NoSuchDictionary(SetUpFailed):
    def __init__(self, *args):
        SetUpFailed(self, 'err-dict-no-such-file', *args)


class Repertoaari:
    def __init__(self, dictionary):
        self.__dictionary = dictionary
        self.__number_of_questions = 1
        self.__shuffle = True

    def with_num_of_questions(self, number):
        if number < 0:
            raise SetUpFailed('err-args-invalid-questions-number')

        self.__number_of_questions = number
        return self

    def with_shuffle_enabled(self, is_enabled):
        self.__shuffle = is_enabled
        return self

    def run(self, ui):
        questions_to_ask = self.__number_of_questions if self.__number_of_questions != 0 else len(self.__dictionary)

        score = 0.0
        max_score = questions_to_ask * 1.0

        for i in range(0, questions_to_ask):
            question_id = i if not self.__shuffle else self.__dictionary.pick_random_id()
            question = self.__dictionary[question_id]

            actual = ui.ask_question(question.word, (i+1, questions_to_ask))
            score += self.score_answer(ui, question, actual)

        ui.summarize(score, max_score)

    @staticmethod
    def score_answer(ui, translation, actual):
        for acceptable in translation.accepted:
            if acceptable.match(actual):
                ui.tell_answer_was_correct(translation.accepted)
                return 1.0

        ui.tell_answer_was_wrong(translation.accepted)
        return 0.0


class Translation(object):
    def __init__(self, word, accepted_translations):
        self.word = word
        self.accepted = accepted_translations


class WordMatcher:
    def __init__(self, text):
        self.__text = text
        text = re.sub(r"\([^\)]*\)", r"", text).strip()
        text = re.sub(r"\] ", " ]", text)
        text = re.sub(r" \[", "[ ", text)
        text = re.sub(r"\[([^\]]*)\]", r"(\1)?", text)
        self.__expected = re.compile(text.lower())

    def __str__(self):
        return self.__text

    def __repr__(self):
        return str(self)

    def __eq__(self, text):
        return self.__expected.match(text.strip().lower()) is not None

    def __ne__(self, text):
        return not self.__eq__(text)

    def match(self, text):
        return self.__eq__(text)


class FromFileDictionary:
    def __init__(self, filename):
        self.__dict = []
        self.__keys = set()
        self.left = "Left"
        self.right = "Right"

        try:
            self.__load_from(filename)
        except FileNotFoundError:
            raise NoSuchDictionary(filename)

    def __len__(self):
        return len(self.__keys)

    def __getitem__(self, item):
        return self.__dict[item]

    def __load_from(self, filename):
        with open(filename, mode='rt', encoding='UTF-8') as f:
            lines = f.readlines()
            self.left, self.right = self.__from_line(lines[0])

            for line in lines[1:]:
                key, matchers = self.__from_line(line)
                self.__add(key, matchers)

    @staticmethod
    def __from_line(line):
        elements = [e.strip() for e in re.sub('#.*$', '', line).split(';')]

        if len(elements) != 2:
            return None, None

        return elements[0], elements[1]

    def __add(self, key, matchers):
        if not key or not matchers:
            return

        if key in self.__keys:
            raise SetUpFailed('err-dict-duplicated-entry', key)

        self.__keys.add(key)
        self.__dict.append(Translation(key, self.__parse_entries(matchers)))

    @staticmethod
    def __parse_entries(elements):
        return [WordMatcher(e) for e in elements.split(',')]

    def pick_random_id(self):
        return random.randrange(len(self.__dict))


class CachedDictionaries(object):
    def __init__(self):
        self.__current = None
        self.__all = dict()

    def load(self, name):
        if len(self.__all) > 10:
            self.__all.clear()

        if not name in self.__all:
            self.__all[name] = FromFileDictionary(os.path.dirname(os.path.abspath(__file__)) + '/' + name)

        self.__current = self.__all[name]
        return self.__current

    def __getattr__(self, name):
        return self.__current.__getattr__(name)

    def __getitem__(self, item):
        return self.__current.__getitem__(item)

    def __len__(self):
        return self.__current.__len__()


ITALIC = '3'
RED = '31'
GREEN = '32'
WHITE = '97'


def ansi_format(text, *formats):
    return '\033[{0}m{1}\033[0m'.format(';'.join(formats), text)


class TerminalUI(object):
    def __init__(self):
        self.__indent = 0

    def indent(self):
        return ' ' * self.__indent

    def display_fatal_error(self, code, *args):
        print("[ERR] {0}: {1}".format(code, ','.join(*args)))

    def ask_question(self, word, progress=None):
        print('')

        header = ''
        if progress:
            header = "[{0}/{1}]  ".format(progress[0], progress[1])
        else:
            header = "---  "

        prompt = "→  "
        self.__indent = len(header) + len(prompt) - 3
        return input(header + ansi_format(word, WHITE) + "\n" + self.indent() + ansi_format(prompt, WHITE))

    def tell_answer_was_wrong(self, accepted):
        print(self.indent() + ansi_format('✗  ', RED) + ansi_format(', '.join([str(s) for s in accepted]), RED, ITALIC))

    def tell_answer_was_correct(self, accepted):
        print(self.indent() + ansi_format('✓  ', GREEN) + ansi_format(', '.join([str(s) for s in accepted]), GREEN, ITALIC))

    def summarize(self, score, max_score):
        print("\n----------")
        print(ansi_format(" Σ {0:.1f}%".format(score / max_score * 100.0), WHITE))


class Application:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Terminal based vocabulary quiz')
        self.parser.add_argument('-d, --dict', dest='dictionary', type=str, required=True,
                                 help='selects dictionary file to be used for quiz')
        self.parser.add_argument('-n, --number', dest='number', type=int, default=1,
                                 help='determines how many words will be included in the quiz, 0 means number of words in the dictionary')
        self.parser.add_argument('--no-shuffle', dest='no_shuffle', action='store_true',
                                 help='disables selecting words in random order for the quiz')
        self.config = self.parser.parse_args()
        self.ui = TerminalUI()

    def run(self):
        try:
            Repertoaari(FromFileDictionary(self.config.dictionary)) \
                .with_num_of_questions(self.config.number) \
                .with_shuffle_enabled(not self.config.no_shuffle) \
                .run(self.ui)
        except SetUpFailed as e:
            self.ui.display_fatal_error(e.code, e.args)


if __name__ == '__main__':
    Application().run()
