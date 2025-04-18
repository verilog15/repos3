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

import atexit
import inspect
import os
import time
import warnings
from collections import namedtuple
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import cv2
import datasets
import numpy as np
from multiprocess import Pool, RLock
from PIL import Image

import paddlemix

try:
    import paddle.distributed as dist
except Exception:
    warnings.warn("paddle.distributed is not contains in you paddle!")

import importlib
from functools import partial

from paddle.io import Dataset, IterableDataset
from paddle.utils.download import _get_unique_endpoints

from paddlemix.utils.env import DATA_HOME

__all__ = ["MapDataset", "DatasetBuilder", "IterDataset", "load_dataset", "MixDataset"]

DATASETS_MODULE_PATH = "paddlemix.datasets."

# Patch for intranet
from datasets import load_dataset as origin_load_dataset  # noqa: E402


def load_from_ppvlp(path, *args, **kwargs):
    ppvlp_path = paddlemix.datasets.__path__[0]
    new_path = os.path.split(path)[-1]
    new_path = os.path.join(ppvlp_path, "hf_datasets", new_path + ".py")
    if os.path.exists(new_path):
        return origin_load_dataset(new_path, *args, **kwargs)
    else:
        return origin_load_dataset(path, *args, **kwargs)


datasets.load_dataset = load_from_ppvlp


class DatasetTuple:
    def __init__(self, splits):
        self.identifier_map, identifiers = self._gen_identifier_map(splits)
        self.tuple_cls = namedtuple("datasets", identifiers)
        self.tuple = self.tuple_cls(*[None for _ in splits])

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self.tuple[key]
        if isinstance(key, str):
            return getattr(self.tuple, self.identifier_map[key])

    def __setitem__(self, key, value):
        self.tuple = self.tuple._replace(**{self.identifier_map[key]: value})

    def _gen_identifier_map(self, splits):
        identifier_map = {}
        identifiers = []
        for i in range(len(splits)):
            identifiers.append("splits_" + str(i))
            identifier_map[splits[i]] = "splits_" + str(i)
        return identifier_map, identifiers

    def __len__(self):
        return len(self.tuple)


def import_main_class(module_path):
    """
    Import a module at module_path and return its DatasetBuilder class.

    """
    module_path = DATASETS_MODULE_PATH + module_path
    module = importlib.import_module(module_path)
    main_cls_type = DatasetBuilder

    # Find the main class in our imported module
    module_main_cls = None
    for name, obj in module.__dict__.items():
        if isinstance(obj, type) and issubclass(obj, main_cls_type):
            if name == "DatasetBuilder":
                continue
            module_main_cls = obj
            break

    return module_main_cls


def load_from_hf(path, name=None, splits=None, **kwargs):
    from datasets import DatasetDict
    from datasets import load_dataset as load_hf_dataset
    from datasets.features import ClassLabel

    try:
        hf_datasets = load_hf_dataset(path, name=name, split=splits, **kwargs)
    except FileNotFoundError:
        raise FileNotFoundError("Couldn't find the dataset script for '" + path + "' on PaddleNLP or HuggingFace")
    else:
        label_list = []
        if isinstance(hf_datasets, DatasetDict):
            datasets = DatasetTuple(list(hf_datasets.keys()))
            for split, ds in hf_datasets.items():
                for feature in ds.features.values():
                    if isinstance(feature, ClassLabel):
                        label_list = feature.names
                datasets[split] = MapDataset(ds, label_list=label_list)
        elif isinstance(hf_datasets, list):
            datasets = DatasetTuple(splits)
            for i, split in enumerate(splits):
                for feature in hf_datasets[i].features.values():
                    if isinstance(feature, ClassLabel):
                        label_list = feature.names
                datasets[split] = MapDataset(hf_datasets[i], label_list=label_list)
        else:
            for feature in hf_datasets.features.values():
                if isinstance(feature, ClassLabel):
                    label_list = feature.names
            datasets = MapDataset(hf_datasets, label_list=label_list)
    return datasets


