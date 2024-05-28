import torch

from ultralytics import YOLO

"""Using cuda requires a minimum of 8gb VRAM and more than 200gb of free space
while training so that wasn't possible to accomplish so i just ended up
using my CPU """

# Assuming you have a pre-trained yolov8n.pt model
model = YOLO("yolov8n.pt")  # Load the pre-trained model

# since my GPU doesn't meet the requirement for traning
# Check available device and create a device object
device = torch.device("cpu")  # Explicitly set CPU device

# Transfer the model to the chosen device (redundant in this case)
model.to(device)

# Train the model
model.train(data="config.yaml", epochs=50)
""" in the config.yaml You can using any dataset you have just specify the training data path as shown  in
 the config.yaml section and you need to have a label file(annotations) in both the train and val directories
 You can also specify your classes based on the annotations you have 
 eg 
 names:
 0: legs
 1: arms"""

