import torch
from fine_grained_classification.test.base_tester import Tester


class BaseTrainer:
    def __init__(self, model, dataloader, loss_function, optimizer, epochs,
                 lr_scheduler=None, val_dataloader=None, device="cuda", log_step=50):
        self.model = model
        self.dataloader = dataloader
        self.loss = loss_function()
        self.optimizer = optimizer
        self.epochs = epochs
        self.lr_scheduler = lr_scheduler
        self.device = device
        self.log_step = log_step
        self.validator = Tester(val_dataloader, self.loss) if val_dataloader else None
        self.metrics = {}

    def train_epoch(self, epoch):
        total_loss = 0
        total_predictions = 0
        total_correct_predictions = 0
        self.model.train()
        self.model = self.model.to(self.device)
        for batch_idx, d in enumerate(self.dataloader):
            inputs, labels = d
            inputs = inputs.to(self.device)
            labels = labels.to(self.device)
            outputs = self.model(inputs)
            loss = self.loss(outputs, labels)
            total_loss += loss
            _, preds = torch.max(outputs, 1)
            total_predictions += len(preds)
            total_correct_predictions += torch.sum(preds == labels.data)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            if (batch_idx % self.log_step == 0) and (batch_idx != 0):
                print(f"Train Epoch: {epoch}, Loss: {total_loss/batch_idx}")
        self.metrics[epoch] = {}
        self.metrics[epoch]["train"] = {}
        self.metrics[epoch]["train"]["loss"] = float(total_loss/batch_idx)
        self.metrics[epoch]["train"]["accuracy"] = float(total_correct_predictions) / float(total_predictions)
        print(f"Epoch {epoch} loss, accuracy: {self.metrics[epoch]['loss']}, {self.metrics[epoch]['accuracy']}")

    def train_and_validate(self):
        for i in range(self.epochs):
            self.train_epoch(i + 1)
            if self.validator:
                val_metrics = self.validator.test(self.model)
                self.metrics[i+1]["val"] = {}
                self.metrics[i+1]["val"] = val_metrics
            if self.lr_scheduler:
                self.lr_scheduler.step()