def load_dataset(path_or_read_func, name=None, data_files=None, splits=None, lazy=None, **kwargs):
    """
    This method will load a dataset, either form PaddleNLP library or from a
    self-defined data loading script, by calling functions in `DatasetBuilder`.

    For all the names of datasets in PaddleNLP library, see here:  `dataset_list
    <https://paddlenlp.readthedocs.io/zh/latest/data_prepare/dataset_list.html>`__.

    Either `splits` or `data_files` must be specified.

    Args:
        path_or_read_func (str|callable): Name of the dataset processing script
            in PaddleNLP library or a custom data reading function.
        name (str, optional): Additional name to select a more specific dataset.
            Defaults to None.
        data_files (str|list|tuple|dict, optional): Defining the path of dataset
            files. If None. `splits` must be specified. Defaults to None.
        splits (str|list|tuple, optional): Which split of the data to load. If None.
            `data_files` must be specified. Defaults to None.
        lazy (bool, optional): Weather to return `MapDataset` or an `IterDataset`.
            True for `IterDataset`. False for `MapDataset`. If None, return the
            default type of this dataset. Defaults to None.
        kwargs (dict): Other keyword arguments to be passed to the `DatasetBuilder`.

    Returns:
        A `MapDataset` or `IterDataset` or a tuple of those.

    For how to use this function, please see `dataset_load
    <https://paddlenlp.readthedocs.io/zh/latest/data_prepare/dataset_load.html>`__
    and `dataset_self_defined
    <https://paddlenlp.readthedocs.io/zh/latest/data_prepare/dataset_self_defined.html>`__

    """
    if inspect.isfunction(path_or_read_func):
        assert lazy is not None, "lazy can not be None in custom mode."
        kwargs["name"] = name
        kwargs["data_files"] = data_files
        kwargs["splits"] = splits
        custom_kwargs = {}
        for name in inspect.signature(path_or_read_func).parameters.keys():
            if name in kwargs.keys():
                custom_kwargs[name] = kwargs[name]

        reader_instance = SimpleBuilder(lazy=lazy, read_func=path_or_read_func)
        return reader_instance.read(**custom_kwargs)
    else:
        try:
            reader_cls = import_main_class(path_or_read_func)
        except ModuleNotFoundError:
            datasets = load_from_hf(path_or_read_func, name=name, splits=splits, **kwargs)
        else:
            reader_instance = reader_cls(lazy=lazy, name=name, **kwargs)
            # Check if selected name and split is valid in this DatasetBuilder
            if hasattr(reader_instance, "BUILDER_CONFIGS"):
                if name in reader_cls.BUILDER_CONFIGS.keys():
                    split_names = reader_cls.BUILDER_CONFIGS[name]["splits"].keys()
                else:
                    raise ValueError(
                        'Invalid name "{}". Should be one of {}.'.format(name, list(reader_cls.BUILDER_CONFIGS.keys()))
                    )
            elif hasattr(reader_instance, "SPLITS"):
                split_names = reader_instance.SPLITS.keys()
            else:
                raise AttributeError("Either 'SPLITS' or 'BUILDER_CONFIGS' must be implemented for DatasetBuilder.")

            selected_splits = []
            if isinstance(splits, list) or isinstance(splits, tuple):
                selected_splits.extend(splits)
            else:
                selected_splits += [splits]

            for split_name in selected_splits:
                if split_name not in split_names and split_name is not None:
                    raise ValueError('Invalid split "{}". Should be one of {}.'.format(split_name, list(split_names)))

            datasets = reader_instance.read_datasets(data_files=data_files, splits=splits)
        return datasets


