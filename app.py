from flask import Flask, render_template, request

app = Flask('__name__')

#GET /
@app.route('/')
def index():
    return render_template('index.html')

#GET /login
@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "POST":
        return "OK"
    else:
        return render_template('login.html')

#GET /signup
@app.route('/signup', methods=["GET","POST"])
def signup():
    if request.method == "POST":
        return "OK"
    else:
        return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)
