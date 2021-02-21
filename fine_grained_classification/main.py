import sys
import os

# Add the root folder (Visitor Tracking Utils) as the path to modules.
sys.path.append(f"{'/'.join(os.getcwd().split('/')[:-1])}")

from fine_grained_classification.config.config import Configuration as config
from fine_grained_classification.dataloader.common import Dataloader
from fine_grained_classification.model.common import Model
from fine_grained_classification.train.common import Trainer

if __name__ == "__main__":
    config.load_config("./config.yml")
    # Create the dataloaders
    dataloader = Dataloader(config=config)
    train_loader, test_loader = dataloader.get_loader()
    # Create the model
    model = Model(config=config).get_model()
    # Create the trainer
    trainer = Trainer(config=config, model=model, dataloader=train_loader, val_dataloader=test_loader).get_trainer()
    trainer.train_and_validate()
