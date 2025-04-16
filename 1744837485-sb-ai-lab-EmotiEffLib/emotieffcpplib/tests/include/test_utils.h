#ifndef TEST_UTILS_H
#define TEST_UTILS_H

#include <opencv2/opencv.hpp>
#include <string>
#include <vector>

std::string getEmotiEffLibRootDir();
std::vector<cv::Mat> recognizeFaces(const cv::Mat& frame, int downscaleWidth = 500);
std::string getPathToPythonTestDir();

// Print std::vector
template <typename T> std::ostream& operator<<(std::ostream& os, const std::vector<T>& vec) {
    os << "[";
    for (size_t i = 0; i < vec.size(); ++i) {
        os << vec[i];
        if (i < vec.size() - 1) {
            os << ", ";
        }
    }
    os << "]";
    return os;
}

// Function to compare two vectors
template <typename T> bool AreVectorsEqual(const std::vector<T>& v1, const std::vector<T>& v2) {
    if (v1.size() != v2.size()) {
        std::cerr << "Vectors have different sizes: " << v1.size() << " vs " << v2.size()
                  << std::endl;
        std::cerr << "v1: " << v1 << std::endl;
        std::cerr << "v2: " << v2 << std::endl;
        return false; // Vectors must have the same size
    }
    if (!std::equal(v1.begin(), v1.end(), v2.begin())) {
        std::cerr << "Vectors are not equal:" << std::endl;
        std::cerr << "v1: " << v1 << std::endl;
        std::cerr << "v2: " << v2 << std::endl;

        return false;
    }
    return true;
}

#endif
