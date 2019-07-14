from flask import Flask, render_template, url_for, abort, request
from repertoaari import CachedDictionaries, NoSuchDictionary, Repertoaari, FlashContext

flask_app = Flask(__name__)
dictionaries = CachedDictionaries()
repertoaari = Repertoaari(dictionaries)


@flask_app.route("/")
def hello():
    return "Hello, World!"


@flask_app.errorhandler(404)
def page_not_found(error):
    return render_template(
        'page_not_found.html',
        path=request.path,
        method=request.method
    ), 404


@flask_app.errorhandler(500)
def page_not_found(error):
    return render_template(
        'internal_server_error.html',
        error=error.description
    ), 500


class Page:
    def __init__(self):
        self.kwargs = dict()
        self.kwargs['stylesheet'] = url_for('static', filename='style.css')

    def display_dictionary_name(self, name):
        self.kwargs["dict_name"] = name
        self.kwargs["dict_href"] = url_for('show_dictionary_listing', dict_file=name)
        self.kwargs["exam_href"] = url_for('show_exam_ltr', dict_file=name, words=12)


class TabularPage(Page):
    class ExamEntry:
        def __init__(self, id, pos, left, right, left_class, right_class, left_note=None, right_note=None):
            self.id = id
            self.pos = pos
            self.left = left or ''
            self.right = right or ''
            self.left_class = left_class
            self.right_class = right_class
            self.left_note = left_note
            self.right_note = right_note

    class DictEntry:
        def __init__(self, left, right):
            self.left = left
            self.right = right

    def display_direction(self, left_title, right_title):
        self.kwargs["left_title"] = left_title
        self.kwargs["right_title"] = right_title

    def ask_for(self, question_id, left_value, right_value):
        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.ExamEntry(question_id, len(entries), left_value, right_value,
                                      'answer' if left_value is None else None,
                                      'answer' if right_value is None else None))

    def show_assessment(self, question_id, left_value, right_value, left_correct, right_correct, left_note, right_note):
        styles = {None: None, True: 'correct', False: 'wrong'}

        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.ExamEntry(question_id, len(entries),
                                      left_value, right_value,
                                      styles[left_correct], styles[right_correct],
                                      left_note, right_note))

    def display_entry(self, left_value, right_value):
        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.DictEntry(left_value, right_value))

    def display_summary(self, points_awarded, max_points):
        self.kwargs["points_awarded"] = points_awarded
        self.kwargs["max_points"] = max_points
        self.kwargs["grade"] = '{0:.2f}%'.format(100.0 * points_awarded / float(max_points))


@flask_app.route("/<dict_file>/list")
def show_dictionary_listing(dict_file):
    try:
        selected = dictionaries.load(dict_file)

        page = TabularPage()
        page.display_dictionary_name(dict_file)
        page.display_direction(selected.left, selected.right)

        for entry in selected:
            page.display_entry(entry.word, entry.accepted())

        return render_template(
            'listing.html',
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['GET'])
def show_exam_ltr(dict_file, words):
    try:
        page = TabularPage()

        dictionary = dictionaries.load(dict_file)
        repertoaari.show_left_to_right_exam(page, dictionary, words)

        return render_template(
            'exam.html',
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['POST'])
def assess_exam_ltr(dict_file, words):
    try:
        page = TabularPage()

        answers = []
        for key in sorted(request.form.keys()):
            if key.strip().startswith('answer_'):
                elements = key.strip().split('_')
                answers.append(Repertoaari.Answer(elements[2], elements[3], request.form[key]))

        dictionary = dictionaries.load(dict_file)
        repertoaari.assess_exam(page, dictionary, answers)
        return render_template(
            'exam.html',
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)


class FlashPage(Page):
    class Result:
        def __init__(self, correct, total, percent):
            self.correct = correct
            self.total = total
            self.percent = percent

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

    def set_next(self, action):
        self.kwargs['action'] = action

    def show_assessment(self, question_id, given_language, given_word, answer_language, answer, expected, matched):
        self.kwargs['id'] = question_id
        self.kwargs['given_language'] = given_language
        self.kwargs['given_word'] = given_word

        style = 'correct' if matched else 'wrong'
        self.kwargs['answer'] = self.Answer(answer_language, answer, style, expected, 'note-' + style)

    def store_context(self, context):
        if context is not None:
            self.kwargs["context"] = str(context)


@flask_app.route("/<dict_file>/flash", methods=['GET', 'POST'])
def show_flash(dict_file):
    try:
        page = FlashPage()
        page.set_next(url_for('show_assess_flash', dict_file=dict_file))

        dictionary = dictionaries.load(dict_file)
        context = FlashContext.from_str(request.form['context'], dictionary) if 'context' in request.form.keys() else None
        repertoaari.show_flash(page, dictionary, context)

        return render_template(
            'flash.html',
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)


@flask_app.route("/<dict_file>/assess_flash", methods=['POST'])
def show_assess_flash(dict_file):
    try:
        page = FlashPage()
        page.set_next(url_for('show_flash', dict_file=dict_file))

        dictionary = dictionaries.load(dict_file)
        context = FlashContext.from_str(request.form['context'], dictionary) if 'context' in request.form.keys() else None
        repertoaari.assess_flash(page, dictionary, request.form['id'], request.form['answer'], context)

        return render_template(
            'flash.html',
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)
