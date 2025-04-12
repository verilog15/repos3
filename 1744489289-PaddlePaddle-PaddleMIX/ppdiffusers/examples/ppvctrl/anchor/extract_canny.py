import argparse
import sys
import decord
from decord import VideoReader, cpu
import moviepy.editor as mpy
import numpy as np
import cv2
from utils.video_utils import create_video,save_video_from_bgr
if __name__=='__main__': 
#   if len(sys.argv) != 2:
#     print("用法: python extract_video_canny.py your_video_file.mp4")
#     sys.exit(1)
    parser = argparse.ArgumentParser("Extract Video Canny Demo", add_help=True)
    parser.add_argument("--input_path", type=str, default=None)
    parser.add_argument("--control_video_path", type=str, default="guide_values.mp4")
    parser.add_argument("--reference_image_path", type=str, default="reference_image.jpg")
    parser.add_argument("--canny_threshold_1", type=float, default=200)
    parser.add_argument("--canny_threshold_2", type=float, default=255)
    args = parser.parse_args()


    # 使用decord的VideoReader读取视频
    vr = VideoReader(args.input_path, ctx=cpu(0))

    # 提取并保存第一帧
    first_frame = vr[0].asnumpy()
    first_frame_bgr = cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR)
    cv2.imwrite(args.reference_image_path, first_frame_bgr)
    
    # 逐帧读取视频
    frames = []
    for i in range(len(vr)):
        frame = vr[i].asnumpy()  # 将帧转换为numpy数组（格式为RGB）

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.Canny(frame, args.canny_threshold_1, args.canny_threshold_2)
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        frames.append(frame)

    cv2.imwrite(args.reference_image_path.replace("reference", "control"), frames[0])
    save_video_from_bgr(frames, args.control_video_path,frame_rate=30)