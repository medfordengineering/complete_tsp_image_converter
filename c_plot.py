from __future__ import print_function
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from flask import Flask, render_template, request, session
from werkzeug.utils import secure_filename
import subprocess
import os
import sys
import serial
import json
import time

app = Flask(__name__)

#MOVE THIS FROM GLOBAL
coordinates = []

@app.route('/test')
def upload_file():
	return render_template('test.html')
	
@app.route('/run', methods = ['GET', 'POST'])
def uploaded_file():
	if request.method == 'POST':

		# Get and store file
		f = request.files['file']
		infile = secure_filename(f.filename)
		f.save('static/' + infile)

		# Set image parameters
		levels = '80%,100%'
		size = '128x64'

		# Create output file name
		outfile = infile.split('.')[0] + '.pbm'

		# Convert image
		cmd0 =['convert','static/' + infile, '+level', levels, '-resize', size, '-dither', 'FloydSteinberg', '-remap', 'pattern:gray50', '-compress', 'none', 'static/' + outfile]
		subprocess.call(cmd0, shell=False)

		# Create data set
		data = create_data_model('static/' + outfile)

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
		#start_time = time.time()
		solution = routing.SolveWithParameters(search_parameters)
		#elapse = time.time() - start_time
		print("TSP Complete")

		# Print solution on console.
		if solution:
			print_solution(manager, routing, solution)

		return render_template('complete.html')
	
def convert(list):
	return tuple(list)

def create_data_model(filepath):
	xypair = [0,0]
	data = {}
	data.clear()
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
					print("Line {}: {},{}".format( char, x, y))
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
	print('Dataset Complete with {} points.'.format(points))
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
	#NEED USER SET FOR THIS
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
	
if __name__ == '__main__':
	app.run(debug = True)
