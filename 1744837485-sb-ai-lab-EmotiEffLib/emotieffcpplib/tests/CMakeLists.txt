cmake_minimum_required(VERSION 3.10.2)

enable_testing()

function(build_mtcnn)
    # This is a part of CMakeLists.txt file from opencv-mtcnn repository and it is necessary only to
    # avoid boost dependencies from samples.

    #configure variables
    set (MTCNN_LIB_NAME "mtcnn")

    # configure directories
    set(MTCNN_PATH "${PROJECT_SOURCE_DIR}/3rdparty/opencv-mtcnn")
    set (MTCNN_LIB_PATH "${MTCNN_PATH}/lib")
    set (MTCNN_LIB_SRC_PATH  "${MTCNN_LIB_PATH}/src" )
    set (MTCNN_LIB_INCLUDE_PATH  "${MTCNN_LIB_PATH}/include")

    find_package(OpenCV REQUIRED)

    # set includes
    include_directories (
        ${MTCNN_LIB_INCLUDE_PATH}
        ${OpenCV_INCLUDE_DIRS}
    )

    # set sources
    file (GLOB MTCNN_LIB_HEADER_FILES "${MTCNN_LIB_INCLUDE_PATH}/**/*.h" "${MTCNN_LIB_INCLUDE_PATH}/**/**/*.h")
    file (GLOB MTCNN_LIB_SOURCE_FILES "${MTCNN_LIB_SRC_PATH}/*.cc" "${MTCNN_LIB_SRC_PATH}/**/*.cc")

    # set library
    add_library (${MTCNN_LIB_NAME} ${MTCNN_LIB_SOURCE_FILES} ${MTCNN_LIB_HEADER_FILES})
    set_target_properties(${PROJECT_NAME} PROPERTIES
        VERSION 1.0
        SOVERSION 1
    )
endfunction()

build_mtcnn()
#add_subdirectory("${MTCNN_PATH}" "${CMAKE_BINARY_DIR}/3rdparty/opencv-mtcnn")

include_directories(
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${PROJECT_SOURCE_DIR}/3rdparty/opencv-mtcnn/lib/include"
)

file(GLOB src_files
    "*.cpp"
)

add_executable(unit_tests
  ${src_files}
)
target_link_libraries(
  unit_tests
  ${PROJECT_NAME}
  GTest::gtest_main
  mtcnn
)

include(GoogleTest)
gtest_discover_tests(unit_tests)
