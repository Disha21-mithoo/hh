import sys
from utils.utils import get_object_from_path
from torch.optim.lr_scheduler import StepLR as LRScheduler
import logging


logger = logging.getLogger(f"train/common.py")


class Trainer:
    """
    This class initiates the specified trainer object
    """

    def __init__(self, config, model, dataloader, val_dataloader=None, warm_up=False):
        # Initialize the selected trainer
        self.trainer = None
        # Select the correct model
        if config.cfg["train"]["name"] == "base_trainer":
            from train import BaseTrainer as Trainer
        else:
            logger.info(f"Please provide correct trainer to use in configuration. "
                        f"Available options are ['base_trainer']")
            sys.exit(1)
        self.trainer = self.__get_trainer(Trainer, config.cfg, model, dataloader, val_dataloader, warm_up)

    @staticmethod
    def __get_trainer(trainer_cls, config, model, dataloader, val_dataloader=None, warm_up=False):
        """
        Create and return the base trainer object
        """
        # Import the base trainer class
        # Parse the config
        if warm_up:
            loss_func = get_object_from_path(config["train"]["warm_up_loss_function_path"])
        else:
            loss_func = get_object_from_path(config["train"]["loss_function_path"])
        optimizer_func = get_object_from_path(config["train"]["optimizer_path"])
        optimizer_param = config["train"]["optimizer_param"]
        epochs = config["train"]["epochs"]
        output_directory = config["general"]["output_directory"]
        experiment_id = config["general"]["experiment_id"]
        model_checkpoints_directory_name = config["general"]["model_checkpoints_directory_name"]
        params = []
        for key, value in dict(model.named_parameters()).items():
            if value.requires_grad:
                params += [{'params': [value]}]
        optimizer = optimizer_func(params=params, lr=optimizer_param["lr"], momentum=optimizer_param["momentum"],
                                   weight_decay=optimizer_param["weight_decay"])
        lr_scheduler = LRScheduler(optimizer, step_size=config["train"]["lr_scheduler"]["step_size"],
                                   gamma=config["train"]["lr_scheduler"]["gamma"])
        # Create and return the trainer object
        return trainer_cls(model=model, dataloader=dataloader, loss_function=loss_func, optimizer=optimizer,
                           epochs=epochs, lr_scheduler=lr_scheduler, val_dataloader=val_dataloader,
                           checkpoints_dir_path=f"{output_directory}/{experiment_id}/"
                                                f"{model_checkpoints_directory_name}")

    def get_trainer(self):
        """
        This function returns the selected trainer
        """
        return self.trainer
