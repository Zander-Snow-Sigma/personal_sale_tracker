"""API"""

from flask import Flask, render_template, request

app = Flask(__name__, template_folder='templates')

submissions = []


@app.route('/')
def index():
    """Displays the HTML homepage"""
    return render_template('input_website.html')


@app.route('/submit', methods=["POST"])
def submit():
    """Handles data submissions"""
    if request.method == 'POST':
        first_name = request.form.get('firstName').capitalize()
        last_name = request.form.get('lastName').capitalize()
        email = request.form.get('email')
        url = request.form.get('url')
        discount = request.form.get('discount')

        data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'url': url,
            'discount': discount
        }

        submissions.append(data)

        print("Form Submitted:")
        for key, value in data.items():
            print(f"{key}: {value}")
        print("\n")

    return render_template('input_website.html')


if __name__ == "__main__":
    app.run(debug=True)