class MapDataset(Dataset):
    """
    Wraps a map-style dataset-like object as an instance of `MapDataset`, and equips it
    with `map` and other utility methods. All non-magic methods of the raw object
    are also accessible.

    Args:
        data (list|Dataset): An object with `__getitem__` and `__len__` methods. It could
            be a list or a subclass of `paddle.io.Dataset`.
        kwargs (dict, optional): Other information to be passed to the dataset.

    For examples of this class, please see `dataset_self_defined
    <https://paddlenlp.readthedocs.io/zh/latest/data_prepare/dataset_self_defined.html>`__.

    """

    def __init__(self, data, **kwargs):
        self.data = data
        self._transform_pipeline = []
        self.new_data = self.data
        self.info = kwargs
        self.label_list = self.info.pop("label_list", None)
        self.vocab_info = self.info.pop("vocab_info", None)

    def _transform(self, data):
        for fn in self._transform_pipeline:
            data = fn(data)
        return data

    def __getitem__(self, idx):
        """
        Basic function of `MapDataset` to get sample from dataset with a given
        index.
        """
        return self._transform(self.new_data[idx]) if self._transform_pipeline else self.new_data[idx]

    def __len__(self):
        """
        Returns the number of samples in dataset.
        """
        return len(self.new_data)

    def filter(self, fn, num_workers=0):
        """
        Filters samples by the filter function and uses the filtered data to
        update this dataset.

        Args:
            fn (callable): A filter function that takes a sample as input and
                returns a boolean. Samples that return False would be discarded.
            num_workers(int, optional): Number of processes for multiprocessing. If
                set to 0, it doesn't use multiprocessing. Defaults to `0`.
        """
        assert num_workers >= 0, "num_workers should be a non-negative value"
        if num_workers > 1:
            shards = [
                self._shard(num_shards=num_workers, index=index, contiguous=True) for index in range(num_workers)
            ]
            kwds_per_shard = [dict(self=shards[rank], fn=fn) for rank in range(num_workers)]
            pool = Pool(num_workers, initargs=(RLock(),))

            results = [pool.apply_async(self.__class__._filter, kwds=kwds) for kwds in kwds_per_shard]
            transformed_shards = [r.get() for r in results]

            pool.close()
            pool.join()
            self.new_data = []
            for i in range(num_workers):
                self.new_data += transformed_shards[i].new_data
            return self
        else:
            return self._filter(fn)

    def _filter(self, fn):
        self.new_data = [self.new_data[idx] for idx in range(len(self.new_data)) if fn(self.new_data[idx])]
        return self

    def shard(self, num_shards=None, index=None, contiguous=False):
        self.new_data = self._shard(num_shards=num_shards, index=index, contiguous=contiguous).data
        return self

    def _shard(self, num_shards=None, index=None, contiguous=False):
        """
        Split the dataset into `num_shards` pieces. Note that the size of each
        shard might be different because the original dataset may not be evenly
        divisible.

        Args:
            num_shards (int, optional): An integer representing the number of
                data shards. If None, `num_shards` would be number of trainers.
                Defaults to `None`.
            index (int, optional): An integer representing the index of the
                current shard. If None, `index` would be the current trainer rank
                id. Defaults to `None`.
            contiguous: (bool, optional): If true, contiguous chunks of data
                will be select for sharding. And total number of examples will
                be the same. Otherwise each shard will contain all examples of
                dataset whose index mod `num_shards` = `index`. Defaults to `False`.
        """
        if num_shards is None:
            num_shards = dist.get_world_size()
        if index is None:
            index = dist.get_rank()

        if contiguous:
            div = len(self) // num_shards
            mod = len(self) % num_shards
            start = div * index + min(index, mod)
            end = start + div + (1 if index < mod else 0)
            new_data = [self.new_data[idx] for idx in range(start, end)]
        else:
            new_data = [self.new_data[idx] for idx in range(len(self.new_data)) if idx % num_shards == index]

        return MapDataset(new_data)

    def map(self, fn, lazy=True, batched=False, num_workers=0):
        """
        Performs specific function on the dataset to transform and update every sample.

        Args:
            fn (callable): Transformations to be performed. It receives single
                sample as argument if batched is False. Else it receives all examples.
            lazy (bool, optional): If True, transformations would be delayed and
                performed on demand. Otherwise, transforms all samples at once. Note that
                if `fn` is stochastic, `lazy` should be True or you will get the same
                result on all epochs. Defaults to False.
            batched(bool, optional): If True, transformations would take all examples as
                input and return a collection of transformed examples. Note that if set
                True, `lazy` option would be ignored. Defaults to False.
            num_workers(int, optional): Number of processes for multiprocessing. If
                set to 0, it doesn't use multiprocessing. Note that if set to positive
                value, `lazy` option would be ignored. Defaults to 0.
        """

        assert num_workers >= 0, "num_workers should be a non-negative value"
        if num_workers > 1:
            shards = [
                self._shard(num_shards=num_workers, index=index, contiguous=True) for index in range(num_workers)
            ]
            kwds_per_shard = [
                dict(self=shards[rank], fn=fn, lazy=False, batched=batched) for rank in range(num_workers)
            ]
            pool = Pool(num_workers, initargs=(RLock(),))
            results = [pool.apply_async(self.__class__._map, kwds=kwds) for kwds in kwds_per_shard]
            transformed_shards = [r.get() for r in results]
            pool.close()
            pool.join()
            self.new_data = []
            for i in range(num_workers):
                self.new_data += transformed_shards[i].new_data
            return self
        else:
            return self._map(fn, lazy=lazy, batched=batched)

    def _map(self, fn, lazy=True, batched=False):
        if batched:
            self.new_data = fn(self.new_data)
        elif lazy:
            self._transform_pipeline.append(fn)
        else:
            self.new_data = [fn(self.new_data[idx]) for idx in range(len(self.new_data))]
        return self


