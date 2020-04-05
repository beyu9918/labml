from typing import Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data
from torchvision import datasets, transforms

from lab import logger, configs
from lab import training_loop
from lab.experiment.pytorch import Experiment
from lab.logger.indicators import Queue, Histogram, IndexedScalar
from lab.logger.util import pytorch as logger_util


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(4 * 4 * 50, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4 * 4 * 50)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


class MNIST:
    def __init__(self, c: 'Configs'):
        self.model = c.model
        self.device = c.device
        self.train_loader = c.train_loader
        self.test_loader = c.test_loader
        self.optimizer = c.optimizer
        self.train_log_interval = c.train_log_interval
        self.loop = c.training_loop
        self.__is_log_parameters = c.is_log_parameters

    def _train(self):
        self.model.train()
        for i, (data, target) in logger.enum("Train", self.train_loader):
            data, target = data.to(self.device), target.to(self.device)

            self.optimizer.zero_grad()
            output = self.model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            self.optimizer.step()

            # Add training loss to the logger.
            # The logger will queue the values and output the mean
            logger.store(train_loss=loss)
            logger.add_global_step()

            # Print output to the console
            if i % self.train_log_interval == 0:
                # Output the indicators
                logger.write()

    def _test(self):
        self.model.eval()
        test_loss = 0
        correct = 0
        with torch.no_grad():
            idx = 0
            for data, target in logger.iterate("Test", self.test_loader):
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = F.nll_loss(output, target, reduction='none')
                indexes = [idx + i for i in range(self.test_loader.batch_size)]
                values = list(loss.cpu().numpy())
                logger.store('test_sample_loss', (indexes, values))

                test_loss += float(np.sum(loss.cpu().numpy()))
                pred = output.argmax(dim=1, keepdim=True)
                values = list(pred.cpu().numpy())
                logger.store('test_sample_pred', (indexes, values))
                correct += pred.eq(target.view_as(pred)).sum().item()

                idx += self.test_loader.batch_size

        # Add test loss and accuracy to logger
        logger.store(test_loss=test_loss / len(self.test_loader.dataset))
        logger.store(accuracy=correct / len(self.test_loader.dataset))

    def __log_model_params(self):
        if not self.__is_log_parameters:
            return

        # Add histograms with model parameter values and gradients
        logger_util.store_model_indicators(self.model)

    def __call__(self):
        # Training and testing
        logger_util.add_model_indicators(self.model)

        logger.add_indicator(Queue("train_loss", 20, True))
        logger.add_indicator(Histogram("test_loss", True))
        logger.add_indicator(Histogram("accuracy", True))
        logger.add_indicator(IndexedScalar('test_sample_loss'))
        logger.add_indicator(IndexedScalar('test_sample_pred'))

        test_data = np.array([d[0].numpy() for d in self.test_loader.dataset])
        logger.save_numpy("test_data", test_data)

        for _ in self.loop:
            self._train()
            self._test()
            self.__log_model_params()


class LoaderConfigs(configs.Configs):
    train_loader: torch.utils.data.DataLoader
    test_loader: torch.utils.data.DataLoader


class Configs(training_loop.TrainingLoopConfigs, LoaderConfigs):
    epochs: int = 10

    loop_step = None
    loop_count = None

    is_save_models = True
    batch_size: int = 64
    test_batch_size: int = 1000

    # Reset epochs so that it'll be computed
    use_cuda: float = True
    cuda_device: int = 0
    seed: int = 5
    train_log_interval: int = 10

    is_log_parameters: bool = True

    main: MNIST

    device: any

    model: nn.Module

    learning_rate: float = 0.01
    momentum: float = 0.5
    optimizer: optim.SGD

    set_seed = None


# Get dependencies from parameters.
# The code looks cleaner, but might cause problems when you want to refactor
# later.
# It will be harder to use static analysis tools to find the usage of configs.
@Configs.calc()
def device(*, use_cuda, cuda_device):
    from lab.util.pytorch import get_device

    return get_device(use_cuda, cuda_device)


def _data_loader(is_train, batch_size):
    return torch.utils.data.DataLoader(
        datasets.MNIST(str(logger.get_data_path()),
                       train=is_train,
                       download=True,
                       transform=transforms.Compose([
                           transforms.ToTensor(),
                           transforms.Normalize((0.1307,), (0.3081,))
                       ])),
        batch_size=batch_size, shuffle=True)


# Multiple configs can be computed from a single function
@Configs.calc(['train_loader', 'test_loader'])
def data_loaders(c: Configs):
    train = _data_loader(True, c.batch_size)
    test = _data_loader(False, c.test_batch_size)

    return train, test


# Compute multiple results from a single function
@Configs.calc()
def model(c: Configs):
    m: Net = Net()
    m.to(c.device)
    return m


# Multiple options for configs can be provided. Option name is inferred from function name,
# unless explicitly provided
@Configs.calc('optimizer')
def sgd_optimizer(c: Configs):
    return optim.SGD(c.model.parameters(), lr=c.learning_rate, momentum=c.momentum)


@Configs.calc('optimizer')
def adam_optimizer(c: Configs):
    return optim.Adam(c.model.parameters(), lr=c.learning_rate)


# Returns nothing
@Configs.calc()
def set_seed(c: Configs):
    torch.manual_seed(c.seed)


@Configs.calc()
def loop_count(c: Configs):
    return c.epochs * len(c.train_loader)


@Configs.calc()
def loop_step(c: Configs):
    return len(c.train_loader)


def main():
    conf = Configs()
    experiment = Experiment(writers={'sqlite'})
    experiment.calc_configs(conf,
                            {'optimizer': 'sgd_optimizer'},
                            ['set_seed', 'main'])
    experiment.add_models(dict(model=conf.model))
    experiment.start()
    conf.main()


if __name__ == '__main__':
    main()
