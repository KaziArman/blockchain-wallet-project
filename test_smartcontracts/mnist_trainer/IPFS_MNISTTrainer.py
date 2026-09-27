import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, RandomSampler
import numpy as np
import pickle
from web3 import Web3

#hyperparameters
INPUT_SIZE = 28 * 28
HIDDEN_SIZES = [256, 128]
OUTPUT_SIZE = 10
BATCH_SIZE = 512
EPOCHS = 5
LEARNING_RATE = 0.001
DEVICE = "cpu"

#MNIST Trainer using simple Feed forward Deep Neural Network.
class DNN(nn.Module):
    def __init__(self):
        super(DNN, self).__init__()
        self.model = nn.Sequential(
            nn.Flatten(),
            nn.Linear(INPUT_SIZE, HIDDEN_SIZES[0]),
            nn.ReLU(),
            nn.Linear(HIDDEN_SIZES[0], HIDDEN_SIZES[1]),
            nn.ReLU(),
            nn.Linear(HIDDEN_SIZES[1], OUTPUT_SIZE)
        )

    def forward(self, x):
        return self.model(x)

class IPFS_MNISTTrainer:
    def __init__(self):
        # standardized train and test data loaders
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
        ])

        dataset = datasets.MNIST(root='./data', train=True, download=True, transform=self.transform)
        sampler = RandomSampler(dataset, replacement=True, num_samples=10)  # sample 1000 random examples
        self.train_loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler)

        self.test_loader = DataLoader(
            datasets.MNIST(root='./data', train=False, download=True, transform=self.transform),
            batch_size=BATCH_SIZE, shuffle=False
        )

        self.model = DNN().to(DEVICE)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)

        self.private_key = "0x74d507033d2c0f22b34c42ea1bf2d4f86c7f2061e19984a824d95603641a2907"
        self.public_key = Web3.to_checksum_address("0x94b7c73603c2468e23fc83f9d9aa25981ae4e193")

    def pushToIPFS_WithSC(self,model,public_key):
        weight_str = self.dump_weights_to_string(model)
        #TODO: dump weight_str to IPFS
        #TODO: extract CID for weight_str
        #TODO: update CID on SC using public_key
        pass

    def pullFromIPFS_WithSC(self,model,public_key):
        #TODO: using public_key, locate CID on SC
        #TODO: extract the weight_str using CID from IPFS
        #TODO: load weight_str to model using self.load_weights_from_string(model, weight_str)
        pass

    #Serialize weights to string using picke.dumps
    def dump_weights_to_string(self,model):
        numpy_weights = {k: v.cpu().numpy() for k, v in model.state_dict().items()}

        # this simply returns a serialized string of weights
        return pickle.dumps(numpy_weights)

    #Deserialize weights from string using picke.laods
    def load_weights_from_string(self,model, weight_str):
        # consumes a serialized weight string as input
        numpy_weights = pickle.loads(weight_str)

        # extracts the weights
        torch_weights = {k: torch.tensor(v) for k, v in numpy_weights.items()}

        #applies the weights for the model
        model.load_state_dict(torch_weights)

    #training function by EPOCHS for BATCH SIZE
    def train(self):
        model = self.model
        criterion = self.criterion
        optimizer = self.optimizer
        for epoch in range(EPOCHS):

            #load weights from IPFS for every epoch
            print(f"load weights from epoch {epoch}")
            #self.pullFromIPFS_WithSC(model, self.public_key)

            total_loss = 0
            for images, labels in self.train_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)

                outputs = model(images)
                loss = criterion(outputs, labels)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            print(f"Epoch {epoch}, Loss: {total_loss:.4f}")

            #self.pushToIPFS_WithSC(model,self.public_key)


    #to test the output
    def test(self):
        model = self.model
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in self.test_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        print(f"Accuracy: {100 * correct / total:.2f}%")

#main function
if __name__ == "__main__":

    mnist_trainer = IPFS_MNISTTrainer()
    mnist_trainer.train()

    #optional: if you want to test the model accuracy, (not required for assignment purposes.)
    #test(model)
