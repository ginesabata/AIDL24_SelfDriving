import torch
import logging
from utils import read_yaml
from utils import accuracy, save_model
import torch.nn.functional as F  # If required not use this black box, can create binary cross entropy in "utils"
import numpy as np
from torcheval.metrics.functional import binary_accuracy
import matplotlib.pyplot as plt
from logger import Logger

# Set up logging
logger = Logger()
logging.basicConfig(level=logging.INFO)

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
# Parameters to use
config_path = "configs/config.yaml"
config = read_yaml(config_path)

def eval_single_epoch(model, val_loader):
    accs, losses = [], []
    with torch.no_grad():
        model.eval()
        for x, y in val_loader:
            x, y = x.to(device), y.to(device)
            y_ = model(x)
            loss = F.cross_entropy(y_, y)
            acc = accuracy(y, y_)
            losses.append(loss.item())
            accs.append(acc.item())
    return np.mean(losses), np.mean(accs)

def eval_mask_rCNN(model, hparams, eval_loader, rois, device):

    model.to(device)  # Move model to device
    # Model in eval mode
    model.eval()

    # Initialize loss function
    criterion = F.binary_cross_entropy_with_logits

    # Initialize Parameters
    ev_loss, ev_acc = [], []
    for Image_cnt, (images, masks) in enumerate(eval_loader):
        logger.log_info(f"Processing image {Image_cnt+1}/{len(eval_loader)}")
        # Move data to device
        images, masks = images.to(device), masks.to(device)
        # Forward batch of images through the network
        output = model(images, rois)
        # Define the weights for the RGB to grayscale conversion
        weights = torch.tensor([0.2989, 0.5870, 0.1140], device=device).view(1, 3, 1, 1)
        # Apply the weights and sum across the channel dimension
        output = (output * weights).sum(dim=1, keepdim=True)
        # Reshape output & masks
        output = F.interpolate(output, size=hparams["target_size"], mode="bilinear", align_corners=False)
        output = output.reshape(-1).type(torch.float)
        masks = masks.reshape(-1).type(torch.float)  # Convert masks to float
        # Compute loss
        loss = criterion(output, masks)
        # Compute metrics
        acc = binary_accuracy(output, masks, threshold=0.5)
        # Add loss & acc to list
        ev_loss.append(loss.item())
        ev_acc.append(acc.item())
    
    # Plot loast & Accuracy
    plt.figure(figsize=(10, 8))
    plt.subplot(2, 1, 1)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.plot(ev_loss, label="loss eval")
    plt.legend()
    plt.subplot(2, 1, 2)
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy [%]")
    plt.plot(ev_acc, label="acc eval")
    plt.legend()
    plt.show()
    return np.mean(ev_loss), np.mean(ev_acc)