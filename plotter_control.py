from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
app = Flask(__name__)

coordinates = []

def convert(list):
	return tuple(list)

@app.route('/upload')
def upload_file():
	return render_template('upload.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def uploaded_file():
	if request.method == 'POST':
		f = request.files['file']
		infile = secure_filename(f.filename)
		outfile = infile.split('.')[0] + '.pbm'
		viewfile = infile.split('.')[0] + '.gif'
		f.save('static/' + infile)
		size = request.form.get('size')
		dots = request.form.get('dots')
		command = 'convert {} +level {}%,100% -resize {} -dither FloydSteinberg -remap pattern:gray50 -compress none {}'.format('static/' + infile, dots, size, 'static/' + outfile) 
		os.system(command)
		command = 'convert {} {}'.format('static/' + outfile, 'static/' + viewfile)
		os.system(command)
		data = create_data_model('static/' + outfile)
		print(data['points'])
		return render_template('uploaded.html', user_image = viewfile, points = data['points'])

@app.after_request
def add_header(r):
	r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
	r.headers["Pragma"] = "no-cache"
	r.headers["Expires"] = "0"
	r.headers['Cache-Control'] = 'public, max-age=0'
	return r	

def create_data_model(filepath):
	xypair = [0,0]
	data = {}
	points = 0
	with open(filepath) as fp:	

		#read first two lines (header information)
		file_type = fp.readline()
		file_dimensions = fp.readline()

		#grab the x and y dimensions of the file
		dimensions = file_dimensions.split(" ", 2)

		#read the first character and initialize x and y
		char = fp.read(1)	 
		x = 0
		y = 0
		
		#read the file one character at a time
		while char:
			if char != '\n' and char != ' ':
				if char == '1':
					xypair[0] = x
					xypair[1] = y
#					print("Line {}: {},{}".format( char, x, y))
					coordinates.append(convert(xypair))
					points += 1
				x += 1
				if x == int(dimensions[0]):  
					x = 0
					y += 1
			char = fp.read(1)
		data['locations'] = coordinates
	data['num_vehicles'] = 1
	data['depot'] = 0
	data['points'] = points
	return data




if __name__ == '__main__':
	app.run(debug = True)
