import flask

app = flask.Flask(__name__, static_folder='static', static_url_path="")

@app.route('/')
def home():
    return flask.render_template("homepage.html", pageTitle="Foxfire")

@app.route('/results')
def results():
    return flask.render_template("results.html", pageTitle="Results")

@app.route('/about')
def about():
    return flask.render_template("about.html", pageTitle="About")

@app.route('/contact')
def contact():
    return flask.render_template("contact.html", pageTitle="Contact Us")

@app.errorhandler(404)
def notfound(_):
    return flask.render_template("404.html", pageTitle="Uh Oh- Thats a 404!")

if __name__ == "__main__":
    website_url = "localhost:5000"
    app.config["SERVER_NAME"] = website_url
    app.run(debug=True, use_reloader=False)

