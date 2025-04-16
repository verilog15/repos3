#!/bin/bash

config=$1
exit_code=0

echo "Checking configuration: $config..."

if [ "$config" == "" ]; then
    if python -c "import torch" &> /dev/null; then
        exit_code=1
        echo "Package torch is installed, exit code: $exit_code"
    else
        echo "Package torch is not installed, exit code: $exit_code"
    fi
    if python -c "import onnx" &> /dev/null; then
        echo "Package onnx is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package onnx is not installed, exit code: $exit_code"
    fi
    if python -c "import tensorflow" &> /dev/null; then
        exit_code=1
        echo "Package tensorflow is installed, exit code: $exit_code"
    else
        echo "Package tensorflow is not installed, exit code: $exit_code"
    fi
    exit $exit_code
elif [ "$config" == "[torch]" ]; then
    if python -c "import torch" &> /dev/null; then
        echo "Package torch is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package torch is not installed, exit code: $exit_code"
    fi
    if python -c "import onnx" &> /dev/null; then
        echo "Package onnx is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package onnx is not installed, exit code: $exit_code"
    fi
    if python -c "import tensorflow" &> /dev/null; then
        exit_code=1
        echo "Package tensorflow is installed, exit code: $exit_code"
    else
        echo "Package tensorflow is not installed, exit code: $exit_code"
    fi
    exit $exit_code
elif [ "$config" == "[engagement]" ]; then
    if python -c "import torch" &> /dev/null; then
        exit_code=1
        echo "Package torch is installed, exit code: $exit_code"
    else
        echo "Package torch is not installed, exit code: $exit_code"
    fi
    if python -c "import onnx" &> /dev/null; then
        echo "Package onnx is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package onnx is not installed, exit code: $exit_code"
    fi
    if python -c "import tensorflow" &> /dev/null; then
        echo "Package tensorflow is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package tensorflow is not installed, exit code: $exit_code"
    fi
    exit $exit_code
elif [ "$config" == "[torch,engagement]" ]; then
    if python -c "import torch" &> /dev/null; then
        echo "Package torch is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package torch is not installed, exit code: $exit_code"
    fi
    if python -c "import onnx" &> /dev/null; then
        echo "Package onnx is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package onnx is not installed, exit code: $exit_code"
    fi
    if python -c "import tensorflow" &> /dev/null; then
        echo "Package tensorflow is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package tensorflow is not installed, exit code: $exit_code"
    fi
    exit $exit_code
elif [ "$config" == "[all]" ]; then
    if python -c "import torch" &> /dev/null; then
        echo "Package torch is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package torch is not installed, exit code: $exit_code"
    fi
    if python -c "import onnx" &> /dev/null; then
        echo "Package onnx is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package onnx is not installed, exit code: $exit_code"
    fi
    if python -c "import tensorflow" &> /dev/null; then
        echo "Package tensorflow is installed, exit code: $exit_code"
    else
        exit_code=1
        echo "Package tensorflow is not installed, exit code: $exit_code"
    fi
    exit $exit_code
fi

echo "Error: Invalid parameter '$config'."
echo "Allowed values: \"\", \"[torch]\", \"[onnx]\", \"[torch,onnx]\", \"[engagement]\", \"[all]\""
exit 1