class IterDataset(IterableDataset):
    """
    Wraps a dataset-like object as an instance of `IterDataset`, and equips it with
    `map` and other utility methods. All non-magic methods of the raw object
    also accessible.

    Args:
        data (Iterable): An object with `__iter__` function. It can be a Iterable or a
            subclass of `paddle.io.IterableDataset`.
        kwargs (dict, optional): Other information to be passed to the dataset.

    For examples of this class, please see `dataset_self_defined
    <https://paddlenlp.readthedocs.io/zh/latest/data_prepare/dataset_self_defined.html>`__.
    """

    def __init__(self, data, **kwargs):
        self.data = data
        self._transform_pipeline = []
        self._filter_pipeline = []

        self.label_list = kwargs.pop("label_list", None)
        self.vocab_info = kwargs.pop("vocab_info", None)

    def _transform(self, data):
        for fn in self._transform_pipeline:
            data = fn(data)
        return data

    def _shard_filter(self, num_samples):
        return True

    def _filter(self, data):
        for fn in self._filter_pipeline:
            if not fn(data):
                return False
        return True

    def __iter__(self):
        """
        yields sample sequentially.
        """
        num_samples = 0
        if inspect.isfunction(self.data):
            for example in self.data():
                if (not self._filter_pipeline or self._filter(self._filter_pipeline)) and self._shard_filter(
                    num_samples=num_samples
                ):
                    yield self._transform(example) if self._transform_pipeline else example
                num_samples += 1
        else:
            if inspect.isgenerator(self.data):
                warnings.warn("Receiving generator as data source, data can only be iterated once")
            for example in self.data:
                if (not self._filter_pipeline or self._filter(self._filter_pipeline)) and self._shard_filter(
                    num_samples=num_samples
                ):
                    yield self._transform(example) if self._transform_pipeline else example
                num_samples += 1

    def filter(self, fn):
        """
        Filters samples by the filter function and uses the filtered data to
        update this dataset.

        Args:
            fn (callable): A filter function that takes a sample as input and
                returns a boolean. Samples that return False are discarded.
        """

        self._filter_pipeline.append(fn)

        return self

    def shard(self, num_shards=None, index=None):
        """
        Split the dataset into `num_shards` pieces.

        Args:
            num_shards (int, optional): An integer representing the number of
                data shards. If None, `num_shards` would be number of trainers.
                Defaults to None.
            index (int, optional): An integer representing the index of the
                current shard. If None, `index` would be the current trainer rank
                id. Defaults to None.
        """
        if num_shards is None:
            num_shards = dist.get_world_size()
        if index is None:
            index = dist.get_rank()

        def sharder(num_shards, index, num_samples):
            if num_samples % num_shards == index:
                return True
            else:
                return False

        fn = partial(sharder, num_shards=num_shards, index=index)
        self._shard_filter = fn
        return self

    def map(self, fn):
        """
        Performs specific function on the dataset to transform and update every sample.

        Args:
            fn (callable): Transformations to be performed. It receives single
                sample as argument.
        """

        self._transform_pipeline.append(fn)

        return self


