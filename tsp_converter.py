"""Simple travelling salesman problem on a circuit board."""

#The following command can be used to create images for this program (NEED TO ADD SECOND LINE)
# convert mustang_crop.jpg -resize 128x64 -dither FloydSteinberg -remap pattern:gray50 -compress none mustang2.pbm

#This a link to simple progress bars:wq
# https://towardsdatascience.com/learning-to-use-progress-bars-in-python-2dc436de81e5

from __future__ import print_function
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

import sys
import serial
import json
import time

filepath = sys.argv[-1]

coordinates = []

#create progress bar in window
def progress(count, total, status=''):
	bar_len = 60
	filled_len = int(round(bar_len * count / float(total)))

	percents = round(100.0 * count / float(total), 1)
	bar = '=' * filled_len + '-' * (bar_len - filled_len)

	sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
	sys.stdout.flush() 

def convert(list):
	return tuple(list)

#load .pbm file and serial print to USB port
def create_data_model():
	xypair = [0,0]
	data = {}
	with open(filepath) as fp:	

		#read first three lines (header information)
		file_type = fp.readline()
		file_source = fp.readline()
		file_dimensions = fp.readline()

		#grab the x and y dimensions of the file
		dimensions = file_dimensions.split(" ", 2)

		#read the first character and initialize x and y
		char = fp.read(1)	 
		x = 0
		y = 0
		
		#read the file one character at a time
		while char:
#			if char != '\n':
			if char != '\n' and char != ' ':
				if char == '1':
					xypair[0] = x
					xypair[1] = y
#					print("Line {}: {},{}".format( char, x, y))
					coordinates.append(convert(xypair))
				x += 1
				if x == int(dimensions[0]):  
					x = 0
					y += 1
			char = fp.read(1)
		data['locations'] = coordinates
	data['num_vehicles'] = 1
	data['depot'] = 0
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
	data = {}	
	ser = serial.Serial('/dev/ttyUSB0', 9600)
	# Arduino needs time to start after reset
	time.sleep(2)
	index = routing.Start(0)
	coordinates_route = []
	while not routing.IsEnd(index):
		coordinates_route.append(coordinates[manager.IndexToNode(index)])
		data = 	json.dumps({"xy":coordinates[manager.IndexToNode(index)]})
		print(data)
		ser.write(data.encode('ascii'))
		index = solution.Value(routing.NextVar(index))
		time.sleep(.1)

def main():
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
	main()
