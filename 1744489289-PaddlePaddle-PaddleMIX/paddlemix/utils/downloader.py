# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import json
import os
import os.path as osp
import shutil
import tarfile
import threading
import time
import uuid
import zipfile
from typing import Optional, Union

import requests
from filelock import FileLock
from huggingface_hub import get_hf_file_metadata, hf_hub_url
from huggingface_hub.utils import EntryNotFoundError
from tqdm.auto import tqdm

from .env import (
    DOWNLOAD_SERVER,
    FAILED_STATUS,
    HF_CACHE_HOME,
    MODEL_HOME,
    SUCCESS_STATUS,
)
from .log import logger

__all__ = ["get_weights_path_from_url", "resolve_cache_dir"]

COMMUNITY_MODEL_PREFIX = os.getenv("COMMUNITY_MODEL_PREFIX", "https://bj.bcebos.com/paddlenlp/models/community")
WEIGHTS_HOME = osp.expanduser("~/.cache/paddle/hapi/weights")
DOWNLOAD_RETRY_LIMIT = 3
DOWNLOAD_CHECK = False


def is_url(path):
    """
    Whether path is URL.
    Args:
        path (string): URL string or not.
    """
    return path.startswith("http://") or path.startswith("https://")


def get_weights_path_from_url(url, md5sum=None):
    """Get weights path from WEIGHT_HOME, if not exists,
    download it from url.
    Args:
        url (str): download url
        md5sum (str): md5 sum of download package

    Returns:
        str: a local path to save downloaded weights.
    Examples:
        .. code-block:: python
            from paddle.utils.download import get_weights_path_from_url
            resnet18_pretrained_weight_url = 'https://paddle-hapi.bj.bcebos.com/models/resnet18.pdparams'
            local_weight_path = get_weights_path_from_url(resnet18_pretrained_weight_url)
    """
    path = get_path_from_url(url, WEIGHTS_HOME, md5sum)
    return path


def _map_path(url, root_dir):
    # parse path after download under root_dir
    fname = osp.split(url)[-1]
    fpath = fname
    return osp.join(root_dir, fpath)


def get_path_from_url(url, root_dir, md5sum=None, check_exist=True):
    """Download from given url to root_dir.
    if file or directory specified by url is exists under
    root_dir, return the path directly, otherwise download
    from url and decompress it, return the path.
    Args:
        url (str): download url
        root_dir (str): root dir for downloading, it should be
                        WEIGHTS_HOME or DATASET_HOME
        md5sum (str): md5 sum of download package

    Returns:
        str: a local path to save downloaded models & weights & datasets.
    """

    assert is_url(url), "downloading from {} not a url".format(url)
    # parse path after download to decompress under root_dir
    fullpath = _map_path(url, root_dir)

    if osp.exists(fullpath) and check_exist and _md5check(fullpath, md5sum):
        logger.info("Found {}".format(fullpath))
    else:
        fullpath = _download(url, root_dir, md5sum)

    if tarfile.is_tarfile(fullpath) or zipfile.is_zipfile(fullpath):
        fullpath = _decompress(fullpath)

    # model tokenizer config, [file-lock]
    return fullpath


def get_path_from_url_with_filelock(
    url: str,
    root_dir: str,
    md5sum: Optional[str] = None,
    check_exist: bool = True,
    timeout: float = -1,
) -> str:
    """construct `get_path_from_url` for `model_utils` to enable downloading multiprocess-safe

    Args:
        url (str): the url of resource file
        root_dir (str): the local download path
        md5sum (str, optional): md5sum string for file. Defaults to None.
        check_exist (bool, optional): whether check the file is exist. Defaults to True.
        timeout (int, optional): the timeout for downloading. Defaults to -1.

    Returns:
        str: the path of downloaded file
    """

    os.makedirs(root_dir, exist_ok=True)

    # create lock file, which is empty, under the `LOCK_FILE_HOME` directory.
    lock_file_name = hashlib.md5((url + root_dir).encode("utf-8")).hexdigest()

    # create `.lock` private directory in the cache dir
    lock_file_path = os.path.join(root_dir, ".lock", lock_file_name)

    os.makedirs(os.path.dirname(lock_file_path), exist_ok=True)

    with FileLock(lock_file_path, timeout=timeout):
        result = get_path_from_url(url=url, root_dir=root_dir, md5sum=md5sum, check_exist=check_exist)
    return result


