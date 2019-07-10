from flask import Flask, render_template, url_for, abort, request
from repertoaari import CachedDictionaries, NoSuchDictionary

app = Flask(__name__)
dicts = CachedDictionaries()


@app.route("/")
def hello():
    return "Hello, World!"


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        'page_not_found.html',
        stylesheet=url_for('static', filename='style.css'),
        path=request.path,
        method=request.method
    ), 404


@app.route("/<dict_file>/list")
def show_dictionary_listing(dict_file):
    try:
        selected = dicts.load(dict_file + '.dict')

        return render_template(
            'listing.html',
            stylesheet=url_for('static', filename='style.css'),
            dict_file=dict_file,
            head=[selected.left, selected.right],
            entries=[[e.word, ','.join([str(a) for a in e.accepted])] for e in selected])

    except NoSuchDictionary:
        abort(404)
