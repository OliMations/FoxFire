import flask

app = flask.Flask(__name__, static_folder='static', static_url_path="")

@app.route('/')
def home():
    return flask.render_template("temp.html")

if __name__ == "__main__":
    website_url = "localhost:5000"
    app.config["SE1RVER_NAME"] = website_url
    app.run(debug=True, use_reloader=False)