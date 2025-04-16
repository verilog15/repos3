# EmotiEffCppLib

EmotiEffCppLib is a C++ library designed for emotion and engagement recognition in images and videos. It supports multiple inference engines, including Libtorch and ONNX Runtime.

## Features

- Supports Libtorch and ONNX Runtime for inference
- Uses OpenCV for image processing
- Includes xtensor for working with tensors
- Configurable as a static or shared library

## Requirements

- C++17 or later
- CMake 3.10.2 or later
- OpenCV
- At least one of inference engines Libtorch or ONNX Runtime

## CMake Options
The following options can be set during configuration:
- `WITH_TORCH` (Default: OFF): Path to the directory containing Libtorch.
- `WITH_ONNX` (Default: OFF): Path to the directory containing ONNX Runtime.
- `BUILD_TESTS` (Default: OFF): Enable building unit tests using GoogleTest.
- `BUILD_SHARED_LIBS` (Default: OFF): Build as a shared library instead of a static library.

At least one of `WITH_TORCH` or `WITH_ONNX` must be enabled.

## Installation
### 1. Clone the repository
```sh
git clone https://github.com/sb-ai-lab/EmotiEffLib.git
cd EmotiEffLib
git submodule update --init --recursive
```

### 2. Prepare inference engines
#### 2.1 Libtorch
1. Download Libtorch for your OS from here: https://pytorch.org/get-started/locally/

   NOTE: The newest version Libtorch for x86 MacOS is not available. The latest
available version 2.2.2 can be downloaded from here: https://download.pytorch.org/libtorch/cpu/libtorch-macos-x86_64-2.2.2.zip

2. Unpack downloaded archive and path to this folder will be used in
   `-DWITH_TORCH` option.

#### 2.2 ONNX Runtime
1. Download the latest version of ONNX Runtime for your OS from GitHub: https://github.com/microsoft/onnxruntime/releases
2. Unpack downloaded archive and path to this folder will be used in
   `-DWITH_ONNX` option.

### 3. Configure and build the project

#### Basic build (specify at least one inference engine)
```sh
mkdir build && cd build
cmake .. -DWITH_TORCH=/path/to/libtorch -DWITH_ONNX=/path/to/onnxruntime
make -j$(nproc)
```

#### Build with tests
```sh
cmake .. -DWITH_TORCH=/path/to/libtorch -DWITH_ONNX=/path/to/onnxruntime -DBUILD_TESTS=ON
make -j$(nproc)
```
## Usage
### 1. Linking the Library
To use EmotiEffCppLib in your project, you can add this repository as a
submodule to your project and add the following code in your `CMakeLists.txt`:
```cmake
# At least one of these variables should be specified
set(WITH_TORCH "/path/to/libtorch")
set(WITH_ONNX "/path/to/ONNXRuntime")
add_subdirectory("${PROJECT_SOURCE_DIR}/path/to/emotiefflib/emotieffcpplib")
include_directories(
    "${PROJECT_SOURCE_DIR}/path/to/emotiefflib/emotieffcpplib/include"
)
target_link_libraries(your_project PRIVATE emotiefflib)
```

### 2. Run emotions and engagement recognition
Examples of usage EmotiEffCppLib you can find in the [cpp examples section](../docs/tutorials/cpp/README.md).

## Running tests
Google Tests are used for testing EmotiEffCppLib. To run them, you need to follow
the following steps:
1. To run unit tests you should build EmotiEffCppLib with option
`-DBUILD_TESTS=ON`.
2. It is necessary to define the following environment variable:
  ```sh
  export EMOTIEFFLIB_ROOT="/path/to/root/of/emotiefflib_repo"
  ```
  This variable is used in tests to find inputs for tests.
3. Download testing data:
  ```sh
  cd <emotiefflib_root>/tests
  ./download_test_data.sh
  tar -xzf data.tar.gz
  cd -
  ```
3. Run the gtests:
  ```sh
  ./<build_dir>/bin/unit_tests
  ```

## License

The code of EmotiEffCppLib Library is released under the Apache-2.0 License. There is no limitation for both academic and commercial usage.