class DatasetBuilder:
    """
    A base class for all DatasetBuilder. It provides a `read()` function to turn
    a data file into a MapDataset or IterDataset.

    `_get_data()` function and `_read()` function should be implemented to download
    data file and read data file into a `Iterable` of the examples.

    For how to define a custom `DatasetBuilder`, please see `contribute_dataset
    <https://paddlenlp.readthedocs.io/zh/latest/community/contribute_dataset.html>`__.
    """

    lazy = False

    def __init__(self, lazy=None, name=None, **config):
        if lazy is not None:
            self.lazy = lazy
        self.name = name
        self.config = config

    def read_datasets(self, splits=None, data_files=None):
        def remove_if_exit(filepath):
            if isinstance(filepath, (list, tuple)):
                for file in filepath:
                    try:
                        os.remove(file)
                    except OSError:
                        pass
            else:
                try:
                    os.remove(filepath)
                except OSError:
                    pass

        if data_files is None:
            if splits is None:
                splits = (
                    list(self.BUILDER_CONFIGS[self.name]["splits"].keys())
                    if hasattr(self, "BUILDER_CONFIGS")
                    else list(self.SPLITS.keys())
                )

            assert (
                isinstance(splits, str)
                or (isinstance(splits, list) and isinstance(splits[0], str))
                or (isinstance(splits, tuple) and isinstance(splits[0], str))
            ), "`splits` should be a string or list of string or a tuple of string."

            if isinstance(splits, str):
                splits = [splits]
            datasets = DatasetTuple(splits)
            parallel_env = dist.ParallelEnv()
            unique_endpoints = _get_unique_endpoints(parallel_env.trainer_endpoints[:])
            # move register hook to first and register together
            lock_files = []
            for split in splits:
                lock_file = os.path.join(DATA_HOME, self.__class__.__name__)
                if self.name is not None:
                    lock_file = lock_file + "." + self.name
                lock_file += "." + split + ".done" + "." + str(os.getppid())
                lock_files.append(lock_file)
            # Must register to all procs to make the lock file can be removed
            # when any proc breaks. Otherwise, the single registered proc may
            # not receive proper signal send by the parent proc to exit.
            atexit.register(lambda: remove_if_exit(lock_files))
            for split in splits:
                filename = self._get_data(split)
                lock_file = os.path.join(DATA_HOME, self.__class__.__name__)
                if self.name is not None:
                    lock_file = lock_file + "." + self.name
                lock_file += "." + split + ".done" + "." + str(os.getppid())
                # `lock_file` indicates the finished status of`_get_data`.
                # `_get_data` only works in the `unique_endpoints` specified
                # proc since `get_path_from_url` only work for it. The other
                # procs wait `_get_data` to be finished.
                if parallel_env.current_endpoint in unique_endpoints:
                    f = open(lock_file, "w")
                    f.close()
                else:
                    while not os.path.exists(lock_file):
                        time.sleep(1)
                datasets[split] = self.read(filename=filename, split=split)
        else:
            assert (
                isinstance(data_files, str) or isinstance(data_files, tuple) or isinstance(data_files, list)
            ), "`data_files` should be a string or tuple or list of strings."
            if isinstance(data_files, str):
                data_files = [data_files]
            default_split = "train"
            if splits:
                if isinstance(splits, str):
                    splits = [splits]
                datasets = DatasetTuple(splits)
                assert len(splits) == len(
                    data_files
                ), "Number of `splits` and number of `data_files` should be the same if you want to specify the split of local data file."
                for i in range(len(data_files)):
                    datasets[splits[i]] = self.read(filename=data_files[i], split=splits[i])
            else:
                datasets = DatasetTuple(["split" + str(i) for i in range(len(data_files))])
                for i in range(len(data_files)):
                    datasets["split" + str(i)] = self.read(filename=data_files[i], split=default_split)

        return datasets if len(datasets) > 1 else datasets[0]

    def read(self, filename, split="train"):
        """
        Returns a dataset containing all the examples that can be read from the file path.

        If `self.lazy` is False, this eagerly reads all instances from `self._read()`
        and returns a `MapDataset`.

        If `self.lazy` is True, this returns an `IterDataset`, which internally
        relies on the generator created from `self._read()` to lazily produce examples.
        In this case your implementation of `_read()` must also be lazy
        (that is, not load all examples into memory at once).

        Args:
            filename (str): Path of data file to read, usually provided by `_get_data`
                function.
            split (str, optional): The split name of selected dataset. This only makes
                a different when data files of different splits have different structures.

        Returns:
            A `MapDataset|IterDataset`.
        """

        label_list = self.get_labels()
        vocab_info = self.get_vocab()

        def _create_dict(labels):
            # For multiple labels in the form of list.
            if isinstance(labels[0], list) or isinstance(labels[0], tuple):
                label_dict = []
                for sub_labels in labels:
                    sub_dict = {}
                    for i, label in enumerate(sub_labels):
                        sub_dict[label] = i
                    label_dict.append(sub_dict)
            else:
                label_dict = {}
                for i, label in enumerate(labels):
                    label_dict[label] = i
            return label_dict

        def _convert_label_to_id(labels, label_dict):
            if isinstance(labels, list) or isinstance(labels, tuple):
                for label_idx in range(len(labels)):
                    labels[label_idx] = label_dict[labels[label_idx]]
            else:
                labels = label_dict[labels]
            return labels

        if self.lazy:

            def generate_examples():
                generator = (
                    self._read(filename, split) if self._read.__code__.co_argcount > 2 else self._read(filename)
                )
                for example in generator:
                    # We need to check if the example contains label column and confirm its name.
                    # For now we only allow `label` or `labels` to be the name of label column.
                    if "labels" in example.keys():
                        label_col = "labels"
                    elif "label" in example.keys():
                        label_col = "label"
                    else:
                        label_col = None

                    # Convert class label to label ids.
                    if label_list is not None and example.get(label_col, None):
                        label_dict = _create_dict(label_list)
                        # For multiple labels in the form of list.
                        if isinstance(label_dict, list):
                            for idx, sub_dict in enumerate(label_dict):
                                example[label_col][idx] = _convert_label_to_id(example[label_col][idx], sub_dict)
                        else:
                            example[label_col] = _convert_label_to_id(example[label_col], label_dict)

                        yield example
                    else:
                        yield example

            return IterDataset(generate_examples(), label_list=label_list, vocab_info=vocab_info)
        else:
            examples = self._read(filename, split) if self._read.__code__.co_argcount > 2 else self._read(filename)

            # Then some validation.
            if not isinstance(examples, list):
                examples = list(examples)

            if not examples:
                raise ValueError(
                    "No instances were read from the given filepath {}. " "Is the path correct?".format(filename)
                )

            # We need to check if the example contains label column and confirm its name.
            # For now we only allow `label` or `labels` to be the name of label column.
            if isinstance(examples[0], dict):
                if "labels" in examples[0].keys():
                    label_col = "labels"
                elif "label" in examples[0].keys():
                    label_col = "label"
                else:
                    label_col = None

            # Convert class label to label ids.
            if label_list is not None and examples[0].get(label_col, None):
                label_dict = _create_dict(label_list)
                for idx in range(len(examples)):
                    # For multiple labels in the form of list.
                    if isinstance(label_dict, list):
                        for i, sub_dict in enumerate(label_dict):
                            examples[idx][label_col][i] = _convert_label_to_id(examples[idx][label_col][i], sub_dict)
                    else:
                        examples[idx][label_col] = _convert_label_to_id(examples[idx][label_col], label_dict)

            return MapDataset(examples, label_list=label_list, vocab_info=vocab_info)

    def _read(self, filename: str, *args):
        """
        Reads examples from the given file_path and returns them as an
        `Iterable` (which could be a list or a generator).

        This method must be implemented in self-defined `DatasetBuilder`.
        """
        raise NotImplementedError

    def _get_data(self, mode: str):
        """
        Downloads examples from the given URL and customized split
        information and returns a filepath.

        This method must be implemented in self-defined `DatasetBuilder`.
        """
        raise NotImplementedError

    def get_labels(self):
        """
        Returns list of class labels of the dataset if specified.
        """
        return None

    def get_vocab(self):
        """
        Returns vocab file path of the dataset if specified.
        """
        return None


