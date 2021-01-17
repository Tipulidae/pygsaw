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
* Practially unlimited surface area to build on
* Panning and zooming the view
* Selection box to select and move multiple pieces at once
* Pieces snap together when close to a neighbour
* Organize pieces into "trays": clicking a piece while a number key is pressed will move that piece to the corresponding tray. Pressing ctrl+number key will toggle the visibility of all the pieces in the corresponding tray. Hidden pieces can't be interacted with.
* Can organize all selected "single" pieces into a nice grid
* Select custom image or random image from folder
* Select any jigsaw size you want
* Customizeable background image - add your own images to the resources/textures folder
* Print progress (time elapsed and percent completed)
* Pause game (this will hide all pieces and stop the timer)
* Saving and loading (although at the moment you can only load the most recently saved game. To load another game you would have to move or delete any more recent saves.)
* Records statistics of finished game in a local database
* Cheat function to automatically connect random pieces
* Piece rotation - allowing pieces to be rotated.

## Planned features
* Better saving/loading (specify which file to load, and name of the save file)
* Configurable keybindings
* Image preview
* Game box: all pieces start in the box, and you start by taking pieces, a handful at a time, from the box.
* Automatic sorting, at first for finding the edge-pieces, later maybe more advanced
* Game stats, highscore, predicted time to complete, etc.
* Nicer background, with optional outline for the finished puzzle
* Tray visualization, visibility indicator
* Sticky trays or trays that behave more like actual trays
* Select images directly from pixabay or other image database, including choosing a random image
* Loading screen
* Improved interface in general (graphics, menus, etc)
* Better looking pieces


## Keybindings (hardcoded for now)
* Select piece: LEFT MOUSE BUTTON
* Selection box: SHIFT+LEFT MOUSE BUTTON, drag to create selection box
* Unselect piece(s): ESCAPE
* Move selected pieces: Click and drag
* Zoom in/out: CTRL + SCROLL UP/DOWN
* Rotate piece: SCROLL UP/DOWN
* Pan up: W
* Pan left: A
* Pan down: S
* Pan right: D
* Arrange selected pieces in a grid: SPACEBAR
* Move selected pieces to tray {0-9}: {0-9} keys
* Move piece to tray {0-9}: Click on piece while pressing {0-9} key
* Toggle visibility of all pieces in tray {0-9}: CTRL+{0-9} 
* Open dialog for new game: CTRL+R
* Save game: F5
* Load most recently saved game: F9
* Pause/unpause game: PAUSE
* Show progress: PERIOD (.)
* Toggle piece edges: COMMA (,)
* Toggle background image: T (you can put your own image in resources/background_images)
* Connect two random pieces (cheat): C
* Connect 100 random pieces (cheat): X

## Installation instructions
Tested on Windows 10. 
1. Download and install anaconda, if you don't have it already.
1. Clone this project
1. Create new conda environment: ```conda env create```
1. Activate conda environment: ```conda activate pygsaw```
1. Install the development version of pyglet: ```pip install --upgrade --user https://github.com/pyglet/pyglet/archive/master.zip```
1. Run the tests to verify that everything is working: ```pytest```
1. Run game: ```python -m game```