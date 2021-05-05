from importlib import import_module
import requests
from utils import rotation_utils as rot_utils
import torch
import random
import logging

logger = logging.getLogger(f"utils/util.py")


def get_object_from_path(path):
    """
    The function returns the callable function from the path.

    :param path: Path to the function (string)
    :return: Callable instance corresponding to the path
    """
    assert type(path) is str
    mod_path = '.'.join(path.split('.')[:-1])
    object_name = path.split('.')[-1]
    mod = import_module(mod_path)
    target_obj = getattr(mod, object_name)
    return target_obj


def download_file_from_google_drive(id, destination):
    """
    The function downloads the specified file from the google drive.

    :param id: Unique google drive token for the file to download
    :param destination: Destination path
    """
    print(f"Downloading CUB-200-2011 dataset. It may take a while. Thank you for your patience.")

    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params={'id': id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {'id': id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    """
    The helper function for download_file_from_google_drive()
    """
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def save_response_content(response, destination):
    """
    The helper function for download_file_from_google_drive()
    """
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


def preprocess_input_data_rotation(images, labels, rotation=True):
    """
    The function preprocess a mini-batch of images and creates four rotated images along with the rotation labels.

    :param images: Batch of images
    :param labels: Original labels
    :param rotation: Flag to indicate if to apply the rotation or not.
    :return: Rotated images, original labels, rotation labels
    """
    if rotation:
        # Create the 4 rotated version of the images; this step increases
        # the batch size by a multiple of 4.
        batch_size_in = images.size(0)
        images = rot_utils.create_4rotations_images(images)
        labels_rotation = rot_utils.create_rotations_labels(batch_size_in, images.device)
        labels = labels.repeat(4)
    return images, labels, labels_rotation


def load_vissl_weights(model, checkpoints_path):
    """
    The function loads the VISSL (https://github.com/facebookresearch/vissl) weights.
    """
    checkpoint = torch.load(checkpoints_path)
    updated_checkpoints_dict = {}
    for key in checkpoint:
        updated_checkpoints_dict[f"model.{key}"] = checkpoint[key]
    status = model.load_state_dict(updated_checkpoints_dict, strict=False)
    logger.info(status)

    return model


def random_sample(img_names, labels):
    """
    The function randomly samples the images and corresponding labels.

    :param img_names: Images names
    :param labels: Corresponding labels
    :return: Randomly sampled image names and corresponding labels
    """
    ann_dict = {}
    img_list = []
    ann_list = []
    for img, ann in zip(img_names, labels):
        if ann not in ann_dict:
            ann_dict[ann] = [img]
        else:
            ann_dict[ann].append(img)
    for ann in ann_dict.keys():
        ann_len = len(ann_dict[ann])
        fetch_keys = random.sample(list(range(ann_len)), ann_len // 10)
        img_list.extend([ann_dict[ann][x] for x in fetch_keys])
        ann_list.extend([ann for x in fetch_keys])

    return img_list, ann_list


def get_image_crops(image, crop_size):
    """
    The function create crops of provided image of size specified by crop_size.

    :param image: Input image
    :param crop_size: Required crop size
    :return: List of image crops (each crop is of size 'crop_size')
    """
    width, high = image.size
    crop_x = [int((width / crop_size[0]) * i) for i in range(crop_size[0] + 1)]
    crop_y = [int((high / crop_size[1]) * i) for i in range(crop_size[1] + 1)]
    im_list = []
    for j in range(len(crop_y) - 1):
        for i in range(len(crop_x) - 1):
            im_list.append(image.crop((crop_x[i], crop_y[j], min(crop_x[i + 1], width), min(crop_y[j + 1], high))))
    return im_list


def save_model_checkpoints(checkpoints_dir_path, epoch, state_dict, metrics, last_best_accuracy):
    """
    The function saves the training checkpoints (both current and best).

    :param checkpoints_dir_path: Checkpoints directory path
    :param epoch: Current epoch
    :param state_dict: Model's state dict of parameters
    :param metrics: The metrics of the epoch
    :param last_best_accuracy: Last best accuracy
    :return: Current best accuracy
    """
    current_best_accuracy = last_best_accuracy  # Variable to keep track of the current best accuracy
    # Save the model checkpoints
    model_to_save = {
        "epoch": epoch,
        "metrics": metrics,
        'state_dict': state_dict,
    }
    torch.save(model_to_save,
               f"{checkpoints_dir_path}/epoch_{epoch}.pth")
    # Update the best checkpoints based on the accuracy
    if metrics["val"]["accuracy_top_1"] > last_best_accuracy:
        current_best_accuracy = metrics["val"]["accuracy_top_1"]  # Update the current best accuracy
        logger.info(f"New best model at epoch {epoch}.")  # New best model
        if checkpoints_dir_path:
            model_to_save = {
                "epoch": epoch,
                "metrics": metrics,
                'state_dict': state_dict,
            }
            torch.save(model_to_save,
                       f"{checkpoints_dir_path}/best_checkpoints.pth")

    return current_best_accuracy
