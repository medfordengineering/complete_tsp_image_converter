from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, session

import math
import subprocess
import os
import sys
import serial
import json
import time
import csv

app = Flask(__name__)
app.secret_key = "hello"

@app.route('/upload')
def upload_file():
	return render_template('upload.html')
	
@app.route('/view', methods = ['GET', 'POST'])
def uploaded_file():
	if request.method == 'POST':

		# Get and store file
		f = request.files['file']
		infile = secure_filename(f.filename)
		f.save('static/' + infile)

		# Set image parameters
		size = request.form.get('size')
		limit = request.form.get('point_limit') 

		# Create output file names
		basename = infile.split('.')[0]
		session['basename'] = basename
		outfile = basename + '.pbm'
		viewfile = basename + '.gif'

		# Convert image to PBM
		total_points = find_limit(int(limit), size, infile)

		# Create view file
		cmd = ['convert', 'static/' + outfile, 'static/' + viewfile]
		subprocess.call(cmd, shell=False)

		return render_template('view.html', user_image = viewfile, points = total_points, filename = outfile)

@app.route('/process', methods = ['GET', 'POST'])
def process_file():
	if request.method == 'POST':

		# Create dictionary for TSP	
		data = {}

		# Create file names
		outfile = session['basename'] + '.pbm'
		rawfile = session['basename'] + '_u.csv'
		tspfile = session['basename'] + '_o.csv'

		# Create unsorted data set from PBM and save as csv 
		unsorted = create_data_model('static/' + outfile)
		print_solution(unsorted, 'static/' + rawfile)

		# Check for which process to perform
		process = request.form.get('process')

		if process == 'noTSP':
			print_to_port('static/' + rawfile)
			return render_template('complete.html', elapse_time = 0)

		elif process == 'withTSP':
			# Create the routing index manager.
			data['locations'] = unsorted
			data['num_vehicles'] = 1
			data['depot'] = 0
			manager = pywrapcp.RoutingIndexManager(len(data['locations']), data['num_vehicles'], data['depot'])
			
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

			# Solve the problem and time the process
			start_time = time.time()
			solution = routing.SolveWithParameters(search_parameters)
			elapse = time.time() - start_time
			print("TSP Complete")

			# Create list of ordered pairs and print to txt file
			if solution:
				ordered_pairs = ordered_solution(manager, routing, solution, unsorted)
				print_solution(ordered_pairs, 'static/' + tspfile)
				#print_to_port('static/' + tspfile)
				
			return render_template('complete.html', elapse_time = elapse)

# Avoids caching of image files
@app.after_request
def add_header(r):
	r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
	r.headers["Pragma"] = "no-cache"
	r.headers["Expires"] = "0"
	r.headers['Cache-Control'] = 'public, max-age=0'
	return r	

def convert(list):
	return tuple(list)

def create_data_model(filepath):
	
	# Create lists 
	xypair = [0,0]
	coordinates = []
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
					#print("Line {}: {},{}".format( line, x, y))
					coordinates.append(convert(xypair))
				x += 1
				if x == int(dimensions[0]):  
					x = 0
					y += 1
			char = fp.read(1)
	return coordinates

def point_count(black_level, size, filename):
	outfile = filename.split('.')[0] + '.pbm'
	levels = '{}%,100%'.format(black_level)

	#command used to convert standard image to reduced size 1-bit image
	#PIPE TO FOLLOWING COMMANDS??
	cmd0 =['convert','static/' + filename, '+level', levels, '-resize', size, '-dither', 'FloydSteinberg', '-remap', 'pattern:gray50', '-compress', 'none', 'static/' + outfile]
	subprocess.call(cmd0, shell=False)

	#commands used to return the number of black pixels in an image
	cmd1 =['convert', 'static/' + outfile, '-format', '%c', 'histogram:info:']
	cmd2 =['grep', '#000000']
	cmd3 =['cut', '-d', ':', '-f1']

	#shell processes for returning image value
	out1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=False)
	out2 = subprocess.Popen(cmd2, stdin=out1.stdout, stdout=subprocess.PIPE, shell=False)
	out3 = subprocess.Popen(cmd3, stdin=out2.stdout, stdout=subprocess.PIPE, shell=False) 
	points = int(out3.communicate()[0].decode('utf-8').strip())
	return points

def find_limit(limit, size, filename):
	points = 0
	level = 90

	#look for limit counting down from 90 by 10
	while points < limit:
		points = point_count(level, size, filename)
		#print ('{}:{}'.format(level, points))
		if level < 10:
			return points
		level -= 10	
	level += 11

	#fine tune limit search counting back up by 1
	while points > limit:
		points = point_count(level, size, filename)
		#print ('{}:{}'.format(level, points))
		level += 1
	level -= 1
	return points

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

def ordered_solution(manager, routing, solution, coordinates):
	ordered_pairs = [] 
	index = routing.Start(0)
	while not routing.IsEnd(index):
		ordered_pairs.append(coordinates[manager.IndexToNode(index)])
		index = solution.Value(routing.NextVar(index))
	return ordered_pairs

# Print coordinate list to csv file
def print_solution(coordinates, filename):
	with open(filename, 'w', newline='') as fp:
		csvwriter = csv.writer(fp)
		csvwriter.writerows(coordinates)
	
def print_to_port(filename):
	pairs = ""
	ser = serial.Serial('/dev/ttyUSB0', 115200)
	time.sleep(2)
	with open(filename, 'r') as fp:
		csvreader = csv.reader(fp)
		for row in csvreader:
			pairs = json.dumps(row)	
			ser.write(pairs.encode('ascii'))
			time.sleep(.05)

if __name__ == '__main__':
	app.run(debug = True)
