from flask import Flask, render_template

app = Flask(__name__)


# Home Page
@app.route("/")
def home():
    return render_template("index.html")


# Gamification Page (we will build this next)
@app.route("/gamification")
def gamification():
    return render_template("gamification.html")

#challenges page
@app.route("/challenges")
def challenges():
    return render_template("challenges.html")

if __name__ == "__main__":
    app.run(debug=True)