class SimpleBuilder(DatasetBuilder):
    def __init__(self, lazy, read_func):
        self._read = read_func
        self.lazy = lazy

    def read(self, **kwargs):
        if self.lazy:

            def generate_examples():
                generator = self._read(**kwargs)
                for example in generator:
                    yield example

            return IterDataset(generate_examples)
        else:
            examples = self._read(**kwargs)
            if hasattr(examples, "__len__") and hasattr(examples, "__getitem__"):
                return MapDataset(examples)
            else:
                return MapDataset(list(examples))


def has_file_allowed_extension(filename: str, extensions: Union[str, Tuple[str, ...]]) -> bool:
    """Checks if a file is an allowed extension.

    Args:
        filename (string): path to a file
        extensions (tuple of strings): extensions to consider (lowercase)

    Returns:
        bool: True if the filename ends with one of given extensions
    """
    return filename.lower().endswith(extensions if isinstance(extensions, str) else tuple(extensions))


def find_classes(directory: str) -> Tuple[List[str], Dict[str, int]]:
    """Finds the class folders in a dataset.

    See :class:`DatasetFolder` for details.
    """
    classes = sorted(entry.name for entry in os.scandir(directory) if entry.is_dir())
    if not classes:
        raise FileNotFoundError(f"Couldn't find any class folder in {directory}.")

    class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)}
    return classes, class_to_idx


def make_dataset(
    directory: str,
    class_to_idx: Optional[Dict[str, int]] = None,
    extensions: Optional[Union[str, Tuple[str, ...]]] = None,
    is_valid_file: Optional[Callable[[str], bool]] = None,
) -> List[Tuple[str, int]]:
    """Generates a list of samples of a form (path_to_sample, class).

    See :class:`DatasetFolder` for details.

    Note: The class_to_idx parameter is here optional and will use the logic of the ``find_classes`` function
    by default.
    """
    directory = os.path.expanduser(directory)

    if class_to_idx is None:
        _, class_to_idx = find_classes(directory)
    elif not class_to_idx:
        raise ValueError("'class_to_index' must have at least one entry to collect any samples.")

    both_none = extensions is None and is_valid_file is None
    both_something = extensions is not None and is_valid_file is not None
    if both_none or both_something:
        raise ValueError("Both extensions and is_valid_file cannot be None or not None at the same time")

    if extensions is not None:

        def is_valid_file(x: str) -> bool:
            return has_file_allowed_extension(x, extensions)  # type: ignore[arg-type]

    is_valid_file = cast(Callable[[str], bool], is_valid_file)

    instances = []
    available_classes = set()
    for target_class in sorted(class_to_idx.keys()):
        class_index = class_to_idx[target_class]
        target_dir = os.path.join(directory, target_class)
        if not os.path.isdir(target_dir):
            continue
        for root, _, fnames in sorted(os.walk(target_dir, followlinks=True)):
            for fname in sorted(fnames):
                path = os.path.join(root, fname)
                if is_valid_file(path):
                    item = path, class_index
                    instances.append(item)

                    if target_class not in available_classes:
                        available_classes.add(target_class)

    empty_classes = set(class_to_idx.keys()) - available_classes
    if empty_classes:
        msg = f"Found no valid file for the classes {', '.join(sorted(empty_classes))}. "
        if extensions is not None:
            msg += f"Supported extensions are: {extensions if isinstance(extensions, str) else ', '.join(extensions)}"
        raise FileNotFoundError(msg)

    return instances


