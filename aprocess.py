import subprocess

#	command = 'convert {} {}'.format('static/' + outfile, 'static/' + viewfile)
#	command = 'convert {} +level {}%,100% -resize {} -dither FloydSteinberg -remap pattern:gray50 -compress none {}'.format('static/' + infile, dots, size, 'static/' + outfile) 
#	command = 'convert {} -format %c histogram:info: | grep "#00000" | cut -d':' -f1'.format('static/' + outfile)
#command = "convert static/el5.pbm -format %c histogram:info: | grep "#00000" | cut -d':' -f1"

def point_count(black_level):
	levels = '{}%,100%'.format(black_level)

	#command used to convert standard image to reduced size 1-bit image
	#cmd0 =['convert', 'el5.jpg', '+level', levels, '-resize', '128x64', '-dither', 'FloydSteinberg', '-remap', 'pattern:gray50', '-compress', 'none', 'out.pbm']
	cmd0 =['convert', 'el5.jpg', '+level', levels, '-resize', '640x480', '-dither', 'FloydSteinberg', '-remap', 'pattern:gray50', '-compress', 'none', 'out.pbm']
	subprocess.call(cmd0, shell=False)

	#commands used to return the number of black pixels in an image
	cmd1 =['convert', 'out.pbm', '-format', '%c', 'histogram:info:']
	cmd2 =['grep', '#000000']
	cmd3 =['cut', '-d', ':', '-f1']

	#shell processes for returning image value
	out1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=False)
	out2 = subprocess.Popen(cmd2, stdin=out1.stdout, stdout=subprocess.PIPE, shell=False)
	out3 = subprocess.Popen(cmd3, stdin=out2.stdout, stdout=subprocess.PIPE, shell=False) 
	points = int(out3.communicate()[0].decode('utf-8').strip())
	return points

def main():
	limit = 4000
	points = 0
	level = 90
	while points < limit:
		points = point_count(level)
		print ('{}:{}'.format(level, points))
		level -= 10	

	level += 11
	while points > limit:
		points = point_count(level)
		print ('{}:{}'.format(level, points))
		level += 1

if __name__ == "__main__":
	main()
