/**
 * @file facial_analysis.h
 * @brief Header file for the ONNX backend implementation of the EmotiEffLibRecognizer.
 */

#ifndef BACKENDS_ONNX_FACIAL_ANALYSIS_H
#define BACKENDS_ONNX_FACIAL_ANALYSIS_H

#include "emotiefflib/facial_analysis.h"

#include <onnxruntime_cxx_api.h>

namespace EmotiEffLib {

/**
 * @brief ONNX backend implementation of the EmotiEffLibRecognizer.
 *
 * This class provides the ONNX-specific implementation for emotion and engagement recognition.
 */
class EmotiEffLibRecognizerOnnx final : public EmotiEffLibRecognizer {
public:
    /**
     * @brief Constructs an EmotiEffLibRecognizerOnnx instance with the specified model path.
     *
     * @param fullPipelineModelPath Path to the full pipeline emotion recognition ONNX model.
     */
    EmotiEffLibRecognizerOnnx(const std::string& fullPipelineModelPath);

    /**
     * @brief Constructs an EmotiEffLibRecognizerOnnx instance with the specified configuration.
     *
     * @param config The configuration structure.
     */
    EmotiEffLibRecognizerOnnx(const EmotiEffLibConfig& config);

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

    /**
     * @brief Runs the model with the specified inputs.
     *
     * @param modelIdx The index of the model to run.
     * @param inputs The input tensors.
     * @return The output tensors.
     */
    std::vector<Ort::Value> modelRunWrapper(int modelIdx, const std::vector<Ort::Value>& inputs);

private:
    /// Mean values for image normalization.
    std::vector<float> mean_;
    /// Standard deviation values for image normalization.
    std::vector<float> std_;
    /// ONNX Runtime environment.
    Ort::Env env_ = {ORT_LOGGING_LEVEL_WARNING, "EmotiEffLib"};
    /// ONNX Runtime allocator.
    Ort::AllocatorWithDefaultOptions allocator_;
    /// List of ONNX models.
    std::vector<Ort::Session> models_;
};
} // namespace EmotiEffLib

#endif