def _download(url, path, md5sum=None):
    """
    Download from url, save to path.
    url (str): download url
    path (str): download to given path
    """
    os.makedirs(path, exist_ok=True)

    fname = osp.split(url)[-1]
    fullname = osp.join(path, fname)
    retry_cnt = 0

    while not (osp.exists(fullname) and _md5check(fullname, md5sum)):
        if retry_cnt < DOWNLOAD_RETRY_LIMIT:
            retry_cnt += 1
        else:
            raise RuntimeError("Download from {} failed. " "Retry limit reached".format(url))

        logger.info("Downloading {} from {}".format(fname, url))

        req = requests.get(url, stream=True)
        if req.status_code != 200:
            raise RuntimeError("Downloading from {} failed with code " "{}!".format(url, req.status_code))

        # For protecting download interrupted, download to
        # tmp_fullname firstly, move tmp_fullname to fullname
        # after download finished
        tmp_fullname = fullname + "_tmp"
        total_size = req.headers.get("content-length")
        with open(tmp_fullname, "wb") as f:
            if total_size:
                with tqdm(total=int(total_size), unit="B", unit_scale=True, unit_divisor=1024) as pbar:
                    for chunk in req.iter_content(chunk_size=1024):
                        f.write(chunk)
                        pbar.update(len(chunk))
            else:
                for chunk in req.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        shutil.move(tmp_fullname, fullname)

    return fullname


