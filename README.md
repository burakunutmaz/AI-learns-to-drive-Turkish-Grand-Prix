# A.I. Learns to Drive - Turkish Grand Prix
Summary: Cars try to learn to drive through Istanbul Park using genetic algorithm and neural networks.

### Program Info
**Python version**: *3.7.x*,     **Packages Used**: *neat-python, pygame, pygame_gui*<br /><br />
In A.I. Learns to Drive - Turkish Grand Prix, there are 25 cars for each generation. <br />
On the left there is a statistics window with a dynamically updating graph for showing the average fitness value for each generation<br />
On the right, there is a menu for controlling the simulation and the user interface.<br />

### Statistics
* Generation Count: How many generations the program has gone through and the current generation number.
* Cars Alive: The number of alive cars for the current generation.
* Record Time:  Record finishing time (if any of the cars ever finished the race) for all the generations.
* Last Gen. Best Time:  Best finishing time for the last generation (if any of the cars finished the race)
* Average Fitness Graph:  The graph that shows the improvement visually and updates dynamically. (Dynamically changing bounds and intervals).

### Menu
* Pause: Pauses the simulation (Timer also stops).
* Next Generation: Instantly passes the current generation.
* Test the Species: Test the current species by making them go through the track (Istanbul Park) backwards, as if it's a new track. Test starts in the next generation.

### Extra
To start the program make sure you have all the requirements downlaoded and ready to use.
To execute the program type this into the terminal (make sure you are on the right directory)
> python ai_drive.py
