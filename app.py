from flask import Flask, request, jsonify, render_template
import search_movie
import json

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query = request.args.get("q", "")
    search_result = search_movie.searchMovie(query)
    return render_template("search.html", query=query, data=search_result)

@app.route("/search2")
def search2():
    query = request.args.get("q", "")
    #query="shark attack"
    search_result = search_movie.searchMovie(query)
    return search_result

@app.route("/donate")
def donate():
    return render_template("donate.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
