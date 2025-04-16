# EmotiEffLib C++ examples

Here you can find examples of using EmotiEffLib in C++.

Here is a list of examples:
- [One image emotion recognition.ipynb](https://github.com/sb-ai-lab/EmotiEffLib/blob/main/docs/tutorials/cpp/One%20image%20emotion%20recognition.ipynb)
    describes how to use EmotiEffLib to recognize facial emotions on images.
- [Predict emotions on video.ipynb](https://github.com/sb-ai-lab/EmotiEffLib/blob/main/docs/tutorials/cpp/Predict%20emotions%20on%20video.ipynb) describes
    how to use EmotiEffLib for predicting facial emotions on videos.
- [Predict engagement and emotions on video.ipynb](https://github.com/sb-ai-lab/EmotiEffLib/blob/main/docs/tutorials/cpp/Predict%20engagement%20and%20emotions%20on%20video.ipynb) describes how to use EmotiEffLib for predicting facial expressions and recognizing a person's engagement in a video.

## Building and running examples
To run the examples locally you need to do the following:
1. Install python dependencies:
  ```
  pip install -r requirements.txt
  ```
1. Build [EmotiEffCppLib](../../../emotieffcpplib) with Libtorch and ONNXRuntime. It is important to
   build EmotiEffCppLib with flag: `-DBUILD_TESTS=ON` because we need
   to reuse one library which builds for tests. Also, it is required to build
   EmotiEffCppLib with flag: `-DBUILD_SHARED_LIBS=ON` because xeus-cling works
   only with shared libraries.
2. Install [xeus-cling](https://github.com/jupyter-xeus/xeus-cling). Instruction how to build xeus-cling can be found [here](https://xeus-cling.readthedocs.io/en/latest/installation.html).

  After installing xeus-cling, you should be able to check available kernels and see `xcpp17` kernel:
  ```
  $ jupyter kernelspec list
  Available kernels:
    python3    /opt/anaconda3/envs/emotiefflib/share/jupyter/kernels/python3
    xcpp11     /opt/anaconda3/envs/emotiefflib/share/jupyter/kernels/xcpp11
    xcpp14     /opt/anaconda3/envs/emotiefflib/share/jupyter/kernels/xcpp14
    xcpp17     /opt/anaconda3/envs/emotiefflib/share/jupyter/kernels/xcpp17
  ```
3. Prepare models for cpp runtime:
  ```
  python3 <EmotiEffLib_root>/models/prepare_models_for_emotieffcpplib.py
  ```
4. Download and unpack test data:
  ```
  cd <EmotiEffLib_root>/tests
  ./download_test_data.sh
  tar -xzf data.tar.gz
  ```
5. Run jupyter notebook and select C++ kernel.
