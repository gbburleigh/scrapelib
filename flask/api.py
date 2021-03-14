from flask import Flask, render_template
import os, pandas
from datetime import datetime

app = Flask(__name__, template_folder=os.getcwd() + '/templates/')

_, _, filenames = next(os.walk(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cache/csv/'))
if len(filenames) > 0:
    csv_path = str(max([datetime.strptime(x.strip('.csv'), '%Y-%m-%d') for x in filenames]).date()) + '.csv'
else:
    csv_path = None

csv_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/cache/csv/' + csv_path

# if csv_path is not None:
#     print(csv_path)
#     csv_read = open(csv_path, 'r')
#     page =''
#     while True:
#         read_data = csv_read.readline()
#         page += '<p>%s</p>' % read_data
#         if csv_read.readline() == '':
#             break

@app.route('/')
def home():
    data = pandas.read_csv(csv_path, header=0)
    csvlist = list(data.values)
    return render_template('home.html', csvlist=csvlist)
if __name__ == '__main__':
    app.run(debug=True)