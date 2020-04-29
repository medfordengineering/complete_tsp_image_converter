from __future__ import print_function
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
import sys
import serial
import json
import time

app = Flask(__name__)

coordinates = []
#data = {}
#data['points'] = 0

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
#		create_data_model('static/' + outfile)
		return render_template('uploaded.html', user_image = viewfile, points = data['points'])

@app.route('/process', methods = ['GET', 'POST'])
def process_file():
	if request.method == 'POST':
		data = request.form.get('data')
		print(data)

#Copied from forums should avoid cacheing. Have not tested if it actually works.
#Have some evidenced that this might work but need a cache view to be sure
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

def compute_euclidean_distance_matrix(locations):
	"""Creates callback to return distance between points."""
	distances = {}
	for from_counter, from_node in enumerate(locations):
		distances[from_counter] = {}
		for to_counter, to_node in enumerate(locations):
			if from_counter == to_counter:
				distances[from_counter][to_counter] = 0
			else:
				# Euclidean distance
				distances[from_counter][to_counter] = (int(
					math.hypot((from_node[0] - to_node[0]),
							   (from_node[1] - to_node[1]))))
	return distances


def print_solution(manager, routing, solution):
	data_pairs = {}	
	ser = serial.Serial('/dev/ttyUSB0', 9600)
	# Arduino needs time to start after reset
	time.sleep(2)
	index = routing.Start(0)
	coordinates_route = []
	while not routing.IsEnd(index):
		coordinates_route.append(coordinates[manager.IndexToNode(index)])
		data_pairs = json.dumps({"xy":coordinates[manager.IndexToNode(index)]})
		print(data_pairs)
		ser.write(data_pairs.encode('ascii'))
		index = solution.Value(routing.NextVar(index))
		time.sleep(.1)

def last():
	"""Entry point of the program."""
	# Instantiate the data problem.
	data = create_data_model()

	# Create the routing index manager.
	manager = pywrapcp.RoutingIndexManager(len(data['locations']),
										   data['num_vehicles'], data['depot'])
	# Create Routing Model.
	routing = pywrapcp.RoutingModel(manager)

	distance_matrix = compute_euclidean_distance_matrix(data['locations'])

	def distance_callback(from_index, to_index):
		"""Returns the distance between the two nodes."""
		# Convert from routing variable Index to distance matrix NodeIndex.
		from_node = manager.IndexToNode(from_index)
		to_node = manager.IndexToNode(to_index)
		return distance_matrix[from_node][to_node]

	transit_callback_index = routing.RegisterTransitCallback(distance_callback)

	# Define cost of each arc.
	routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

	# Setting first solution heuristic.
	search_parameters = pywrapcp.DefaultRoutingSearchParameters()
	search_parameters.first_solution_strategy = (
		routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

	# Solve the problem.
	#THIS IS THE BOTTLE NECK
	solution = routing.SolveWithParameters(search_parameters)
	print("solution")

	# Print solution on console.
	if solution:
		print_solution(manager, routing, solution)

if __name__ == '__main__':
	app.run(debug = True)
