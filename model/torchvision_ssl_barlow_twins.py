import torch.nn as nn
from utils.util import get_object_from_path
import torch


class TorchvisionSSLBarlowTwins(nn.Module):
    """
    This class inherits from nn.Module class
    """

    def __init__(self, config):
        """
        The function parse the config and initialize the layers of the corresponding model
        :param config: YML configuration file to parse the parameters from
        """
        super(TorchvisionSSLBarlowTwins, self).__init__()  # Call the constructor of the parent class
        # Parse the configuration parameters
        self.model_function = get_object_from_path(config.cfg["model"]["model_function_path"])  # Model type
        self.pretrained = config.cfg["model"]["pretrained"]  # Either to load weights from pretrained model or not
        self.num_classes_classification = config.cfg["model"]["classes_count"]  # No. of classes for classification
        # Initialize the sub modules
        self.feature_extractor = FeatureExtractor(model_function=self.model_function, pretrained=self.pretrained)
        self.classification_head = ClassifierHead(in_features=self.feature_extractor.model.fc.in_features,
                                                  classes=self.num_classes_classification)
        self.bt_head = BTHead(feature_extractor=self.feature_extractor)
        self.flatten = nn.Flatten()

    def forward(self, x, t_1=None, t_2=None, train=True):
        """
        The function implements the forward pass of the network/model
        :param t_2:
        :param t_1:
        :param train:
        :param x: Batch of inputs (images)
        :return:
        """

        # Perform original classification task
        features = self.feature_extractor(x)
        features = self.flatten(features)
        y_classification = self.classification_head(features)
        # Barlow twins
        if train:
            bt_loss = self.bt_head(t_1=t_1, t_2=t_2)
            return y_classification, bt_loss
        else:
            return y_classification


class BTHead(nn.Module):
    def __init__(self, feature_extractor):
        super(BTHead, self).__init__()
        self.feature_extractor = feature_extractor
        projector = "1024-512-128"
        sizes = [2048] + list(map(int, projector.split('-')))
        layers = []
        for i in range(len(sizes) - 2):
            layers.append(nn.Linear(sizes[i], sizes[i + 1], bias=False))
            layers.append(nn.BatchNorm1d(sizes[i + 1]))
            layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Linear(sizes[-2], sizes[-1], bias=False))
        self.projector = nn.Sequential(*layers)
        self.flatten = nn.Flatten()
        # Normalization layer for the representations z1 and z2
        self.bn = nn.BatchNorm1d(sizes[-1], affine=False)
        self.scale_loss = 1 / 32
        self.lambd = 3.9e-3

    def forward(self, t_1, t_2):
        z_1 = self.projector(self.flatten(self.feature_extractor(t_1)))
        z_2 = self.projector(self.flatten(self.feature_extractor(t_2)))
        c = self.bn(z_1).T @ self.bn(z_2)
        on_diag = torch.diagonal(c).add_(-1).pow_(2).sum().mul(self.scale_loss)
        off_diag = off_diagonal(c).pow_(2).sum().mul(self.scale_loss)
        bt_loss = on_diag + self.lambd * off_diag
        return bt_loss


class ClassifierHead(nn.Module):
    def __init__(self, in_features, classes):
        super(ClassifierHead, self).__init__()
        self.classification_head = nn.Linear(in_features=in_features,
                                             out_features=classes)

    def forward(self, x):
        out = self.classification_head(x)
        return out


class FeatureExtractor(nn.Module):
    def __init__(self, model_function, pretrained):
        super(FeatureExtractor, self).__init__()
        self.model = model_function(pretrained=pretrained)
        net_list = list(self.model.children())
        self.feature_extractor = nn.Sequential(*net_list[:-1])

    def forward(self, x):
        out = self.feature_extractor(x)
        return out


def off_diagonal(x):
    # return a flattened view of the off-diagonal elements of a square matrix
    n, m = x.shape
    assert n == m
    return x.flatten()[:-1].view(n - 1, n + 1)[:, 1:].flatten()
