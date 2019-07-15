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


class InvalidRequest(RuntimeError):
    def __init__(self, what):
        RuntimeError.__init__(self, what)


class FlashContext:
    def __init__(self):
        self.question_ids = []
        self.answers = []

    def __str__(self):
        zipped = zip(self.question_ids, self.answers)
        return '\n'.join(['\n'.join([str(element) for element in pair]) for pair in zipped])

    def __repr__(self):
        return str(self)

    @staticmethod
    def from_str(text):
        result = FlashContext()

        if not text:
            return result

        elements = [e.strip() for e in text.split('\n')]

        for i in range(1, len(elements), 2):
            result.question_ids.append(elements[i - 1])
            result.answers.append(elements[i])

        return result

    def add_answer(self, question_id, answer):
        self.question_ids.append(question_id)
        self.answers.append(str(answer).replace('\n', ' '))

    def __len__(self):
        return len(self.question_ids)

    def correct(self, dictionary):
        correct = 0
        for i in range(len(self.question_ids)):
            if dictionary[self.question_ids[i]].any_matches(self.answers[i]):
                correct += 1
        return correct


class Repertoaari:
    def __init__(self, dictionary=None):
        self.__dictionary = dictionary or CachedDictionaries()
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
        if translation.any_matches(actual):
            ui.tell_answer_was_correct(translation.accepted())
            return 1.0

        ui.tell_answer_was_wrong(translation.accepted())
        return 0.0

    def show_exam(self, ui, dictionary_name, words):
        if not isinstance(words, int):
            raise InvalidRequest("Number of requested words for quiz is not an integer")

        if words < 1:
            raise InvalidRequest("There need to be at least one word in an exam (requested {0} words)".format(words))

        if words > 256:
            raise InvalidRequest("We do not support more than 256 words in an exam (requested {0} words)".format(words))

        dictionary = self.__dictionary.load(dictionary_name)
        ui.display_dictionary_name(dictionary.name)
        ui.display_direction(dictionary.left, dictionary.right)
        for question_id in dictionary.pick_random_ids(words):
            question = dictionary[question_id]
            ui.ask_for(str(question_id), question.word, None)

        return ui

    class Answer:
        def __init__(self, question_id, side, answer):
            self.question_id = question_id
            self.side = side
            self.given = answer

    def assess_exam(self, ui, dictionary_name, answers):
        submitted_answers = len(answers)

        if submitted_answers < 1:
            raise InvalidRequest("There need to be at least one word in an exam to assess (submitted {0} words)".format(submitted_answers))

        if submitted_answers > 256:
            raise InvalidRequest("We do not support more than 256 words in an exam to assess (submitted {0} words)".format(submitted_answers))

        result = 0
        dictionary = self.__dictionary.load(dictionary_name)
        ui.display_dictionary_name(dictionary.name)
        ui.display_direction(dictionary.left, dictionary.right)
        for answer in answers:
            question = dictionary[int(answer.question_id)]

            if answer.side == 'left':
                question = question.reversed()

            matches = question.any_matches(answer.given)
            if matches:
                result += 1

            left_matched = None if answer.side == 'right' else matches
            right_matched = None if answer.side == 'left' else matches
            left_note = None if answer.side == 'right' else question.accepted()
            right_note = None if answer.side == 'left' else question.accepted()

            ui.show_assessment(answer.question_id, question.word, answer.given, left_matched, right_matched, left_note, right_note)

        ui.display_summary(result, len(answers))
        return ui

    def show_flash(self, ui, dictionary_name, context):
        dictionary = self.__dictionary.load(dictionary_name)
        ui.display_dictionary_name(dictionary.name)

        question_id = dictionary.pick_random_id()
        question = dictionary[question_id]
        ui.ask_for(str(question_id), dictionary.left, question.word, dictionary.right)
        Repertoaari.update_context(ui, context, dictionary)

        return ui

    def assess_flash(self, ui, dictionary_name, question_id, answer, context):
        dictionary = self.__dictionary.load(dictionary_name)
        ui.display_dictionary_name(dictionary.name)

        question = dictionary[int(question_id)]
        matched = question.any_matches(answer)
        ui.show_assessment(str(question_id), dictionary.left, question.word, dictionary.right, answer, question.accepted(), matched)

        context.add_answer(question_id, answer)
        Repertoaari.update_context(ui, context, dictionary)

        return ui

    @staticmethod
    def update_context(ui, context, dictionary):
        correct_answers = context.correct(dictionary)
        questions_asked = len(context)
        percentage = 100.0 * correct_answers / float(questions_asked) if questions_asked > 0 else 0.0
        ui.display_state(str(correct_answers), str(questions_asked), '{0:.2f}%'.format(percentage))
        ui.store_context(context)

    def show_dictionary(self, ui, dictionary_name):
        dictionary = self.__dictionary.load(dictionary_name)

        ui.display_dictionary_name(dictionary.name)
        ui.display_direction(dictionary.left, dictionary.right)

        for entry in dictionary:
            ui.display_entry(entry.word, entry.accepted())

        return ui


class Translation(object):
    def __init__(self, word, accepted_translations):
        self.word = word
        self.__accepted = accepted_translations

    def reversed(self):
        return Translation(self.__accepted, self.word)

    def any_matches(self, actual):
        for acceptable in self.__accepted:
            if acceptable.match(actual):
                return True
        return False

    def accepted(self):
        return ', '.join([str(s) for s in self.__accepted])


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
    def __init__(self, filename, name=None):
        self.__dict = []
        self.__keys = set()
        self.left = "Left"
        self.right = "Right"
        self.name = name or filename

        try:
            self.__load_from(filename)
        except FileNotFoundError:
            raise NoSuchDictionary(filename)

    def __len__(self):
        return len(self.__keys)

    def __getitem__(self, item):
        return self.__dict[int(item)]

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

    def pick_random_ids(self, number):
        method = random.sample if number <= len(self.__dict) else random.choices
        return method(range(len(self.__dict)), k=number)


class CachedDictionaries(object):
    def __init__(self):
        self.__current = None
        self.__all = dict()

    def load(self, name):
        if len(self.__all) > 10:
            self.__all.clear()

        if not re.match('^[0-9A-Za-z._-]+$', name):
            raise InvalidRequest("Dictionary name '{0}' is not supported - names may not contain special letters".format(name))

        if not name in self.__all:
            self.__all[name] = FromFileDictionary(os.path.dirname(os.path.abspath(__file__)) + '/' + name + '.dict', name)

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
        print(self.indent() + ansi_format('✗  ', RED) + ansi_format(accepted, RED, ITALIC))

    def tell_answer_was_correct(self, accepted):
        print(self.indent() + ansi_format('✓  ', GREEN) + ansi_format(accepted, GREEN, ITALIC))

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
