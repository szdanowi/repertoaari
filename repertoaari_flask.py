from flask import Flask, request

from impl.ui.web.pages import *
from repertoaari import CachedDictionaries, NoSuchDictionary, Repertoaari, FlashContext, InvalidRequest

flask_app = Flask(__name__)
dictionaries = CachedDictionaries()
repertoaari = Repertoaari(dictionaries)


@flask_app.route("/")
def hello():
    return "Hello, World!"


@flask_app.errorhandler(404)
def on_page_not_found(error):
    return ErrorPage('page_not_found.html').display_error('{0} {1}'.format(request.method, request.path)).render(), 404


@flask_app.errorhandler(500)
def on_server_error(error):
    return ErrorPage('error.html').display_error(error.description).render(), 500


@flask_app.errorhandler(InvalidRequest)
def on_invalid_request(error):
    return ErrorPage('error.html').display_error(error).render(), 400


@flask_app.errorhandler(NoSuchDictionary)
def on_invalid_dictionary(error):
    return on_page_not_found(error)


@flask_app.route("/<dict_file>/list")
def show_dictionary_listing(dict_file):
    dictionary = dictionaries.load(dict_file)

    page = TabularPage('listing.html')
    repertoaari.show_dictionary(page, dictionary)

    return page.render()


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['GET'])
def show_exam_ltr(dict_file, words):
    page = TabularPage('exam.html')

    dictionary = dictionaries.load(dict_file)
    repertoaari.show_left_to_right_exam(page, dictionary, words)

    return page.render()


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['POST'])
def assess_exam_ltr(dict_file, words):
    page = TabularPage('exam.html')

    answers = []
    for key in sorted(request.form.keys()):
        if key.strip().startswith('answer_'):
            elements = key.strip().split('_')
            answers.append(Repertoaari.Answer(elements[2], elements[3], request.form[key]))

    dictionary = dictionaries.load(dict_file)
    repertoaari.assess_exam(page, dictionary, answers)

    return page.render()


@flask_app.route("/<dict_file>/flash", methods=['GET', 'POST'])
def show_flash(dict_file):
    page = FlashPage('flash.html').with_next('show_assess_flash', dict_file=dict_file)

    dictionary = dictionaries.load(dict_file)
    context = FlashContext.from_str(request.form.get('context'), dictionary)
    repertoaari.show_flash(page, dictionary, context)

    return page.render()


@flask_app.route("/<dict_file>/assess_flash", methods=['POST'])
def show_assess_flash(dict_file):
    page = FlashPage('flash.html').with_next('show_flash', dict_file=dict_file)

    dictionary = dictionaries.load(dict_file)
    context = FlashContext.from_str(request.form.get('context'), dictionary)
    repertoaari.assess_flash(page, dictionary, request.form['id'], request.form['answer'], context)

    return page.render()
