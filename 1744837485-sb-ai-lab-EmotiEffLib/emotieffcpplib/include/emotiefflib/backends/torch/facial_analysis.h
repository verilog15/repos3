/**
 * @file facial_analysis.h
 * @brief Header file for the Torch backend implementation of the EmotiEffLibRecognizer.
 */

#ifndef BACKENDS_TORCH_FACIAL_ANALYSIS_H
#define BACKENDS_TORCH_FACIAL_ANALYSIS_H

#include "emotiefflib/facial_analysis.h"

#include <torch/script.h>

namespace EmotiEffLib {

/**
 * @brief Torch backend implementation of the EmotiEffLibRecognizer.
 *
 * This class provides the Torch-specific implementation for emotion and engagement recognition.
 */
class EmotiEffLibRecognizerTorch final : public EmotiEffLibRecognizer {
public:
    /**
     * @brief Constructs an EmotiEffLibRecognizerOnnx instance with the specified model path.
     *
     * @param fullPipelineModelPath Path to the full pipeline emotion recognition ONNX model.
     */
    EmotiEffLibRecognizerTorch(const std::string& fullPipelineModelPath);

    /**
     * @brief Constructs an EmotiEffLibRecognizerOnnx instance with the specified configuration.
     *
     * @param config The configuration structure.
     */
    EmotiEffLibRecognizerTorch(const EmotiEffLibConfig& config);

    /**
     * @brief Extracts features from a single face image.
     *
     * @param faceImg The input face image.
     * @return An array of extracted features.
     */
    xt::xarray<float> extractFeatures(const cv::Mat& faceImg) override;

    /**
     * @brief Classifies emotions based on extracted features.
     *
     * @param features The extracted features.
     * @param logits Whether to return raw logits or apply softmax.
     * @return The classification results.
     */
    EmotiEffLibRes classifyEmotions(const xt::xarray<float>& features, bool logits = true) override;

    /**
     * @brief Classifies engagement based on extracted features.
     *
     * @param features The extracted features.
     * @return The classification results.
     */
    EmotiEffLibRes classifyEngagement(const xt::xarray<float>& features) override;

    /**
     * @brief Predicts emotions for a single face image.
     *
     * @param faceImg The input face image.
     * @param logits Whether to return raw logits or apply softmax.
     * @return The prediction results.
     */
    EmotiEffLibRes predictEmotions(const cv::Mat& faceImg, bool logits = true) override;

    /**
     * @brief Predicts engagement for a sequence of face images.
     *
     * @param faceImgs A list of input face images.
     * @return The prediction results.
     */
    EmotiEffLibRes predictEngagement(const std::vector<cv::Mat>& faceImgs) override;

private:
    /**
     * @brief Initializes the internal state of recognizer based on a modelPath.
     *
     * @param modelPath Path to the model file.
     */
    void initRecognizer(const std::string& modelPath) override;

    /**
     * @brief Parses the configuration to initialize the recognizer.
     *
     * @param config The configuration structure.
     */
    void configParser(const EmotiEffLibConfig& config) override;

    /**
     * @brief Preprocesses an image for feature extraction.
     *
     * @param img The input image.
     * @return The preprocessed image as an array.
     */
    xt::xarray<float> preprocess(const cv::Mat& img) override;

private:
    /// List of Torch models.
    std::vector<torch::jit::script::Module> models_;
};
} // namespace EmotiEffLib

#endif
