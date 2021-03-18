from flask import Flask, render_template
import os, pandas
from datetime import datetime

app = Flask(__name__, template_folder=os.getcwd() + '/templates/')

_, _, filenames = next(os.walk(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cache/csv/'))
if len(filenames) > 0:
    fn = str(max([datetime.strptime(x.strip('.csv'), '%Y-%m-%d') for x in filenames]).date()) + '.csv'
else:
    fn = None

csv_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cache/csv/' + fn

@app.route('/')
def home():
    data = pandas.read_csv(csv_path, header=0)
    csvlist = list(data.values)
    return render_template('home.html', csvlist=csvlist)
if __name__ == '__main__':
    app.run(debug=True)