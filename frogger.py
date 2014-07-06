from numpy import matrix
import os
import random
import time
import subprocess
import RPi.GPIO as GPIO
from Adafruit_7Segment import SevenSegment
from multiprocessing import Process
import pygame
import sys

os.environ["SDL_FBDEV"] = "/dev/fb1"
pygame.init()
size = 320, 240
screen = pygame.display.set_mode(size)
pygame.mouse.set_visible(0)

#Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

segment = SevenSegment(address=0x70)

# Game Grid Matrix
O = 0	#OPEN SPACE
C = 1	#CAR
BF = 2	#BUS (front)
BB = 3	#BUS (back)
T = 4	#Turtle
LF = 5	#Log (front)
LM = 6	#Log (middle)
LB = 7	#Log (back)
TE = 8	#End Target (empty)
TF = 9	#End Target (full)
X = 10	#Unusable Space
OC = 11 #Open Car Space
OL = 12 #Open Log Space

GRID_HEIGHT = 13
GRID_WIDTH = 15
position = [12, 7]
number_of_lives = 3
level = 1
game_grid = matrix([
[X,TE,X,X,TE,X,X,TE,X,X,TE,X,X,TE,X],
[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
[O,O,O,O,O,O,O,O,O,O,O,O,O,O,O],
[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
[O,O,O,O,O,O,O,O,O,O,O,O,O,O,O]
])

images = list()
for i in range(14):
	img = pygame.image.load(str(i) + '.png')
	images.append(img)

splash = pygame.image.load('splash.png')
	
def process_car_row(row_number):
	global game_grid
	
	row = game_grid[row_number].tolist()[0]
	row = row[1:GRID_WIDTH] #Dump the leftmost number
	if row[-1] == BF:								#If the rightmost element is the front of a bus,
		row.append(BB)								#the next element has to be the back of the bus
	elif (row[-1] == C) or (row[-1] == BB):			#If the rightmost element is a car,
		row.append(OC)								#the next element should be a space
	else:											#Otherwise, let's randomize it
		r = random.randint(1, 1000)
		s = 125 + ((level+1)**3)/2
		if r < s:
			spawn_car = random.randint(0,1)
			if spawn_car == 1:
				row.append(C)
			else:
				row.append(BF)
		else:
			row.append(OC)
	game_grid[row_number] = row
				
	
def process_log_row(row_number):
	global game_grid
	global position
	
	if position[0] == row_number:
		position[1] = max(position[1] - 1, 0)
	row = game_grid[row_number].tolist()[0]
	row = row[1:GRID_WIDTH] #Dump the leftmost number
	if row[-1] == LB:	#If the rightmost element is the end of a log,
		row.append(OL)	#the next element has to be an open space
	else:				#Otherwise, let's randomize it
		r = random.randint(1, 1000)
		s = 1000 - (300 + ((level+1)**3)/2)
		if (row[-4] == LF or row[-4] == LM) and (row[-3] == LF or row[-3] == LM) and (row[-2] == LF or row[-2] == LM) and (row[-1] == LF or row[-1] == LM) : #logs can't be more than 5 long
			row.append(LB)
		elif (row[-3] == LF or row[-3] == LM) and (row[-2] == LF or row[-2] == LM) and (row[-1] == LF or row[-1] == LM):
			if r < s:
				row.append(LM)
			else:
				row.append(LB)
		elif (row[-2] == LF or row[-2] == LM) and (row[-1] == LF or row[-1] == LM):
			if r < s:
				row.append(LM)
			else:
				row.append(LB)
		elif row[-1] == LF or row[-1] == LM:
			if r < s:
				row.append(LM)
			else:
				row.append(LB)
		else:
			if r < s:
				row.append(LF)
			else:
				row.append(OL)
	game_grid[row_number] = row
	
def process_input():
	global game_grid
	global position

	old_position = list(position)
	#input = [LEFT, RIGHT, UP, DOWN]
	input =  [not GPIO.input(22), not GPIO.input(17), not GPIO.input(21), not GPIO.input(4)] #Each value is inverted since this is active low
	left,right,up,down = input

	if up:
		position[0] = max(position[0] - 1, 0)
	if down:
		position[1] = max(position[1] - 1, 0)
	if left:
		position[0] = min(position[0] + 1, 12)
	if right:
		position[1] = min(position[1] + 1, 14)
		
	#Check to make sure the move is legal (i.e. game_grid[newpos] != X)
	if game_grid[position[0], position[1]] == X:
		position = old_position
		
def handle_death():
	global number_of_lives
	global position

	#TODO: flash position and wait
	number_of_lives = number_of_lives - 1
	position = [12,7] #Reset position
	
	if number_of_lives == 0:
		#Pause and go back to menu/just wait
		time.sleep(3)
		reset()
	
def collision_check():
	global game_grid
	global position
	global level

	y,x = position
	if y == 0: #If we are in the top row
		game_grid[y,x] = TF #Fill in stop
		position = [12,7] #Reset position
		if game_grid[0].tolist()[0] == [X,TF,X,X,TF,X,X,TF,X,X,TF,X,X,TF,X]:
			reset(level + 1)
	elif y >= 1 and y <= 5: #If on log rows
		if game_grid[y,x] == OL: #If no log underneath player
			handle_death()
	elif y >= 7 and y <= 11: #If on car rows
		if game_grid[y,x] != OC: #If car/bus is underneath player
			handle_death()
			
def output_frame():
	global game_grid
	global position
	global images
	
	for y in range(GRID_HEIGHT):
		for x in range(GRID_WIDTH):
			screen.blit(images[game_grid[y,x]], (21*x, 18*y))
	screen.blit(images[13], (21*position[1], 18*position[0]))
	
	pygame.display.flip()

def reset(new_level = 1):
	global position
	global number_of_lives
	global game_grid
	global level
	global splash
	position = [12, 7]
	number_of_lives = 3
	level = new_level #1 if not given
	game_grid = matrix([
[	X,TE,X,X,TE,X,X,TE,X,X,TE,X,X,TE,X],
	[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
	[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
	[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
	[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
	[OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL,OL],
	[O,O,O,O,O,O,O,O,O,O,O,O,O,O,O],
	[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
	[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
	[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
	[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
	[OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC,OC],
	[O,O,O,O,O,O,O,O,O,O,O,O,O,O,O]
	])
	
	if new_level == 1: #Only show splash screen on game over
		screen.blit(splash, (0,0))
		pygame.display.flip()

	#Wait for user's input to continue
	input = [not GPIO.input(22), not GPIO.input(17), not GPIO.input(21), not GPIO.input(4)]
	while 1 not in input:
		input =  [not GPIO.input(22), not GPIO.input(17), not GPIO.input(21), not GPIO.input(4)] #Each value is inverted since this is active low
	
#Application Entry Point
reset()
t1 = time.time()
t2 = time.time()
while True:
	if time.time() - t1 > 0.01:
		process_input()
		collision_check()
		output_frame()
		t1 = time.time()

	if time.time() - t2 > 0.5:
		for row_number in range(1,6):
			process_log_row(row_number)
		for row_number in range(7,12):
			process_car_row(row_number)
		segment.writeDigit(0, 0)
		segment.writeDigit(1, level)
		segment.writeDigit(3, 0)
		segment.writeDigit(4, number_of_lives)
		t2 = time.time()

		
