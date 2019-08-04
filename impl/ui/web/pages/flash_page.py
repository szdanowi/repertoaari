from flask import url_for

from impl.ui.web.pages.page import Page


class FlashPage(Page):
    class Result:
        def __init__(self, correct, total, percent):
            self.correct = correct
            self.total = total
            self.percentage = percent
            self.label = '{0}/{1}'.format(correct, total)

    class Answer:
        def __init__(self, language, value=None, style=None, note=None, note_style=None):
            self.language = language
            self.value = value
            self.style = style
            self.note = note
            self.note_style = note_style

    def display_state(self, correct, total, percent):
        self.kwargs['result'] = self.Result(correct, total, percent)

    def ask_for(self, question_id, given_language, given_word, answer_language):
        self.kwargs['id'] = question_id
        self.kwargs['given_language'] = given_language
        self.kwargs['given_word'] = given_word
        self.kwargs['answer'] = self.Answer(answer_language)

    def with_next(self, action, **kwargs):
        self.kwargs['action'] = url_for(action, **kwargs)
        return self

    def show_assessment(self, question_id, given_language, given_word, answer_language, answer, expected, matched):
        self.kwargs['id'] = question_id
        self.kwargs['given_language'] = given_language
        self.kwargs['given_word'] = given_word

        style = 'correct' if matched else 'wrong'
        self.kwargs['answer'] = self.Answer(answer_language, answer, style, expected, 'note-' + style)

    def store_context(self, context):
        if context is not None:
            self.kwargs["context"] = str(context)

    def with_stats_button(self, dict):
        self.kwargs["stats_href"] = url_for('show_flash_stats', dict_file=dict)
        return self
