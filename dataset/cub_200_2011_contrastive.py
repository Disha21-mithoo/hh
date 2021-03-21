import os
import pandas as pd
from torchvision.datasets.folder import default_loader
from utils.util import download_file_from_google_drive
from torch.utils.data import Dataset
import tarfile


class Cub2002011Contrastive(Dataset):
    base_folder = 'CUB_200_2011/images'  # Base dataset path
    google_drive_id = '1ZzCyTEYBOGDlHzcKCJqKzHX4SlJFUVEz'  # Google drive ID to download the dataset
    filename = 'CUB_200_2011.tgz'  # Dataset TGZ file name

    def __init__(self, root, train=True, download=True, loader=default_loader, resize_dims=None, transform=None,
                 contrastive_transforms=None, train_data_fraction=1, test_data_fraction=1):
        """
        Initialize the class variables, download the dataset (if prompted to do so), verify the data presence,
        :param root: Dataset root path
        :param train: Train dataloader flag (True: Train Dataloader, False: Test Dataloader)
        :param download: Flag set to download the dataset
        :param loader: The data point loader function (By default a PyTorch default_loader(PIL loader) is used)
        :param resize_dims: Image resize dimensions
        """
        self.root = os.path.expanduser(root)
        self.train = train
        self.loader = loader
        self.resize_dims = resize_dims
        self.train_data_fraction = train_data_fraction
        self.test_data_fraction = test_data_fraction
        if download:
            self._download()

        if not self._check_integrity():
            raise RuntimeError('Dataset not found or corrupted.' +
                               ' You can use download=True to download it')
        self.transform = transform
        self.contrastive_transforms = contrastive_transforms

    def __sample_data_train(self, group):
        return pd.DataFrame(group.sample(n=int(len(group)*self.train_data_fraction)))

    def __sample_data_test(self, group):
        return pd.DataFrame(group.sample(n=int(len(group)*self.test_data_fraction)))

    def _load_metadata(self):
        """
        Load the metadata (image list, class list and train/test split) of the CUB_200_2011 dataset
        """
        images = pd.read_csv(os.path.join(self.root, 'CUB_200_2011', 'images.txt'), sep=' ',
                             names=['img_id', 'filepath'])
        image_class_labels = pd.read_csv(os.path.join(self.root, 'CUB_200_2011', 'image_class_labels.txt'),
                                         sep=' ', names=['img_id', 'target'])
        train_test_split = pd.read_csv(os.path.join(self.root, 'CUB_200_2011', 'train_test_split.txt'),
                                       sep=' ', names=['img_id', 'is_training_img'])

        data = images.merge(image_class_labels, on='img_id')
        self.data = data.merge(train_test_split, on='img_id')
        if self.train:
            self.data = self.data[self.data.is_training_img == 1]
            self.data = self.data.groupby('target').apply(self.__sample_data_train)
        else:
            self.data = self.data[self.data.is_training_img == 0]
            self.data = self.data.groupby('target').apply(self.__sample_data_test)

    def _check_integrity(self):
        """
        Verify if the dataset is present and loads accurately
        """
        try:
            self._load_metadata()
        except Exception:
            return False

        for index, row in self.data.iterrows():
            filepath = os.path.join(self.root, self.base_folder, row.filepath)
            if not os.path.isfile(filepath):
                print(filepath)
                return False
        return True

    def _download(self):
        """
        Download the CUB_200_2011 dataset if not downloaded already
        """
        # Check if the files are already downloaded
        if self._check_integrity():
            print("Files already downloaded and verified")
            return
        if not os.path.exists(self.root):
            os.makedirs(self.root)
        # Download the data if not downloaded already
        download_file_from_google_drive(self.google_drive_id, os.path.join(self.root, self.filename))
        # Extract the downloaded dataset
        with tarfile.open(os.path.join(self.root, self.filename), "r:gz") as tar:
            tar.extractall(path=self.root)

    def __len__(self):
        """
        The function overrides the __len__ method of Dataset class
        :return: Length of the CUB dataset (train/test)
        """
        return len(self.data)

    def __getitem__(self, idx):
        """
        The function overrides the __getitem__ method of the Dataset class
        :param idx: The index to fetch the data entry/sample
        :return: The image tensor and corresponding label
        """
        sample = self.data.iloc[idx]
        path = os.path.join(self.root, self.base_folder, sample.filepath)
        target = sample.target - 1  # Targets start at 1 by default, so shift to 0
        img = self.loader(path)  # Call the loader function to load the image
        # Resize the image if the resize dims are specified
        if self.resize_dims is not None:
            img = img.resize(self.resize_dims)
        # Apply the transforms if the transformations are specified
        o, t_1, t_2 = img, img, img
        if self.transform is not None:
            o = self.transform(img)
        if self.train:
            if self.contrastive_transforms is not None:
                t_1, t_2 = self.contrastive_transforms(img)
                # Return the original image tensor, transformed image tensors, and target/label corresponding to
                # original image
            return o, t_1, t_2, target
        else:
            # Return the original image and its corresponding labels
            return o, target