class DatasetFolder(Dataset):
    """A generic data loader.

    This default directory structure can be customized by overriding the
    :meth:`find_classes` method.

    Args:
        root (string): Root directory path.
        loader (callable): A function to load a sample given its path.
        extensions (tuple[string]): A list of allowed extensions.
            both extensions and is_valid_file should not be passed.
        transform (callable, optional): A function/transform that takes in
            a sample and returns a transformed version.
            E.g, ``transforms.RandomCrop`` for images.
        target_transform (callable, optional): A function/transform that takes
            in the target and transforms it.
        is_valid_file (callable, optional): A function that takes path of a file
            and check if the file is a valid file (used to check of corrupt files)
            both extensions and is_valid_file should not be passed.

     Attributes:
        classes (list): List of the class names sorted alphabetically.
        class_to_idx (dict): Dict with items (class_name, class_index).
        samples (list): List of (sample path, class_index) tuples
        targets (list): The class_index value for each image in the dataset
    """

    def __init__(
        self,
        root: str,
        loader: Callable[[str], Any],
        extensions: Optional[Tuple[str, ...]] = None,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        is_valid_file: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.root = root
        self.transform = transform
        self.target_transform = target_transform

        classes, class_to_idx = self.find_classes(self.root)
        samples = self.make_dataset(self.root, class_to_idx, extensions, is_valid_file)
        print(f"find total {len(classes)} classes and {len(samples)} images.")

        self.loader = loader
        self.extensions = extensions

        self.classes = classes
        self.class_to_idx = class_to_idx
        self.samples = samples
        self.targets = [s[1] for s in samples]

    @staticmethod
    def make_dataset(
        directory: str,
        class_to_idx: Dict[str, int],
        extensions: Optional[Tuple[str, ...]] = None,
        is_valid_file: Optional[Callable[[str], bool]] = None,
    ) -> List[Tuple[str, int]]:
        """Generates a list of samples of a form (path_to_sample, class).

        This can be overridden to e.g. read files from a compressed zip file instead of from the disk.

        Args:
            directory (str): root dataset directory, corresponding to ``self.root``.
            class_to_idx (Dict[str, int]): Dictionary mapping class name to class index.
            extensions (optional): A list of allowed extensions.
                Either extensions or is_valid_file should be passed. Defaults to None.
            is_valid_file (optional): A function that takes path of a file
                and checks if the file is a valid file
                (used to check of corrupt files) both extensions and
                is_valid_file should not be passed. Defaults to None.

        Raises:
            ValueError: In case ``class_to_idx`` is empty.
            ValueError: In case ``extensions`` and ``is_valid_file`` are None or both are not None.
            FileNotFoundError: In case no valid file was found for any class.

        Returns:
            List[Tuple[str, int]]: samples of a form (path_to_sample, class)
        """
        if class_to_idx is None:
            # prevent potential bug since make_dataset() would use the class_to_idx logic of the
            # find_classes() function, instead of using that of the find_classes() method, which
            # is potentially overridden and thus could have a different logic.
            raise ValueError("The class_to_idx parameter cannot be None.")
        return make_dataset(directory, class_to_idx, extensions=extensions, is_valid_file=is_valid_file)

    def find_classes(self, directory: str) -> Tuple[List[str], Dict[str, int]]:
        """Find the class folders in a dataset structured as follows::

            directory/
            ├── class_x
            │   ├── xxx.ext
            │   ├── xxy.ext
            │   └── ...
            │       └── xxz.ext
            └── class_y
                ├── 123.ext
                ├── nsdf3.ext
                └── ...
                └── asd932_.ext

        This method can be overridden to only consider
        a subset of classes, or to adapt to a different dataset directory structure.

        Args:
            directory(str): Root directory path, corresponding to ``self.root``

        Raises:
            FileNotFoundError: If ``dir`` has no class folders.

        Returns:
            (Tuple[List[str], Dict[str, int]]): List of all classes and dictionary mapping each class to an index.
        """
        return find_classes(directory)

    def __getitem__(self, index: int) -> Tuple[Any, Any]:
        """
        Args:
            index (int): Index

        Returns:
            tuple: (sample, target) where target is class_index of the target class.
        """
        path, target = self.samples[index]
        sample = self.loader(path)
        if self.transform is not None:
            sample = self.transform(sample)
        if self.target_transform is not None:
            target = self.target_transform(target)
        return sample, np.int32(target)

    def __len__(self) -> int:
        return len(self.samples)

    @property
    def class_num(self):
        return len(set(self.classes))


IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".pgm", ".tif", ".tiff", ".webp")

