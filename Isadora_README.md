# Sending Coordinates to Isadora via OSC 

## Setting Up Isadora: 

1. Open Isadora
2. Double click on the canvas/blank space. Type in 'OSC Multi Listener'. 
3. Set up two OSC Multi Listeners (I used one each for the x and one for the y coordinates of each keypoint).
4. Set the base channels to be 1 and 18 on the two multi-listeners. Also set the number of channels to be 17.
![alt text](image.png)
5. Click on Communications and then Stream Setup (or use ctrl+9). Select 'Open Sound Control' in the 'Stream Select' field. Also select the Auto-Detect Input box.
6. Channels can be added using '+' button on the bottom leeft corner. Add 34 channels (2 for each keypoint) and number them from 1-34. Less channels can be used if only a few keypoints are to be detected.
7. Enter '/isadora-multi/1' in the stream address field for the first 17 channels and '/isadora-multi/2' for the next 17 channels in order. 
![alt text](image-1.png)
8. Once all the stream addresses have been set up, click OK.
9. Run the program as you normally would. All x coordinates are sent to OSC Multi Listener 1 and all y coordinates are sent to OSC Multi Listener 2.