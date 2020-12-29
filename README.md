# pygsaw
Welcome to my Jigsaw puzzle game, built with python and pyglet. The ultimate 
goal of this project is to make a jigsaw game that captures the feeling of 
building a real, large jigsaw. Most of the jigsaw games out there right now 
only allow a rather limited number of pieces (typically less than 1000), and 
don't provide user controls for making the gameplay feel like a real jigsaw. 
When building a real, large puzzle, you typically start by sorting the pieces 
into different categories - blue pieces, red pieces, edge pieces etc. Doing 
this by dragging pieces one by one into different parts of the screen is 
extremely tiresome and quite unlike what you would do in real life. In this 
game, you can instead move pieces into "trays", which can be hidden from view, 
allowing you to quickly and easily sorting the pieces in any way you like. 

The main selling points of this game, therefore, are that it performs well even 
for very large puzzles (thousands of pieces), and that you can move your pieces 
into different trays. You can also zoom and pan the view as much as you like, 
as well as arrange the pieces into grids automatically. More is planned, but 
in my experience, these features alone are enough to set this game apart from 
the plethora of jigsaw games out there.  

The game is of course still in early development, much of the user interface is 
ugly and/or minimalistic, and there are still some critical features missing, 
like saving/loading games and allowing piece rotation. More advanced 
"gamification" features are planned too, but not until the basics are done as 
outlined below.  

## Implemented features
* Good performance with large number of pieces (can easily handle 10000 pieces
 or more)
* Unlimited surface area to build on
* Pan with wasd keys
* Zoom with mouse scroll wheel
* Select multiple pieces by holding shift and dragging
* Piecese "snap" together when close to a neighbour
* Organize pieces into "trays": clicking a piece while a number key is pressed will move that piece to the corresponding tray. Pressing ctrl+number key will toggle the visibility of all the pieces in the corresponding tray. Hidden pieces can't be interacted with.
* Spacebar will organize all selected "single" pieces into a "grid"
* Ctrl+r to create a new game. Select any jpg or png image from your computer to use as jigsaw image. You can select the number of pieces to use in the dialog box. 
* Cheat-buttons for debugging: c will connect two random pieces, x will connect 100 random pieces.
* Save game with F5
* Load the most recently saved game with F9

## Planned features
* Better saving/loading (specify which file to load, and name of the save file)
* Piece rotation - allowing pieces to be rotated.
* Timer, pause button, progress bar, victory screen
* Image preview
* Background image
* Tray visualization, visibility indicator
* Nice(r) user interface
* Better looking pieces
* Select images directly from pixabay or other image database
* Random image
* Loading screen
* Game stats, highscore, predicted time to complete, number of clicks needed, etc.

## Installation instructions
Tested on Windows 10. 
1. Download and install anaconda, if you don't have it already.
1. Clone this project
1. Create new conda environment: ```conda env create```
1. Activate conda environment: ```conda activate pygsaw```
1. Install the development version of pyglet: ```pip install --upgrade --user https://github.com/pyglet/pyglet/archive/master.zip```
1. Run the tests to verify that everything is working: ```pytest```
1. Run game: ```python -m game```