_image_backend = "pil"


def pil_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, "rb") as f:
        img = Image.open(f)
        return img.convert("RGB")


def set_image_backend(backend):
    """
    Specifies the package used to load images.

    Args:
        backend (string): Name of the image backend. one of {'PIL', 'accimage'}.
            The :mod:`accimage` package uses the Intel IPP library. It is
            generally faster than PIL, but does not support as many operations.
    """
    global _image_backend
    if backend not in ["pil", "cv2"]:
        raise ValueError(f"Invalid backend '{backend}'. Options are 'pil' and 'cv2'")
    _image_backend = backend


def get_image_backend():
    """
    Gets the name of the package used to load images
    """
    return _image_backend


def cv2_loader(path: str):
    return cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)


def default_loader(path: str) -> Any:
    if get_image_backend() == "cv2":
        return cv2_loader(path)
    else:
        return pil_loader(path)


class ImageFolder(DatasetFolder):
    """A generic data loader where the images are arranged in this way by default: ::

        root/dog/xxx.png
        root/dog/xxy.png
        root/dog/[...]/xxz.png

        root/cat/123.png
        root/cat/nsdf3.png
        root/cat/[...]/asd932_.png

    This class inherits from :class:`~torchvision.datasets.DatasetFolder` so
    the same methods can be overridden to customize the dataset.

    Args:
        root (string): Root directory path.
        transform (callable, optional): A function/transform that  takes in an PIL image
            and returns a transformed version. E.g, ``transforms.RandomCrop``
        target_transform (callable, optional): A function/transform that takes in the
            target and transforms it.
        loader (callable, optional): A function to load an image given its path.
        is_valid_file (callable, optional): A function that takes path of an Image file
            and check if the file is a valid file (used to check of corrupt files)

     Attributes:
        classes (list): List of the class names sorted alphabetically.
        class_to_idx (dict): Dict with items (class_name, class_index).
        imgs (list): List of (image path, class_index) tuples
    """

    def __init__(
        self,
        root: str,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        loader: Callable[[str], Any] = default_loader,
        is_valid_file: Optional[Callable[[str], bool]] = None,
    ):
        super().__init__(
            root,
            loader,
            IMG_EXTENSIONS if is_valid_file is None else None,
            transform=transform,
            target_transform=target_transform,
            is_valid_file=is_valid_file,
        )
        self.imgs = self.samples


import bisect


class ConcatDataset(Dataset):
    r"""Dataset as a concatenation of multiple datasets.

    This class is useful to assemble different existing datasets.

    Args:
        datasets (sequence): List of datasets to be concatenated
    """
    datasets: List[Dataset]
    cumulative_sizes: List[int]

    @staticmethod
    def cumsum(sequence):
        r, s = [], 0
        for e in sequence:
            l = len(e)
            r.append(l + s)
            s += l
        return r

    def __init__(self, datasets) -> None:
        super().__init__()
        self.datasets = list(datasets)
        assert len(self.datasets) > 0, "datasets should not be an empty iterable"  # type: ignore[arg-type]
        for d in self.datasets:
            assert not isinstance(d, IterableDataset), "ConcatDataset does not support IterableDataset"
        self.cumulative_sizes = self.cumsum(self.datasets)

    def __len__(self):
        return self.cumulative_sizes[-1]

    def __getitem__(self, idx):
        if idx < 0:
            if -idx > len(self):
                raise ValueError("absolute value of index should not exceed dataset length")
            idx = len(self) + idx
        dataset_idx = bisect.bisect_right(self.cumulative_sizes, idx)
        if dataset_idx == 0:
            sample_idx = idx
        else:
            sample_idx = idx - self.cumulative_sizes[dataset_idx - 1]
        return self.datasets[dataset_idx][sample_idx]

    @property
    def cummulative_sizes(self):
        warnings.warn(
            "cummulative_sizes attribute is renamed to " "cumulative_sizes", DeprecationWarning, stacklevel=2
        )
        return self.cumulative_sizes


class MixDataset(Dataset):
    datasets_names: List[Dict]

    def __init__(self, datasets_names) -> None:
        super().__init__()
        self.datasets_names = list(datasets_names)
        self.datasets = []
        for d in self.datasets_names:
            name = d["name"]
            data_files = d["data_files"] if "data_files" in d else None
            splits = d["splits"] if "splits" in d else None
            chat_template = d["chat_template"] if "chat_template" in d else None
            self.datasets.append(load_dataset(name, data_files=data_files, splits=splits, chat_template=chat_template))

        self.datasets = ConcatDataset(self.datasets)

    def __len__(self):
        return len(self.datasets)

    def __getitem__(self, idx):
        return self.datasets[idx]