def _md5check(fullname, md5sum=None):
    if md5sum is None:
        return True

    logger.info("File {} md5 checking...".format(fullname))
    md5 = hashlib.md5()
    with open(fullname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    calc_md5sum = md5.hexdigest()

    if calc_md5sum != md5sum:
        logger.info("File {} md5 check failed, {}(calc) != " "{}(base)".format(fullname, calc_md5sum, md5sum))
        return False
    return True


def _md5(text):
    """
    Calculate the md5 value of the input text.
    """

    md5code = hashlib.md5(text.encode())
    return md5code.hexdigest()


def _decompress(fname):
    """
    Decompress for zip and tar file
    """
    logger.info("Decompressing {}...".format(fname))

    # For protecting decompressing interrupted,
    # decompress to fpath_tmp directory firstly, if decompress
    # successfully, move decompress files to fpath and delete
    # fpath_tmp and remove download compress file.

    if tarfile.is_tarfile(fname):
        uncompressed_path = _uncompress_file_tar(fname)
    elif zipfile.is_zipfile(fname):
        uncompressed_path = _uncompress_file_zip(fname)
    else:
        raise TypeError("Unsupported compress file type {}".format(fname))

    return uncompressed_path


def _uncompress_file_zip(filepath):
    files = zipfile.ZipFile(filepath, "r")
    file_list = files.namelist()

    file_dir = os.path.dirname(filepath)

    if _is_a_single_file(file_list):
        rootpath = file_list[0]
        uncompressed_path = os.path.join(file_dir, rootpath)

        for item in file_list:
            files.extract(item, file_dir)

    elif _is_a_single_dir(file_list):
        rootpath = os.path.splitext(file_list[0])[0].split(os.sep)[-1]
        uncompressed_path = os.path.join(file_dir, rootpath)

        for item in file_list:
            files.extract(item, file_dir)

    else:
        rootpath = os.path.splitext(filepath)[0].split(os.sep)[-1]
        uncompressed_path = os.path.join(file_dir, rootpath)
        if not os.path.exists(uncompressed_path):
            os.makedirs(uncompressed_path)
        for item in file_list:
            files.extract(item, os.path.join(file_dir, rootpath))

    files.close()

    return uncompressed_path


def _uncompress_file_tar(filepath, mode="r:*"):
    files = tarfile.open(filepath, mode)
    file_list = files.getnames()
    file_dir = os.path.dirname(filepath)

    if _is_a_single_file(file_list):
        rootpath = file_list[0]
        uncompressed_path = os.path.join(file_dir, rootpath)
        files.extractall(file_dir, files.getmembers())
    elif _is_a_single_dir(file_list):
        rootpath = os.path.splitext(file_list[0])[0].split(os.sep)[-1]
        uncompressed_path = os.path.join(file_dir, rootpath)
        files.extractall(file_dir, files.getmembers())
    else:
        rootpath = os.path.splitext(filepath)[0].split(os.sep)[-1]
        uncompressed_path = os.path.join(file_dir, rootpath)
        if not os.path.exists(uncompressed_path):
            os.makedirs(uncompressed_path)

        files.extractall(os.path.join(file_dir, rootpath), files.getmembers())

    files.close()

    return uncompressed_path


def _is_a_single_file(file_list):
    if len(file_list) == 1 and file_list[0].find(os.sep) < -1:
        return True
    return False


def _is_a_single_dir(file_list):
    new_file_list = []
    for file_path in file_list:
        if "/" in file_path:
            file_path = file_path.replace("/", os.sep)
        elif "\\" in file_path:
            file_path = file_path.replace("\\", os.sep)
        new_file_list.append(file_path)

    file_name = new_file_list[0].split(os.sep)[0]
    for i in range(1, len(new_file_list)):
        if file_name != new_file_list[i].split(os.sep)[0]:
            return False
    return True


class DownloaderCheck(threading.Thread):
    """
    Check the resource applicability  when downloading the models.
    """

    def __init__(self, task, command="taskflow", addition=None):
        threading.Thread.__init__(self)
        self.command = command
        self.task = task
        self.addition = addition
        self._initialize()

    def uri_path(self, server_url, api):
        srv = server_url
        if server_url.endswith("/"):
            srv = server_url[:-1]
        if api.startswith("/"):
            srv += api
        else:
            api = "/" + api
            srv += api
        return srv

    def _initialize(self):
        etime = str(int(time.time()))
        self.full_hash_flag = _md5(str(uuid.uuid1())[-12:])
        self.hash_flag = _md5(str(uuid.uuid1())[9:18]) + "-" + etime

    def request_check(self, task, command, addition):
        if task is None:
            return SUCCESS_STATUS
        payload = {"word": self.task}
        api_url = self.uri_path(DOWNLOAD_SERVER, "stat")
        cache_path = os.path.join("～")
        if os.path.exists(cache_path):
            extra = {
                "command": self.command,
                "mtime": os.stat(cache_path).st_mtime,
                "hub_name": self.hash_flag,
                "cache_info": self.full_hash_flag,
            }
        else:
            extra = {
                "command": self.command,
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "hub_name": self.hash_flag,
                "cache_info": self.full_hash_flag,
            }
        if addition is not None:
            extra.update({"addition": addition})
        try:
            import paddle
            import paddlenlp

            payload["hub_version"] = " "
            payload["ppnlp_version"] = paddlenlp.__version__
            payload["paddle_version"] = paddle.__version__.split("-")[0]
            payload["from"] = "ppnlp"
            payload["extra"] = json.dumps(extra)
            r = requests.get(api_url, payload, timeout=1).json()
            if r.get("update_cache", 0) == 1:
                return SUCCESS_STATUS
            else:
                return FAILED_STATUS
        except Exception:
            return FAILED_STATUS

    def run(self):
        self.request_check(self.task, self.command, self.addition)


def download_check(model_id, model_class, addition=None):
    logger.disable()
    global DOWNLOAD_CHECK
    if not DOWNLOAD_CHECK:
        DOWNLOAD_CHECK = True
        checker = DownloaderCheck(model_id, model_class, addition)
        checker.start()
        checker.join()
    logger.enable()


def url_file_exists(url: str) -> bool:
    """check whether the url file exists

        refer to: https://stackoverflow.com/questions/2486145/python-check-if-url-to-jpg-exists

    Args:
        url (str): the url of target file

    Returns:
        bool: whether the url file exists
    """
    if not is_url(url):
        return False

    result = requests.head(url)
    return result.status_code == requests.codes.ok


def hf_file_exists(
    repo_id: str,
    filename: str,
    token: Union[bool, str, None] = None,
    subfolder: Optional[str] = None,
) -> bool:
    """Check whether the HF file exists

    Args:
        repo_id (`str`): A namespace (user or an organization) name and a repo name separated by a `/`.
        filename (`str`): The name of the file in the repo.
        token (`str` or `bool`, *optional*): A token to be used for the download.
            - If `True`, the token is read from the HuggingFace config folder.
            - If `False` or `None`, no token is provided.
            - If a string, it's used as the authentication token.
        subfolder (str, optional) An optional value corresponding to a folder inside the repo.
    Returns:
        bool: whether the HF file exists
    """

    url = hf_hub_url(repo_id=repo_id, filename=filename, subfolder=subfolder)
    try:
        _ = get_hf_file_metadata(
            url=url,
            token=token,
        )
        return True
    except EntryNotFoundError:
        return False


def resolve_cache_dir(
    pretrained_model_name_or_path: str,
    from_hf_hub: bool,
    cache_dir: Optional[str] = None,
) -> str:
    """resolve cache dir for PretrainedModel and PretrainedConfig

    Args:
        pretrained_model_name_or_path (str): the name or path of pretrained model
        from_hf_hub (bool): if load from huggingface hub
        cache_dir (str): cache_dir for models
    """
    if os.path.isdir(pretrained_model_name_or_path):
        return pretrained_model_name_or_path

    # hf hub library takes care of appending the model name so we don't append the model name
    if from_hf_hub:
        if cache_dir is not None:
            return cache_dir
        else:
            return HF_CACHE_HOME
    else:
        if cache_dir is not None:
            # since model_clas.from_pretrained calls config_clas.from_pretrained, the model_name may get appended twice
            if cache_dir.endswith(pretrained_model_name_or_path):
                return cache_dir
            else:
                return os.path.join(cache_dir, pretrained_model_name_or_path)
        return os.path.join(MODEL_HOME, pretrained_model_name_or_path)
