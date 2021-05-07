import torch.nn as nn
from layers.diversification_block import DiversificationBlock
from utils.util import get_object_from_path


class FGVCResnet(nn.Module):
    """
    The class implements the fine-grained classification model introduced in
    "Fine-grained Recognition: Accounting for Subtle Differences between Similar Classes".
    (http://arxiv.org/abs/1912.06842).
    """
    def __init__(self, config):
        """
        Constructor, the function initializes the model parameters by reading from the config.

        :param config: Configuration class object
        """
        super(FGVCResnet, self).__init__()  # Call the constructor of the parent class
        # Parse the configuration parameters
        self.model_function = get_object_from_path(config.cfg["model"]["model_function_path"])  # Model type
        self.pretrained = config.cfg["model"]["pretrained"]  # Either to load weights from pretrained model or not
        self.num_classes = config.cfg["model"]["classes_count"]  # Number of classes
        self.kernel_size = config.cfg["diversification_block"]["patch_size"]  # Patch size to be suppressed
        self.alpha = config.cfg["diversification_block"]["alpha"]  # Suppression factor
        self.p_peak = config.cfg["diversification_block"]["p_peak"]  # Probability for peak selection
        self.p_patch = config.cfg["diversification_block"]["p_patch"]  # Probability for patch selection
        self.cam = CAM(self.model_function, self.num_classes, self.pretrained)  # Initialize the CAM module
        # Initialize the diversification block (DB) module
        self.diversification_block = DiversificationBlock(self.kernel_size, self.alpha, self.p_peak, self.p_patch)

    def forward(self, x, train=False):
        """
        The function implements the forward pass of the model.

        :param x: Input image tensor
        :param train: Flag to specify either train or test mode
        """
        out = self.cam(x)  # Calculate the CAMs
        if train:
            # Diversification block is only used during training
            out = self.diversification_block(out)
        # Apply global average pooling to calculate the class probabilities
        out = out.mean([2, 3])

        return out


class CAM(nn.Module):
    """
    The class implements the class activation maps (CAMs) calculation logic introduced in
    "Fine-grained Recognition: Accounting for Subtle Differences between Similar Classes".
    (http://arxiv.org/abs/1912.06842).
    """
    def __init__(self, model_function, num_classes, pretrained=True):
        """
        Constructor, the function initializes the model as per the provided parameters.

        :param model_function: The backbone path to use for the model (e.g. torchvision.models.resnet50)
        :param num_classes: Number of classes for the classification head
        :param pretrained: Either to load weights from torchvision ImageNet pretrained model or not
        """
        # Call the parent constructor
        super(CAM, self).__init__()
        # Load the specified model
        net = model_function(pretrained=pretrained)
        net_list = list(net.children())
        # Separate out the feature extractor
        self.feature_extractor = nn.Sequential(*net_list[:-2])
        # 1 x 1 convolution with out_channels equal to number of classes to get CAMS as suggested in
        # (http://arxiv.org/abs/1912.06842)
        self.conv = nn.Conv2d(in_channels=2048, out_channels=num_classes, kernel_size=1)

    def forward(self, x):
        """
        The function implements the forward pass of the model.

        :param x: Input image tensor
        """
        feature_map = self.feature_extractor(x)  # Extract features
        cams = self.conv(feature_map)  # Get CAMs

        return cams
